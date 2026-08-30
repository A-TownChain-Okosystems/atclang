# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Compilation Context
======================================

ATC-92 | Compiler Infrastructure

Zentrale Verwaltung des Compiler-Zustands.

Der CompilationContext kapselt:

    - Instruction-Stream
    - Constant Pool
    - Function Table
    - Symbol Scopes
    - Exports
    - Function Parameter
    - Source Map
    - Control-Flow Stacks
    - Compiler Diagnostics
    - Labels / temporäre IDs

Architektur:

    AST
     │
     ▼
    ATCCompiler
     │
     ▼
    CompilationContext
     ├── SymbolTable
     ├── Instruction Stream
     ├── Constant Pool
     ├── Functions
     ├── Exports
     ├── Source Map
     └── Control Flow
          ├── break
          └── continue

Designziele:

    1. Kein globaler Compiler-State
    2. Reentrancy für verschachtelte Compilation
    3. Saubere Scope-Verwaltung
    4. Deterministische Bytecode-Erzeugung
    5. Source-Level Debugging
    6. Vorbereitung für Optimizer und CFG
    7. Vorbereitung für Async / Capability / Contract Compilation

Der Context enthält KEINE AST-Logik.
Er ist ausschließlich Infrastruktur für den Compiler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from atclang.vm.atcvm import Instruction, OP


# ═════════════════════════════════════════════════════════════
# DIAGNOSTICS
# ═════════════════════════════════════════════════════════════

@dataclass(slots=True)
class CompilerDiagnostic:
    """
    Compiler-Diagnostic.

    severity:
        "error"
        "warning"
        "note"
    """

    message: str
    severity: str = "error"
    line: int = 0
    column: int = 0
    code: str = ""

    def format(self) -> str:
        location = ""

        if self.line > 0:
            location = f" @ {self.line}"

            if self.column > 0:
                location += f":{self.column}"

        prefix = f"[{self.severity.upper()}]"

        if self.code:
            prefix += f"[{self.code}]"

        return f"{prefix}{location}: {self.message}"


# ═════════════════════════════════════════════════════════════
# SYMBOL
# ═════════════════════════════════════════════════════════════

@dataclass(slots=True)
class Symbol:
    """
    Compiler-Symbol.

    kind:

        local
        global
        parameter
        function
        contract
        state
        type
        enum
        import
        builtin
        temporary
    """

    name: str
    kind: str
    index: int = 0
    typ: str = ""
    mutable: bool = True
    initialized: bool = False
    exported: bool = False


class SymbolTable:
    """
    Lexical Symbol Scope.

    SymbolTable bildet einen Scope-Baum:

        global
          │
          ├── function
          │     └── block
          │
          └── contract
                ├── state
                └── function
    """

    def __init__(
        self,
        parent: Optional["SymbolTable"] = None,
    ) -> None:
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self._next_index = 0

    # ──────────────────────────────────────────────────────
    # Definition
    # ──────────────────────────────────────────────────────

    def define(
        self,
        name: str,
        kind: str,
        typ: str = "",
        *,
        mutable: bool = True,
        initialized: bool = False,
        exported: bool = False,
    ) -> Symbol:
        """
        Definiert ein Symbol im aktuellen Scope.

        Raises:
            ValueError:
                Wenn der Name im aktuellen Scope bereits existiert.
        """

        if name in self.symbols:
            raise ValueError(
                f"Symbol bereits definiert: '{name}'"
            )

        symbol = Symbol(
            name=name,
            kind=kind,
            index=self._next_index,
            typ=typ,
            mutable=mutable,
            initialized=initialized,
            exported=exported,
        )

        self.symbols[name] = symbol
        self._next_index += 1

        return symbol

    # ──────────────────────────────────────────────────────
    # Lookup
    # ──────────────────────────────────────────────────────

    def resolve_local(
        self,
        name: str,
    ) -> Optional[Symbol]:
        """Nur aktuellen Scope durchsuchen."""
        return self.symbols.get(name)

    def resolve(
        self,
        name: str,
    ) -> Optional[Symbol]:
        """
        Lexical Lookup.

        Sucht vom aktuellen Scope bis zum globalen Scope.
        """

        symbol = self.symbols.get(name)

        if symbol is not None:
            return symbol

        if self.parent is not None:
            return self.parent.resolve(name)

        return None

    def contains(
        self,
        name: str,
    ) -> bool:
        return self.resolve(name) is not None

    # ──────────────────────────────────────────────────────
    # Scope
    # ──────────────────────────────────────────────────────

    def child(self) -> "SymbolTable":
        """Erzeugt einen verschachtelten Scope."""
        return SymbolTable(parent=self)

    def depth(self) -> int:
        """Berechnet die Scope-Tiefe."""
        depth = 0
        current = self.parent

        while current is not None:
            depth += 1
            current = current.parent

        return depth


# ═════════════════════════════════════════════════════════════
# CONTROL FLOW
# ═════════════════════════════════════════════════════════════

@dataclass(slots=True)
class LoopContext:
    """
    Kontext einer Schleife.

    break:
        springt zum Loop-Ende

    continue:
        springt zum Loop-Continue-Punkt
    """

    start_ip: int
    continue_ip: int
    break_jumps: List[int] = field(default_factory=list)
    continue_jumps: List[int] = field(default_factory=list)


@dataclass(slots=True)
class FunctionContext:
    """Compilation-Kontext einer Funktion."""

    name: str
    start_ip: int = 0
    params: List[str] = field(default_factory=list)

    # eigener Instruction Stream
    instructions: List[Instruction] = field(default_factory=list)

    # eigener Source Map
    source_map: List[Tuple[int, int, int]] = field(
        default_factory=list
    )


@dataclass(slots=True)
class ContractContext:
    """Compilation-Kontext eines Contracts."""

    name: str
    state_fields: Dict[str, Symbol] = field(
        default_factory=dict
    )

    functions: List[str] = field(
        default_factory=list
    )


# ═════════════════════════════════════════════════════════════
# COMPILATION CONTEXT
# ═════════════════════════════════════════════════════════════

class CompilationContext:
    """
    Zentraler Compiler-State.

    Beispiel:

        ctx = CompilationContext()

        ctx.emit(OP.PUSH, 42)
        ctx.emit(OP.STORE, "x")

        scope = ctx.push_scope()

        ctx.define_symbol(
            "x",
            "local",
            "Int"
        )

        ctx.pop_scope()

    Der Context besitzt keine Kenntnis über konkrete AST-Nodes.
    """

    def __init__(
        self,
        *,
        module_name: str = "main",
    ) -> None:

        self.module_name = module_name

        # ────────────────────────────────────────────────
        # Bytecode
        # ────────────────────────────────────────────────

        self.instructions: List[Instruction] = []

        # Constant Pool
        self.constants: List[Any] = []

        # ────────────────────────────────────────────────
        # Functions
        # ────────────────────────────────────────────────

        self.functions: Dict[
            str,
            List[Instruction]
        ] = {}

        self.function_params: Dict[
            str,
            List[str]
        ] = {}

        # ────────────────────────────────────────────────
        # Module metadata
        # ────────────────────────────────────────────────

        self.exports: List[str] = []

        self.source_map: List[
            Tuple[int, int, int]
        ] = []

        # ────────────────────────────────────────────────
        # Symbol scopes
        # ────────────────────────────────────────────────

        self.global_scope = SymbolTable()
        self.scope = self.global_scope

        # ────────────────────────────────────────────────
        # Control Flow
        # ────────────────────────────────────────────────

        self.loop_stack: List[LoopContext] = []

        # ────────────────────────────────────────────────
        # Function / Contract
        # ────────────────────────────────────────────────

        self.function_stack: List[FunctionContext] = []

        self.contract_stack: List[ContractContext] = []

        # ────────────────────────────────────────────────
        # Labels
        # ────────────────────────────────────────────────

        self._label_counter = 0

        # ────────────────────────────────────────────────
        # Temporaries
        # ────────────────────────────────────────────────

        self._temporary_counter = 0

        # ────────────────────────────────────────────────
        # Diagnostics
        # ────────────────────────────────────────────────

        self.diagnostics: List[
            CompilerDiagnostic
        ] = []

    # ═════════════════════════════════════════════════════
    # INSTRUCTIONS
    # ═════════════════════════════════════════════════════

    def emit(
        self,
        op: OP,
        *args: Any,
        line: int = 0,
        col: int = 0,
    ) -> int:
        """
        Emittiert eine Instruction.

        Returns:
            Instruction Index
        """

        index = len(self.instructions)

        instruction = Instruction(
            op,
            list(args),
        )

        self.instructions.append(instruction)

        self.source_map.append(
            (index, line, col)
        )

        return index

    def current_ip(self) -> int:
        """Aktuelle Instruction Position."""
        return len(self.instructions)

    def patch(
        self,
        index: int,
        *args: Any,
    ) -> None:
        """Patcht Instruction-Argumente."""

        if index < 0 or index >= len(self.instructions):
            raise IndexError(
                f"Invalid instruction index: {index}"
            )

        self.instructions[index].args = list(args)

    # ═════════════════════════════════════════════════════
    # CONSTANT POOL
    # ═════════════════════════════════════════════════════

    def add_constant(
        self,
        value: Any,
    ) -> int:
        """
        Fügt einen Wert deterministisch zum Constant Pool hinzu.

        Identische Werte werden dedupliziert.
        """

        for index, existing in enumerate(
            self.constants
        ):
            try:
                if existing == value:
                    return index
            except Exception:
                pass

        index = len(self.constants)
        self.constants.append(value)

        return index

    def get_constant(
        self,
        index: int,
    ) -> Any:
        return self.constants[index]

    # ═════════════════════════════════════════════════════
    # SYMBOL MANAGEMENT
    # ═════════════════════════════════════════════════════

    def define_symbol(
        self,
        name: str,
        kind: str,
        typ: str = "",
        *,
        mutable: bool = True,
        initialized: bool = False,
        exported: bool = False,
    ) -> Symbol:

        return self.scope.define(
            name,
            kind,
            typ,
            mutable=mutable,
            initialized=initialized,
            exported=exported,
        )

    def resolve_symbol(
        self,
        name: str,
    ) -> Optional[Symbol]:

        return self.scope.resolve(name)

    def require_symbol(
        self,
        name: str,
    ) -> Symbol:

        symbol = self.resolve_symbol(name)

        if symbol is None:
            raise KeyError(
                f"Undefined symbol: '{name}'"
            )

        return symbol

    # ═════════════════════════════════════════════════════
    # SCOPES
    # ═════════════════════════════════════════════════════

    def push_scope(self) -> SymbolTable:
        """Erzeugt und aktiviert einen Child-Scope."""

        self.scope = self.scope.child()
        return self.scope

    def pop_scope(self) -> SymbolTable:
        """
        Verlässt den aktuellen Scope.

        Returns:
            Der verlassene Scope.
        """

        if self.scope.parent is None:
            raise RuntimeError(
                "Cannot pop global scope"
            )

        old_scope = self.scope
        self.scope = self.scope.parent

        return old_scope

    # ═════════════════════════════════════════════════════
    # LOOP MANAGEMENT
    # ═════════════════════════════════════════════════════

    def push_loop(
        self,
        start_ip: int,
        continue_ip: Optional[int] = None,
    ) -> LoopContext:

        if continue_ip is None:
            continue_ip = start_ip

        loop = LoopContext(
            start_ip=start_ip,
            continue_ip=continue_ip,
        )

        self.loop_stack.append(loop)

        return loop

    def pop_loop(self) -> LoopContext:
        if not self.loop_stack:
            raise RuntimeError(
                "No active loop"
            )

        return self.loop_stack.pop()

    @property
    def current_loop(
        self,
    ) -> Optional[LoopContext]:

        if not self.loop_stack:
            return None

        return self.loop_stack[-1]

    def add_break_jump(
        self,
        instruction_index: int,
    ) -> None:

        loop = self.current_loop

        if loop is None:
            raise RuntimeError(
                "'break' outside loop"
            )

        loop.break_jumps.append(
            instruction_index
        )

    def add_continue_jump(
        self,
        instruction_index: int,
    ) -> None:

        loop = self.current_loop

        if loop is None:
            raise RuntimeError(
                "'continue' outside loop"
            )

        loop.continue_jumps.append(
            instruction_index
        )

    # ═════════════════════════════════════════════════════
    # FUNCTION MANAGEMENT
    # ═════════════════════════════════════════════════════

    def enter_function(
        self,
        name: str,
        params: Optional[List[str]] = None,
    ) -> FunctionContext:

        function = FunctionContext(
            name=name,
            start_ip=self.current_ip(),
            params=params or [],
        )

        self.function_stack.append(function)

        return function

    def leave_function(
        self,
    ) -> FunctionContext:

        if not self.function_stack:
            raise RuntimeError(
                "No active function"
            )

        return self.function_stack.pop()

    @property
    def current_function(
        self,
    ) -> Optional[FunctionContext]:

        if not self.function_stack:
            return None

        return self.function_stack[-1]

    # ═════════════════════════════════════════════════════
    # CONTRACT MANAGEMENT
    # ═════════════════════════════════════════════════════

    def enter_contract(
        self,
        name: str,
    ) -> ContractContext:

        contract = ContractContext(
            name=name
        )

        self.contract_stack.append(
            contract
        )

        return contract

    def leave_contract(
        self,
    ) -> ContractContext:

        if not self.contract_stack:
            raise RuntimeError(
                "No active contract"
            )

        return self.contract_stack.pop()

    @property
    def current_contract(
        self,
    ) -> Optional[ContractContext]:

        if not self.contract_stack:
            return None

        return self.contract_stack[-1]

    # ═════════════════════════════════════════════════════
    # LABELS / TEMPORARIES
    # ═════════════════════════════════════════════════════

    def new_label(self) -> int:
        """Erzeugt eine eindeutige Compiler-Label-ID."""

        value = self._label_counter
        self._label_counter += 1

        return value

    def new_temporary(
        self,
        prefix: str = "__tmp",
    ) -> str:

        value = self._temporary_counter
        self._temporary_counter += 1

        return f"{prefix}_{value}"

    # ═════════════════════════════════════════════════════
    # EXPORTS
    # ═════════════════════════════════════════════════════

    def export(
        self,
        name: str,
    ) -> None:

        if name not in self.exports:
            self.exports.append(name)

    # ═════════════════════════════════════════════════════
    # DIAGNOSTICS
    # ═════════════════════════════════════════════════════

    def error(
        self,
        message: str,
        *,
        line: int = 0,
        col: int = 0,
        code: str = "",
    ) -> None:

        diagnostic = CompilerDiagnostic(
            message=message,
            severity="error",
            line=line,
            column=col,
            code=code,
        )

        self.diagnostics.append(
            diagnostic
        )

    def warning(
        self,
        message: str,
        *,
        line: int = 0,
        col: int = 0,
        code: str = "",
    ) -> None:

        diagnostic = CompilerDiagnostic(
            message=message,
            severity="warning",
            line=line,
            column=col,
            code=code,
        )

        self.diagnostics.append(
            diagnostic
        )

    @property
    def has_errors(self) -> bool:
        return any(
            d.severity == "error"
            for d in self.diagnostics
        )

    def diagnostics_text(self) -> str:
        return "\n".join(
            diagnostic.format()
            for diagnostic in self.diagnostics
        )

    # ═════════════════════════════════════════════════════
    # STATE RESET
    # ═════════════════════════════════════════════════════

    def reset(self) -> None:
        """
        Setzt den vollständigen Compilation-State zurück.

        Der Context kann anschließend für eine neue
        Compilation verwendet werden.
        """

        self.instructions.clear()
        self.constants.clear()
        self.functions.clear()
        self.function_params.clear()
        self.exports.clear()
        self.source_map.clear()

        self.global_scope = SymbolTable()
        self.scope = self.global_scope

        self.loop_stack.clear()
        self.function_stack.clear()
        self.contract_stack.clear()

        self.diagnostics.clear()

        self._label_counter = 0
        self._temporary_counter = 0

    # ═════════════════════════════════════════════════════
    # SNAPSHOT
    # ═════════════════════════════════════════════════════

    def snapshot(self) -> Dict[str, Any]:
        """
        Lightweight Compiler-State Snapshot.

        Primär für Debugging, Tests und Compiler-Introspection.
        """

        return {
            "module": self.module_name,
            "instruction_count": len(
                self.instructions
            ),
            "constant_count": len(
                self.constants
            ),
            "function_count": len(
                self.functions
            ),
            "export_count": len(
                self.exports
            ),
            "scope_depth": self.scope.depth(),
            "loop_depth": len(
                self.loop_stack
            ),
            "function_depth": len(
                self.function_stack
            ),
            "contract_depth": len(
                self.contract_stack
            ),
            "diagnostic_count": len(
                self.diagnostics
            ),
            "has_errors": self.has_errors,
        }


__all__ = [
    "CompilerDiagnostic",
    "Symbol",
    "SymbolTable",
    "LoopContext",
    "FunctionContext",
    "ContractContext",
    "CompilationContext",
]