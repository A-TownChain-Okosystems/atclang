# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Kernel Runtime — Dezentrales KI-Betriebssystem Runtime
===============================================================
Version: 1.0.0-alpha | ATC-97 | Sprint 3.2

Verbindet ATCLang Compiler + VM + Kernel API zu einer ausführbaren Runtime.
Lädt .atc Module, kompiliert sie zu Bytecode, führt Contracts aus
und dispatcht Syscalls über die KernelAPI.

Pipeline:
    .atc file → Lexer → Parser → AST → Compiler → Bytecode → VM → Kernel

Architektur:
    ┌─────────────────────────────────────────────────────┐
    │              ATCLang Kernel Runtime                   │
    ├─────────────────────────────────────────────────────┤
    │  Module Loader  →  Compiler  →  VM  →  Kernel API    │
    │       ↓              ↓         ↓        ↓           │
    │  Contract State  │  Bytecode │ Stack  │ Syscalls    │
    │  Event Bus       │  Functions│ Events │ Memory/IPC  │
    │  Persistence     │  Exports  │ Gas    │ AI/Consensus│
    └─────────────────────────────────────────────────────┘
"""

import os
import sys
import time
import json
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Callable

from atclang.parser.parser import parse
from atclang.parser.ast_nodes import (
    Program, ContractDef, FunctionDef, EventDef, ErrorDef,
    StructDef, EnumDef, ImportStatement, LetStatement,
    ClassDef, StorageBlock, TypeAliasDef,
)
from atclang.compiler.compiler import compile_source, ATCCompiler, CompiledModule
from atclang.vm.atcvm import (
    ATCVM, ATCFunction, Instruction, OP, ATCVMError,
    RequireError, GasError, ATCObject, STDLIB_DISPATCH,
)


# ════════════════════════════════════════════════════════════════
#  CONTRACT STATE — Persistenter Contract-Zustand
# ════════════════════════════════════════════════════════════════

@dataclass
class ContractState:
    """Laufzeit-Zustand eines ATCLang Contracts."""
    name: str
    fields: Dict[str, Any] = field(default_factory=dict)
    functions: Dict[str, ATCFunction] = field(default_factory=dict)
    events: List[dict] = field(default_factory=list)
    enums: Dict[str, Dict[str, int]] = field(default_factory=dict)
    structs: Dict[str, type] = field(default_factory=dict)
    imports: List[str] = field(default_factory=list)
    source_path: str = ""
    gas_used: int = 0
    call_count: int = 0
    initialized: bool = False


# ════════════════════════════════════════════════════════════════
#  MODULE DESCRIPTOR — Geladenes .atc Modul
# ════════════════════════════════════════════════════════════════

@dataclass
class ATCModule:
    """Ein geladenes ATCLang-Modul."""
    name: str
    path: str
    source: str
    ast: Program
    compiled: CompiledModule
    contracts: Dict[str, ContractState] = field(default_factory=dict)
    globals: Dict[str, Any] = field(default_factory=dict)
    loaded_at: float = field(default_factory=time.time)
    source_hash: str = ""

    def summary(self) -> str:
        n_fns = sum(len(c.functions) for c in self.contracts.values())
        n_contracts = len(self.contracts)
        return (f"Module '{self.name}' | {n_contracts} contracts | "
                f"{n_fns} functions | {len(self.compiled.instructions)} instrs")


# ════════════════════════════════════════════════════════════════
#  ERRORS
# ════════════════════════════════════════════════════════════════

class KernelRuntimeError(Exception):
    """Runtime-Fehler im ATCLang Kernel."""
    pass


class ContractCallError(KernelRuntimeError):
    """Fehler bei Contract-Aufruf."""
    pass


class ModuleLoadError(KernelRuntimeError):
    """Fehler beim Laden eines .atc Moduls."""
    pass


# ════════════════════════════════════════════════════════════════
#  KERNEL RUNTIME — Zentrale Runtime-Instanz
# ════════════════════════════════════════════════════════════════

class KernelRuntime:
    """
    ATCLang Kernel Runtime — Lädt, kompiliert und führt .atc Module aus.

    Usage:
        rt = KernelRuntime()
        rt.load_file("modules/kernel/kernel_api.atc")
        result = rt.call("KernelAPI.spawn", "test_agent", ...)
    """

    VERSION = "1.0.0-alpha"

    def __init__(self, gas_limit: int = 50_000_000):
        self.vm = ATCVM(gas_limit=gas_limit)
        self.modules: Dict[str, ATCModule] = {}
        self.contracts: Dict[str, ContractState] = {}
        self.module_cache: Dict[str, str] = {}  # path → name
        self.event_bus: List[dict] = []
        self.call_log: List[dict] = []
        self._syscalls_registered = 0
        self._boot_time = time.time()

        # Register kernel-specific stdlib extensions
        self._register_kernel_stdlib()

    # ═══════════════════════════════════════════════════════════
    #  MODULE LOADING
    # ═══════════════════════════════════════════════════════════

    def load_file(self, path: str, module_name: str = None) -> ATCModule:
        """Lädt eine .atc Datei, kompiliert sie und registriert Contracts."""
        if not os.path.exists(path):
            raise ModuleLoadError(f"File not found: {path}")

        source = open(path, 'r', encoding='utf-8').read()
        return self.load_source(source, module_name or self._derive_name(path), path)

    def load_source(self, source: str, module_name: str, path: str = "<inline>") -> ATCModule:
        """Lädt ATCLang-Quellcode, kompiliert und registriert ihn."""
        # Check cache
        source_hash = hashlib.sha256(source.encode()).hexdigest()[:16]
        if module_name in self.modules and self.modules[module_name].source_hash == source_hash:
            return self.modules[module_name]

        try:
            ast = parse(source)
        except Exception as e:
            raise ModuleLoadError(f"Parse error in '{module_name}': {e}")

        try:
            compiled = compile_source(source)
        except Exception as e:
            raise ModuleLoadError(f"Compile error in '{module_name}': {e}")

        # Register functions in VM
        for fname, instrs in compiled.functions.items():
            params = compiled.function_params.get(fname, [])
            self.vm.register_function(ATCFunction(fname, params, instrs))

        # Build module
        module = ATCModule(
            name=module_name,
            path=path,
            source=source,
            ast=ast,
            compiled=compiled,
            source_hash=source_hash,
        )

        # Extract contracts, enums, structs from AST
        for node in ast.statements:
            if isinstance(node, ContractDef):
                contract = self._build_contract_state(node, module_name)
                module.contracts[contract.name] = contract
                self.contracts[contract.name] = contract
            elif isinstance(node, ClassDef):
                # Treat class like a contract
                contract = self._build_class_state(node, module_name)
                module.contracts[contract.name] = contract
                self.contracts[contract.name] = contract
            elif isinstance(node, EnumDef):
                self._register_enum(node, module)
            elif isinstance(node, StructDef):
                self._register_struct(node, module)
            elif isinstance(node, ImportStatement):
                mod_path = "::".join(node.path)
                module.imports.append(mod_path)

        # Run init functions for contracts
        for contract in module.contracts.values():
            if not contract.initialized:
                self._init_contract(contract)

        self.modules[module_name] = module
        self.module_cache[path] = module_name
        return module

    def load_directory(self, dir_path: str, pattern: str = "*.atc") -> List[ATCModule]:
        """Lädt alle .atc Dateien aus einem Verzeichnis."""
        loaded = []
        for root, dirs, files in os.walk(dir_path):
            for f in sorted(files):
                if f.endswith('.atc') and not f.startswith('.'):
                    path = os.path.join(root, f)
                    name = self._derive_name(path)
                    try:
                        mod = self.load_file(path, name)
                        loaded.append(mod)
                    except KernelRuntimeError as e:
                        self.call_log.append({"error": str(e), "path": path})
        return loaded

    # ═══════════════════════════════════════════════════════════
    #  CONTRACT EXECUTION
    # ═══════════════════════════════════════════════════════════

    def call(self, fn_path: str, *args) -> Any:
        """
        Ruft eine Contract-Funktion auf.
        fn_path Format: "ContractName.function_name"
        """
        if '.' not in fn_path:
            return self._call_global(fn_path, list(args))

        contract_name, fn_name = fn_path.split('.', 1)
        contract = self.contracts.get(contract_name)
        if not contract:
            raise ContractCallError(f"Contract '{contract_name}' not loaded. Available: {list(self.contracts.keys())}")

        fn = contract.functions.get(fn_path)
        if not fn:
            fn = contract.functions.get(fn_name)
        if not fn:
            raise ContractCallError(
                f"Function '{fn_name}' not found in contract '{contract_name}'. "
                f"Available: {list(contract.functions.keys())}"
            )

        # Set up call context
        self._setup_call_context(contract)

        # Set up frame with params
        from atclang.vm.atcvm import CallFrame
        frame = CallFrame(func_name=fn_path)
        param_names = [f"arg{i}" for i in range(len(args))]
        for pname, pval in zip(param_names, args):
            frame.locals[pname] = pval

        contract.call_count += 1
        start_gas = self.vm.gas_used

        try:
            result = self.vm.execute(fn.instructions, frame)
        except RequireError as e:
            raise ContractCallError(f"require() failed in {fn_path}: {e}")
        except GasError as e:
            raise ContractCallError(f"Gas limit in {fn_path}: {e}")
        except ATCVMError as e:
            raise ContractCallError(f"VM error in {fn_path}: {e}")

        gas_consumed = self.vm.gas_used - start_gas
        contract.gas_used += gas_consumed

        self.call_log.append({
            "fn": fn_path,
            "args": list(args),
            "result": result,
            "gas": gas_consumed,
            "ts": int(time.time() * 1000),
        })

        return result

    def call_contract(self, contract_name: str, fn_name: str, *args) -> Any:
        """Convenience: Contract-Funktion aufrufen."""
        return self.call(f"{contract_name}.{fn_name}", *args)

    # ═══════════════════════════════════════════════════════════
    #  CONTRACT STATE ACCESS
    # ═══════════════════════════════════════════════════════════

    def get_contract_state(self, contract_name: str) -> Optional[ContractState]:
        return self.contracts.get(contract_name)

    def get_state(self, contract_name: str, field_name: str) -> Any:
        c = self.contracts.get(contract_name)
        if not c:
            return None
        return c.fields.get(field_name)

    def set_state(self, contract_name: str, field_name: str, value: Any):
        c = self.contracts.get(contract_name)
        if c:
            c.fields[field_name] = value

    def get_events(self, contract_name: str = None) -> List[dict]:
        if contract_name:
            c = self.contracts.get(contract_name)
            return c.events if c else []
        return self.event_bus

    # ═══════════════════════════════════════════════════════════
    #  ENUM / STRUCT REGISTRATION
    # ═══════════════════════════════════════════════════════════

    def _register_enum(self, node: EnumDef, module: ATCModule):
        variants = {}
        for i, v in enumerate(node.variants):
            variants[v] = i
        module.globals[node.name] = variants
        self.vm.globals[node.name] = variants

    def _register_struct(self, node: StructDef, module: ATCModule):
        struct_name = node.name
        field_names = []
        for f in node.fields:
            if hasattr(f, 'name'):
                field_names.append(f.name)
            elif isinstance(f, tuple):
                field_names.append(f[0])

        def factory(**kwargs):
            obj = ATCObject(type_name=struct_name)
            for fn in field_names:
                obj.fields[fn] = kwargs.get(fn, None)
            return obj

        module.globals[struct_name] = factory
        self.vm.globals[struct_name] = factory

    # ═══════════════════════════════════════════════════════════
    #  CONTRACT BUILDING
    # ═══════════════════════════════════════════════════════════

    def _build_contract_state(self, node: ContractDef, module_name: str) -> ContractState:
        """Extrahiert Contract-Definition aus dem AST."""
        contract = ContractState(name=node.name)

        # Extract state fields
        for state in node.states:
            contract.fields[state.name] = self._default_value(
                state.type_hint.name if hasattr(state.type_hint, 'name') else state.type_hint
            )

        # Register functions
        for fn in node.functions:
            fn_full_name = f"{node.name}.{fn.name}"
            compiled_fn = self.vm.functions.get(fn_full_name)
            if compiled_fn:
                contract.functions[fn_full_name] = compiled_fn
            compiled_fn2 = self.vm.functions.get(fn.name)
            if compiled_fn2:
                contract.functions[fn.name] = compiled_fn2

        return contract

    def _build_class_state(self, node: ClassDef, module_name: str) -> ContractState:
        """Extrahiert Class-Definition als Contract-State."""
        contract = ContractState(name=node.name)

        # Extract fields
        for fname, ftype in node.fields:
            contract.fields[fname] = self._default_value(
                ftype.name if hasattr(ftype, 'name') else ftype
            )

        # Register functions
        for fn in node.functions:
            fn_full_name = f"{node.name}.{fn.name}"
            compiled_fn = self.vm.functions.get(fn_full_name)
            if compiled_fn:
                contract.functions[fn_full_name] = compiled_fn

        return contract

    def _init_contract(self, contract: ContractState):
        """Führt die init() Funktion eines Contracts aus, falls vorhanden."""
        init_fn = contract.functions.get(f"{contract.name}.init")
        if not init_fn:
            init_fn = contract.functions.get("init")
        if init_fn:
            try:
                from atclang.vm.atcvm import CallFrame
                frame = CallFrame(func_name=f"{contract.name}.init")
                self.vm.execute(init_fn.instructions, frame)
                contract.initialized = True
            except Exception as e:
                self.call_log.append({
                    "fn": f"{contract.name}.init",
                    "error": str(e),
                    "ts": int(time.time() * 1000),
                })

    def _setup_call_context(self, contract: ContractState):
        """Setzt den VM-Kontext für einen Contract-Aufruf."""
        for fname, fval in contract.fields.items():
            self.vm.globals[fname] = fval
        self.vm.globals['msg_sender'] = self.vm.globals.get('caller', 'ATC' + '0' * 32)

    # ═══════════════════════════════════════════════════════════
    #  KERNEL STDLIB EXTENSIONS
    # ═══════════════════════════════════════════════════════════

    def _register_kernel_stdlib(self):
        """Registriert Kernel-spezifische ATC:: stdlib Erweiterungen."""
        kernel_dispatch = {
            "ATC::Kernel::spawn": lambda args: self._kernel_spawn(args),
            "ATC::Kernel::kill": lambda args: self._kernel_kill(args),
            "ATC::Kernel::stats": lambda args: self._kernel_stats(),
            "ATC::Kernel::alloc": lambda args: self._kernel_alloc(args),
            "ATC::Kernel::chan_send": lambda args: self._kernel_chan_send(args),
            "ATC::Kernel::chan_recv": lambda args: self._kernel_chan_recv(args),
            "ATC::Kernel::ai_route": lambda args: self._kernel_ai_route(args),
            "ATC::Kernel::ai_infer": lambda args: self._kernel_ai_infer(args),
            "ATC::Kernel::timestamp": lambda args: int(time.time() * 1000),
            "ATC::Kernel::uptime": lambda args: int((time.time() - self._boot_time) * 1000),
            "ATC::Kernel::version": lambda args: self.VERSION,
        }
        STDLIB_DISPATCH.update(kernel_dispatch)
        self._syscalls_registered = len(kernel_dispatch)

    def _kernel_spawn(self, args: List[Any]) -> int:
        name = str(args[0]) if args else "unnamed"
        return len(self.call_log) + 100

    def _kernel_kill(self, args: List[Any]) -> bool:
        return True

    def _kernel_stats(self) -> dict:
        return self.stats()

    def _kernel_alloc(self, args: List[Any]) -> int:
        return int(args[0]) if args else 0

    def _kernel_chan_send(self, args: List[Any]) -> bool:
        return True

    def _kernel_chan_recv(self, args: List[Any]) -> Any:
        return None

    def _kernel_ai_route(self, args: List[Any]) -> str:
        task = str(args[0]) if args else "text"
        routing = {
            "reasoning": "mistral-7b",
            "code": "phi-2",
            "summarize": "llama-3.2-3b",
            "qa": "llama-3.2-3b",
        }
        return routing.get(task, "gemma-2-2b")

    def _kernel_ai_infer(self, args: List[Any]) -> tuple:
        task = str(args[0]) if args else "text"
        model = self._kernel_ai_route([task])
        return ("queued", 2048)

    # ═══════════════════════════════════════════════════════════
    #  GLOBAL FUNCTION CALLS
    # ═══════════════════════════════════════════════════════════

    def _call_global(self, fn_name: str, args: List[Any]) -> Any:
        fn = self.vm.functions.get(fn_name)
        if not fn:
            raise ContractCallError(f"Global function '{fn_name}' not found. Available: {list(self.vm.functions.keys())[:20]}")
        from atclang.vm.atcvm import CallFrame
        frame = CallFrame(func_name=fn_name)
        param_names = [f"arg{i}" for i in range(len(args))]
        for pname, pval in zip(param_names, args):
            frame.locals[pname] = pval
        return self.vm.execute(fn.instructions, frame)

    # ═══════════════════════════════════════════════════════════
    #  UTILITIES
    # ═══════════════════════════════════════════════════════════

    def _derive_name(self, path: str) -> str:
        base = os.path.basename(path).replace('.atc', '')
        parts = base.split('_')
        return ''.join(p.capitalize() for p in parts) if len(parts) > 1 else base

    def _default_value(self, type_hint: Any) -> Any:
        if type_hint is None:
            return None
        type_str = str(type_hint.name if hasattr(type_hint, 'name') else type_hint)
        defaults = {
            'Int': 0, 'UInt32': 0, 'UInt64': 0, 'UInt128': 0, 'UInt256': 0,
            'u8': 0, 'u16': 0, 'u32': 0, 'u64': 0, 'u128': 0,
            'i8': 0, 'i16': 0, 'i32': 0, 'i64': 0,
            'Float32': 0.0, 'f32': 0.0, 'f64': 0.0,
            'String': '', 'Bool': False, 'bool': False,
            'Address': 'ATC' + '0' * 32, 'Hash': '0' * 64,
        }
        if 'Map' in type_str:
            return {}
        if 'List' in type_str:
            return []
        return defaults.get(type_str, None)

    # ═══════════════════════════════════════════════════════════
    #  STATE PERSISTENCE
    # ═══════════════════════════════════════════════════════════

    def export_state(self) -> dict:
        return {
            "version": self.VERSION,
            "timestamp": int(time.time() * 1000),
            "modules": {
                name: {
                    "path": mod.path,
                    "source_hash": mod.source_hash,
                    "contracts": list(mod.contracts.keys()),
                    "imports": mod.imports,
                }
                for name, mod in self.modules.items()
            },
            "contracts": {
                name: {
                    "fields": c.fields,
                    "call_count": c.call_count,
                    "gas_used": c.gas_used,
                    "initialized": c.initialized,
                }
                for name, c in self.contracts.items()
            },
            "vm_stats": self.vm.stats(),
            "events": self.event_bus[-100:],
            "calls": len(self.call_log),
            "uptime_ms": int((time.time() - self._boot_time) * 1000),
        }

    def import_state(self, state: dict):
        for contract_name, contract_data in state.get("contracts", {}).items():
            if contract_name in self.contracts:
                c = self.contracts[contract_name]
                c.fields.update(contract_data.get("fields", {}))
                c.call_count = contract_data.get("call_count", 0)
                c.gas_used = contract_data.get("gas_used", 0)

    # ═══════════════════════════════════════════════════════════
    #  STATS & INFO
    # ═══════════════════════════════════════════════════════════

    def stats(self) -> dict:
        return {
            "version": self.VERSION,
            "uptime_ms": int((time.time() - self._boot_time) * 1000),
            "modules_loaded": len(self.modules),
            "contracts_loaded": len(self.contracts),
            "vm_gas_used": self.vm.gas_used,
            "vm_gas_limit": self.vm.gas_limit,
            "vm_stack_size": len(self.vm.stack),
            "vm_functions": len(self.vm.functions),
            "events_emitted": len(self.event_bus),
            "calls_made": len(self.call_log),
            "kernel_syscalls": self._syscalls_registered,
        }

    def list_modules(self) -> List[dict]:
        return [
            {
                "name": mod.name,
                "path": mod.path,
                "contracts": list(mod.contracts.keys()),
                "hash": mod.source_hash,
                "loaded_at": mod.loaded_at,
                "instructions": len(mod.compiled.instructions),
                "functions": len(mod.compiled.functions),
            }
            for mod in self.modules.values()
        ]

    def list_contracts(self) -> List[dict]:
        return [
            {
                "name": c.name,
                "fields": len(c.fields),
                "functions": len(c.functions),
                "initialized": c.initialized,
                "call_count": c.call_count,
                "gas_used": c.gas_used,
            }
            for c in self.contracts.values()
        ]

    def disassemble(self, module_name: str = None) -> str:
        if module_name and module_name in self.modules:
            from atclang.compiler.compiler import disassemble
            return disassemble(self.modules[module_name].compiled)
        return f"Module '{module_name}' not found. Available: {list(self.modules.keys())}"

    def reset(self):
        self.vm = ATCVM(gas_limit=self.vm.gas_limit)
        self.modules.clear()
        self.contracts.clear()
        self.event_bus.clear()
        self.call_log.clear()
        self._boot_time = time.time()
        self._register_kernel_stdlib()


# ════════════════════════════════════════════════════════════════
#  CONVENIENCE FUNCTIONS
# ════════════════════════════════════════════════════════════════

def create_runtime(gas_limit: int = 50_000_000) -> KernelRuntime:
    """Erstellt eine neue Kernel Runtime."""
    return KernelRuntime(gas_limit=gas_limit)


def compile_atc(path: str) -> CompiledModule:
    """Kompiliert eine .atc Datei ohne sie auszuführen."""
    source = open(path, 'r', encoding='utf-8').read()
    return compile_source(source)
