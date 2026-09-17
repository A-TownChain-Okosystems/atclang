# src/atclang/ — Referenz-Implementierung (Pipeline)

*57 Dateien, 23003 Zeilen — AST-generiert*


## Paket `abi`
*ABI-Definition (Call-/Callee-Views, Funktions-ABI)*

### `src/atclang/abi/__init__.py` (5 Zeilen)

> ATCLang ABI — kanonische Wert-Kodierung und Methoden-Selektoren (ATC-92 §ABI).


### `src/atclang/abi/codec.py` (156 Zeilen)

> ATCLang ABI Codec — kanonische Kodierung von Argument- und Rückgabewerten.
> 
> Wire-Format (big-endian, deterministisch, 32-Byte-Ausrichtung wie ATC-8300):
> - UInt/Int (U8..U256/I256): vorzeichenbehaftete/notierte Ganzzahl, rechts-

- **`class ABIError`** — ABI-Kodierungs-/Dekodierungsfehler.
- **`def canonical_signature(name: str, params: Sequence[str]) -> str`** — fn transfer(to: Address, amount: UInt256) -> 'transfer(Address,UInt256)'.
- **`def method_selector(name: str, params: Sequence[str]) -> str`** — 4-Byte-Methoden-ID aus SHA3-256 der kanonischen Signatur (hex 0x…).
- **`class ABICodec`** — Kanonischer Wert-Codec für ATCLang-ABI-Typen (ATC-8300-kompatibel).
  - `encode(self, value: Any, abi_type: str) -> bytes` — 
  - `encode_call(self, selector: str, values: Sequence[Any], abi_types: Sequence[str]) -> bytes` — Call-Payload = Selektor || kanonisch verkettete Argumente.
  - `decode(self, data: bytes, abi_type: str, offset: int=0) -> tuple[Any, int]` — 


## Paket `artifact`
*Artefakt-Handling (ATC-Artefakt-Format)*

### `src/atclang/artifact/__init__.py` (5 Zeilen)

> ATCLang Artifact — deterministische kompilierte Artefakte (.atca).


### `src/atclang/artifact/artifact.py` (115 Zeilen)

> CompiledArtifact — das transportable Compile-Ergebnis (.atca).
> 
> Governance-Kopplung: Artefakt-Record nach ATC-STD-043 (Artifact Integrity,
> 9 Felder) und Reproducible Builds (ATC-STD-041): kanonische JSON-Serialisierung

- **`class ArtifactError`** — 
- **`class CompiledArtifact`** — Deterministisch serialisierbares Compile-Artefakt.
  - `canonical_payload(self) -> bytes` — Kanonische JSON-Serialisierung (Determinismus-Pflicht).
  - `artifact_id(self) -> str` — 
  - `to_bytes(self) -> bytes` — Wire-Format: ATCA-Header + kanonischer Payload.
  - `from_bytes(cls, raw: bytes) -> CompiledArtifact` — 
  - `validate(self) -> None` — ATC-STD-043-Feldpruefung (9 Pflichtfelder).


## Paket `cli`
*Kommandozeilen-Frontend*

### `src/atclang/cli/__init__.py` (5 Zeilen)

> ATCLang CLI — atc compile | check | ir | deploy (ATC-92 Tooling).


### `src/atclang/cli/main.py` (133 Zeilen)

> atc-CLI: Kompilieren, Pruefen, IR-Dump, Artifacts schreiben.
> 
>     atc compile <file.atc> [--profile consensus] [--out artifact.atca]
>     atc check   <file.atc> [--profile consensus]     # SecurityGate + Semantik

- **`def _load(path: str) -> str`** — 
- **`def cmd_compile(args) -> int`** — 
- **`def cmd_check(args) -> int`** — 
- **`def cmd_ir(args) -> int`** — 
- **`def main(argv=None) -> int`** — 


## Paket `compiler`
*Bytecode-Compiler (kontrollfluss, konstanten, ausdruecke, funktionen, klassen, ...)*

### `src/atclang/compiler/__init__.py` (84 Zeilen)

> ATCLang Compiler Package
> ========================
> 
> Public compiler API for ATCLang.


### `src/atclang/compiler/bytecode.py` (1612 Zeilen)

> ATCLang Compiler — Bytecode
> ===========================
> 
> Zentrale Bytecode-Datenstrukturen für ATCLang v0.3.1.

- **`class BytecodeLimits`** — Modulweite Bytecode-Grenzen.
- **`class BytecodeError`** — Base exception for bytecode errors.
- **`class BytecodeValidationError`** — Raised when bytecode violates compiler invariants.
- **`class BytecodeFormatError`** — Raised when serialized bytecode has an invalid format.
- **`def _require_exact_int(value: Any, *, name: str, minimum: int | None=None, maximum: int | None=None) -> None`** — Validate an exact Python int.
- **`def _validate_identifier(value: Any, *, name: str, maximum_length: int | None=None) -> None`** — Validate a compiler identifier-like string.
- **`class Instruction`** — Single ATC VM instruction.
  - `copy(self) -> Instruction` — 
  - `opcode_name(self) -> str` — Return a stable human-readable opcode name.
  - `to_dict(self) -> dict[str, Any]` — 
- **`class FunctionBytecode`** — Compiled function metadata.
  - `validate(self) -> None` — 
  - `to_dict(self) -> dict[str, Any]` — 
- **`class SourceMapEntry`** — Maps an instruction index to a source position.
  - `to_tuple(self) -> tuple[int, int, int]` — 
  - `to_dict(self) -> dict[str, int]` — 
- **`class SourceMap`** — Canonical source-map container.
  - `validate(self, *, instruction_count: int | None=None) -> None` — 
  - `add(self, instruction: int, line: int, column: int=UNKNOWN_SOURCE_COLUMN) -> None` — 
  - `lookup(self, instruction: int) -> SourceMapEntry | None` — 
  - `to_list(self) -> list[tuple[int, int, int]]` — 
  - `from_list(cls, entries: Iterable[Sequence[int]], version: int=SOURCE_MAP_VERSION) -> SourceMap` — 
- **`class CompiledModule`** — Complete compiler output.
  - `constant_pool(self) -> ConstantPool` — Canonical ConstantPool accessor.
  - `summary(self) -> str` — 
  - `instruction_count(self) -> int` — 
  - `function_count(self) -> int` — 
  - `constant_count(self) -> int` — 
  - `export_count(self) -> int` — 
  - `get_function(self, name: str) -> list[Instruction] | None` — 
  - `get_function_parameters(self, name: str) -> list[str]` — 
  - `source_location(self, instruction: int) -> SourceMapEntry | None` — 
  - `validate(self) -> None` — 
  - `freeze_constants(self) -> None` — Freeze the canonical ConstantPool.
  - `constants_frozen(self) -> bool` — 
  - `to_dict(self) -> dict[str, Any]` — Deterministische JSON-kompatible Darstellung.
  - `to_json(self, *, indent: int | None=2) -> str` — 
  - `disassemble(self, *, include_source_map: bool=False) -> str` — 
- **`class BytecodeBuilder`** — Stateful helper für Compiler-Komponenten.
  - `__init__(self) -> None` — 
  - `emit(self, op: Any, *args: Any, line: int=UNKNOWN_SOURCE_LINE, column: int=UNKNOWN_SOURCE_COLUMN) -> int` — 
  - `patch(self, index: int, *args: Any) -> None` — 
  - `current_position(self) -> int` — 
  - `build(self) -> list[Instruction]` — 
- **`def disassemble(module: CompiledModule, *, include_source_map: bool=False) -> str`** — Human-readable ATC Bytecode Disassembly.
- **`def _format_constant(constant: Constant) -> str`** — 
- **`def _format_instruction(index: int, instruction: Instruction, *, source_map: list[tuple[int, int, int]] | None=None) -> str`** — 
- **`def _lookup_source_map(source_map: list[tuple[int, int, int]], instruction: int) -> tuple[int, int, int] | None`** — 
- **`def serialize_json(module: CompiledModule, *, indent: int | None=2) -> bytes`** — Serialize module into UTF-8 JSON.
- **`def write_json(module: CompiledModule, path: str, *, indent: int | None=2) -> None`** — 
- **`def encode_container(module: CompiledModule) -> bytes`** — Encode a versioned ATCB outer container.
- **`def decode_container(data: bytes) -> dict[str, Any]`** — Decode the outer ATCB container.
- **`def write_container(module: CompiledModule, path: str) -> None`** — 
- **`def read_container(path: str) -> dict[str, Any]`** — 
- **`def add_constant(constants: ConstantPool | list[Any], value: Any) -> int`** — Compatibility helper.
- **`def _json_safe(value: Any) -> Any`** — Convert compiler values into deterministic JSON-compatible data.

### `src/atclang/compiler/bytecode_abi.py` (1652 Zeilen)

> ATCLang Bytecode ABI v1.0
> =========================
> 
> Normative Binary Application Binary Interface für ATCLang / ATC-92.

- **`class SectionType`** — Normative ATCB section identifiers.
- **`class ABIConstantType`** — Normative ATC-92 constant type identifiers.
- **`class OperandType`** — Normative instruction operand encodings.
- **`class ABIMetadata`** — Metadata encoded in the METADATA section.
  - `validate(self) -> None` — 
- **`class ABISection`** — Complete ABI section.
  - `encode(self) -> bytes` — 
- **`def _require_exact_int(value: Any, *, name: str, minimum: int | None=None, maximum: int | None=None) -> None`** — 
- **`def _require_string(value: Any, name: str) -> None`** — 
- **`def _require_bytes(value: Any, name: str) -> None`** — 
- **`def _require_available(data: bytes, offset: int, length: int) -> None`** — 
- **`def encode_u8(value: int) -> bytes`** — 
- **`def decode_u8(data: bytes, offset: int=0) -> tuple[int, int]`** — 
- **`def encode_u16(value: int) -> bytes`** — 
- **`def decode_u16(data: bytes, offset: int=0) -> tuple[int, int]`** — 
- **`def encode_u32(value: int) -> bytes`** — 
- **`def decode_u32(data: bytes, offset: int=0) -> tuple[int, int]`** — 
- **`def encode_u64(value: int) -> bytes`** — 
- **`def decode_u64(data: bytes, offset: int=0) -> tuple[int, int]`** — 
- **`def encode_i64(value: int) -> bytes`** — 
- **`def decode_i64(data: bytes, offset: int=0) -> tuple[int, int]`** — 
- **`def encode_f64(value: float) -> bytes`** — 
- **`def decode_f64(data: bytes, offset: int=0) -> tuple[float, int]`** — 
- **`def encode_bytes(value: bytes) -> bytes`** — 
- **`def decode_bytes(data: bytes, offset: int=0) -> tuple[bytes, int]`** — 
- **`def encode_string(value: str) -> bytes`** — 
- **`def decode_string(data: bytes, offset: int=0) -> tuple[str, int]`** — 
- **`def _constant_type(constant: Constant) -> ABIConstantType`** — 
- **`def _encode_constant_payload(constant_type: ABIConstantType, value: Any) -> bytes`** — 
- **`def encode_constant(constant: Constant) -> bytes`** — Constant record:
- **`def encode_constant_pool(pool: ConstantPool) -> bytes`** — Constant pool:
- **`def _infer_operand_type(value: Any) -> OperandType`** — 
- **`def _encode_operand_payload(operand_type: OperandType, value: Any) -> bytes`** — 
- **`def encode_operand(value: Any) -> bytes`** — 
- **`def opcode_value(op: Any) -> int`** — Convert an opcode to the normative u8 representation.
- **`def encode_instruction(instruction: Instruction) -> bytes`** — Instruction:
- **`def encode_instruction_stream(instructions: Sequence[Instruction]) -> bytes`** — Instruction stream:
- **`def encode_function(function: FunctionBytecode) -> bytes`** — Function:
- **`def encode_functions(functions: Mapping[str, Sequence[Instruction]], function_params: Mapping[str, Sequence[str]], exports: Sequence[str]) -> bytes`** — 
- **`def encode_exports(exports: Sequence[str]) -> bytes`** — 
- **`def encode_source_map(source_map: Iterable[Sequence[int]]) -> bytes`** — Source-map v1:
- **`def encode_metadata(module: CompiledModule) -> bytes`** — 
- **`def build_sections(module: CompiledModule) -> list[ABISection]`** — 
- **`def _encode_header(*, section_count: int, payload_length: int) -> bytes`** — 
- **`def encode_module(module: CompiledModule) -> bytes`** — Encode a CompiledModule into canonical ATCB ABI v1.0.
- **`def decode_header(data: bytes) -> dict[str, Any]`** — 
- **`def decode_sections(data: bytes) -> list[ABISection]`** — 
- **`def validate_binary(data: bytes) -> None`** — Validate the ATCB container structure without executing bytecode.
- **`def write_abi(module: CompiledModule, path: str) -> None`** — 
- **`def read_abi(path: str) -> bytes`** — 
- **`def abi_info() -> dict[str, Any]`** — Return machine-readable normative ABI information.

### `src/atclang/compiler/compiler.py` (2115 Zeilen)

> ATCLang Compiler
> ================
> 
> ATCLang AST -> ATC Bytecode compiler.

- **`class CompileError`** — Raised when AST compilation fails.
  - `__init__(self, message: str, *, line: int | None=None, col: int | None=None) -> None` — 
- **`class SourceLocation`** — Maps bytecode instruction to source location.
- **`class Symbol`** — Compiler symbol.
- **`class SymbolTable`** — Hierarchical compiler symbol table.
  - `__init__(self, parent: SymbolTable | None=None) -> None` — 
  - `define(self, name: str, kind: str, typ: str='') -> Symbol` — 
  - `define_or_get(self, name: str, kind: str, typ: str='') -> Symbol` — 
  - `resolve(self, name: str) -> Symbol | None` — 
  - `child(self) -> SymbolTable` — 
  - `contains_local(self, name: str) -> bool` — 
- **`class CompiledModule`** — Result of ATCLang compilation.
  - `summary(self) -> str` — 
- **`class ATCCompiler`** — ATCLang AST -> ATC bytecode compiler.
  - `__init__(self, *, module_name: str='main') -> None` — 
  - `error(self, message: str, node: ASTNode | None=None) -> None` — 
  - `emit(self, op: OP, *args: Any, line: int=0, col: int=0) -> int` — Emit one instruction.
  - `patch(self, instruction_index: int, *args: Any) -> None` — Patch a previously emitted instruction.
  - `current_pos(self) -> int` — 
  - `add_constant(self, value: Any) -> int` — Add value to module constant pool.
  - `new_temp(self, prefix: str='__tmp') -> str` — 
  - `compile_expr(self, node: ASTNode, scope: SymbolTable) -> None` — Compile an expression and leave its result on the VM stack.
  - `compile_call(self, node: FunctionCall, scope: SymbolTable) -> None` — Compile function, method or external calls.
  - `compile_assignment(self, node: Assignment, scope: SymbolTable) -> None` — Compile assignment expressions.
  - `compile_ternary(self, node: TernaryExpr, scope: SymbolTable) -> None` — Compile:
  - `compile_stmt(self, node: ASTNode, scope: SymbolTable) -> None` — Compile one statement.
  - `compile_if(self, node: IfStatement, scope: SymbolTable) -> None` — Compile:
  - `compile_while(self, node: WhileStatement, scope: SymbolTable) -> None` — Compile:
  - `compile_for(self, node: ForStatement, scope: SymbolTable) -> None` — Lower:
  - `compile_if_toplevel(self, node: IfStatement, scope: SymbolTable) -> None` — Compile top-level if without automatically POP-ing expression
  - `compile_function(self, fn: FunctionDef) -> list[Instruction]` — Compile function into an independent instruction stream.
  - `compile_contract(self, contract: ContractDef) -> None` — Compile contract state initialization and functions.
  - `compile_program(self, program: Program) -> CompiledModule` — Compile complete ATCLang program.
- **`def compile_source(source: str, *, module_name: str='main', semantic_check: bool=True) -> CompiledModule`** — Compile ATCLang source directly.
- **`def disassemble(module: CompiledModule) -> str`** — Human-readable ATC bytecode disassembly.

### `src/atclang/compiler/constants.py` (1166 Zeilen)

> ATCLang Compiler Constant Pool
> ==============================
> 
> Zentrales Constant-Pool-System des ATCLang Compilers.

- **`class ConstantType`** — Kanonische Konstantentypen des ATCLang Constant Pools.
- **`class ConstantPoolLimits`** — Zentrale Limits des Constant Pools.
- **`def _constant_error(message: str) -> ConstantPoolError`** — Erzeugt einen standardisierten ConstantPoolError.
- **`def _require_exact_int(value: Any, *, name: str, minimum: int | None=None, maximum: int | None=None) -> None`** — Validiert einen echten Python-int.
- **`def _payload_size(constant_type: ConstantType, value: Any) -> int`** — Berechnet die semantische Payload-Größe einer Konstante.
- **`def _validate_constant_value(constant_type: ConstantType, value: Any) -> None`** — Validiert einen Konstantenwert gegen seinen ConstantType.
- **`def infer_constant_type(value: Any) -> ConstantType`** — Ermittelt den kanonischen ConstantType eines Python-Wertes.
- **`def _constant_key(constant_type: ConstantType, value: Any) -> tuple[ConstantType, Any]`** — Erzeugt einen stabilen Deduplication-Key.
- **`class Constant`** — Immutable Constant-Pool-Entry.
  - `to_dict(self) -> dict` — Erstellt eine JSON-kompatible Repräsentation.
  - `from_dict(cls, data: dict) -> Constant` — Rekonstruiert eine Constant aus einer serialisierten Struktur.
- **`class ConstantPool`** — Deterministischer ATCLang Constant Pool.
  - `__init__(self, *, max_size: int=DEFAULT_MAX_SIZE, max_total_payload_bytes: int=ConstantPoolLimits.MAX_TOTAL_PAYLOAD_BYTES) -> None` — 
  - `is_frozen(self) -> bool` — Gibt an, ob der Pool eingefroren wurde.
  - `freeze(self) -> None` — Friert den Constant Pool ein.
  - `add(self, value: Any, *, constant_type: ConstantType | None=None) -> int` — Fügt eine Konstante hinzu und gibt ihren Index zurück.
  - `add_null(self) -> int` — Fügt eine NULL-Konstante hinzu.
  - `add_bool(self, value: bool) -> int` — Fügt eine Boolean-Konstante hinzu.
  - `add_int(self, value: int) -> int` — Fügt eine Integer-Konstante hinzu.
  - `add_float(self, value: float) -> int` — Fügt eine Float-Konstante hinzu.
  - `add_string(self, value: str) -> int` — Fügt eine String-Konstante hinzu.
  - `add_bytes(self, value: bytes) -> int` — Fügt eine Bytes-Konstante hinzu.
  - `get(self, index: int) -> Constant` — Liefert eine Constant anhand ihres Index.
  - `find(self, value: Any, *, constant_type: ConstantType | None=None) -> int | None` — Sucht eine Konstante, ohne sie hinzuzufügen.
  - `contains(self, value: Any, *, constant_type: ConstantType | None=None) -> bool` — Prüft, ob eine Konstante vorhanden ist.
  - `size(self) -> int` — Aktuelle Anzahl der Konstanten.
  - `is_full(self) -> bool` — Gibt an, ob der Pool sein Entry-Limit erreicht hat.
  - `total_payload_bytes(self) -> int` — Aktuelle semantische Payload-Größe.
  - `constants(self) -> tuple[Constant, ...]` — Read-only Sicht auf alle Constant Entries.
  - `to_dict(self) -> list[dict]` — Serialisiert den vollständigen Constant Pool.
  - `from_dict(cls, data: Iterable[dict], *, max_size: int=DEFAULT_MAX_SIZE, max_total_payload_bytes: int=ConstantPoolLimits.MAX_TOTAL_PAYLOAD_BYTES) -> ConstantPool` — Rekonstruiert einen Constant Pool.
  - `copy(self) -> ConstantPool` — Erstellt eine unabhängige Kopie des Constant Pools.
  - `clear(self) -> None` — Leert den Constant Pool.
- **`class ConstantPoolBuilder`** — Convenience-Builder für Compiler-Komponenten.
  - `__init__(self, *, max_size: int=ConstantPool.DEFAULT_MAX_SIZE, max_total_payload_bytes: int=ConstantPoolLimits.MAX_TOTAL_PAYLOAD_BYTES) -> None` — 
  - `literal(self, value: Any) -> int` — Registriert ein Literal.
  - `null(self) -> int` — Registriert null.
  - `boolean(self, value: bool) -> int` — Registriert einen Boolean.
  - `integer(self, value: int) -> int` — Registriert einen Integer.
  - `floating(self, value: float) -> int` — Registriert einen Float.
  - `string(self, value: str) -> int` — Registriert einen String.
  - `bytes(self, value: bytes) -> int` — Registriert Bytes.
  - `freeze(self) -> None` — Friert den zugrunde liegenden Pool ein.
  - `build(self) -> ConstantPool` — Gibt den aufgebauten Constant Pool zurück.

### `src/atclang/compiler/context.py` (841 Zeilen)

> ATCLang Compiler — Compilation Context
> ======================================
> 
> ATC-92 | Compiler Infrastructure

- **`class CompilerDiagnostic`** — Compiler-Diagnostic.
  - `format(self) -> str` — 
- **`class Symbol`** — Compiler-Symbol.
- **`class SymbolTable`** — Lexical Symbol Scope.
  - `__init__(self, parent: SymbolTable | None=None) -> None` — 
  - `define(self, name: str, kind: str, typ: str='', *, mutable: bool=True, initialized: bool=False, exported: bool=False) -> Symbol` — Definiert ein Symbol im aktuellen Scope.
  - `resolve_local(self, name: str) -> Symbol | None` — Nur aktuellen Scope durchsuchen.
  - `resolve(self, name: str) -> Symbol | None` — Lexical Lookup.
  - `contains(self, name: str) -> bool` — 
  - `child(self) -> SymbolTable` — Erzeugt einen verschachtelten Scope.
  - `depth(self) -> int` — Berechnet die Scope-Tiefe.
- **`class LoopContext`** — Kontext einer Schleife.
- **`class FunctionContext`** — Compilation-Kontext einer Funktion.
- **`class ContractContext`** — Compilation-Kontext eines Contracts.
- **`class CompilationContext`** — Zentraler Compiler-State.
  - `__init__(self, *, module_name: str='main') -> None` — 
  - `emit(self, op: OP, *args: Any, line: int=0, col: int=0) -> int` — Emittiert eine Instruction.
  - `current_ip(self) -> int` — Aktuelle Instruction Position.
  - `patch(self, index: int, *args: Any) -> None` — Patcht Instruction-Argumente.
  - `add_constant(self, value: Any) -> int` — Fügt einen Wert deterministisch zum Constant Pool hinzu.
  - `get_constant(self, index: int) -> Any` — 
  - `define_symbol(self, name: str, kind: str, typ: str='', *, mutable: bool=True, initialized: bool=False, exported: bool=False) -> Symbol` — 
  - `resolve_symbol(self, name: str) -> Symbol | None` — 
  - `require_symbol(self, name: str) -> Symbol` — 
  - `push_scope(self) -> SymbolTable` — Erzeugt und aktiviert einen Child-Scope.
  - `pop_scope(self) -> SymbolTable` — Verlässt den aktuellen Scope.
  - `push_loop(self, start_ip: int, continue_ip: int | None=None) -> LoopContext` — 
  - `pop_loop(self) -> LoopContext` — 
  - `current_loop(self) -> LoopContext | None` — 
  - `add_break_jump(self, instruction_index: int) -> None` — 
  - `add_continue_jump(self, instruction_index: int) -> None` — 
  - `enter_function(self, name: str, params: list[str] | None=None) -> FunctionContext` — 
  - `leave_function(self) -> FunctionContext` — 
  - `current_function(self) -> FunctionContext | None` — 
  - `enter_contract(self, name: str) -> ContractContext` — 
  - `leave_contract(self) -> ContractContext` — 
  - `current_contract(self) -> ContractContext | None` — 
  - `new_label(self) -> int` — Erzeugt eine eindeutige Compiler-Label-ID.
  - `new_temporary(self, prefix: str='__tmp') -> str` — 
  - `export(self, name: str) -> None` — 
  - `error(self, message: str, *, line: int=0, col: int=0, code: str='') -> None` — 
  - `warning(self, message: str, *, line: int=0, col: int=0, code: str='') -> None` — 
  - `has_errors(self) -> bool` — 
  - `diagnostics_text(self) -> str` — 
  - `reset(self) -> None` — Setzt den vollständigen Compilation-State zurück.
  - `snapshot(self) -> dict[str, Any]` — Lightweight Compiler-State Snapshot.

### `src/atclang/compiler/contracts.py` (502 Zeilen)

> ATCLang Compiler — Contract Compilation
> =======================================
> 
> ATC-92 | ATCLang v0.3.x

- **`class ContractCompiler`** — Kompiliert ATCLang Contracts in ATC-Bytecode.
  - `__init__(self, context: CompilerContext)` — 
  - `compile(self, contract: ContractDef) -> None` — Kompiliert einen vollständigen Contract.
- **`def compile_contract(contract: ContractDef, context: CompilerContext) -> None`** — Convenience API.

### `src/atclang/compiler/control_flow.py` (932 Zeilen)

> ATCLang Compiler — Control Flow
> ================================
> 
> ATC-92 | Compiler Backend

- **`class ControlFlowError`** — Fehler während der Control-Flow-Kompilierung.
- **`class LoopContext`** — Kontext eines aktiven Loops.
- **`class IfContext`** — Temporärer Kontext einer if/elif/else-Kette.
- **`class ControlFlowCompiler`** — Compiler für Control-Flow-Konstrukte.
  - `__init__(self, compiler: Any, compile_expr: ExpressionCompiler | None=None, compile_stmt: StatementCompiler | None=None) -> None` — 
  - `instructions(self) -> list[Instruction]` — 
  - `emit(self, op: OP, *args: Any, node: Any | None=None) -> int` — Delegiert Instruction-Emission an den Hauptcompiler.
  - `patch(self, index: int, *args: Any) -> None` — Patcht ein Jump-Target.
  - `current_pos(self) -> int` — 
  - `set_callbacks(self, compile_expr: ExpressionCompiler, compile_stmt: StatementCompiler) -> None` — Setzt Compiler-Callbacks.
  - `compile_block(self, statements: Sequence[Any], scope: Any) -> None` — Kompiliert einen Statement-Block.
  - `compile_if(self, node: Any, scope: Any, *, preserve_result: bool=False) -> None` — Kompiliert:
  - `compile_while(self, node: Any, scope: Any) -> None` — Kompiliert:
  - `compile_for(self, node: Any, scope: Any) -> None` — Kompiliert einen generischen for-loop.
  - `compile_break(self, node: Any) -> None` — Kompiliert break.
  - `compile_continue(self, node: Any) -> None` — Kompiliert continue.
  - `compile(self, node: Any, scope: Any, *, preserve_result: bool=False) -> bool` — Allgemeiner Dispatcher.
  - `loop_depth(self) -> int` — Aktuelle Verschachtelungstiefe der Loops.
  - `in_loop(self) -> bool` — True, wenn aktuell innerhalb eines Loops kompiliert wird.
  - `current_loop(self) -> LoopContext | None` — Gibt den innersten Loop-Kontext zurück.

### `src/atclang/compiler/errors.py` (932 Zeilen)

> ATCLang Compiler Errors
> =======================
> 
> Zentrales, unabhängiges Error- und Diagnostic-System des Compilers.

- **`class ErrorSeverity`** — Schweregrad einer Compiler-Diagnose.
- **`class SourceLocation`** — Einzelne Position im ATCLang-Quelltext.
  - `is_known(self) -> bool` — Gibt an, ob die Position bekannt ist.
  - `format(self) -> str` — Formatiert die Position für eine Diagnostic.
- **`class SourceSpan`** — Bereich im ATCLang-Quelltext.
  - `from_node(cls, node: Any) -> SourceSpan` — Erstellt einen SourceSpan aus einem AST-Node.
  - `line(self) -> int` — 
  - `column(self) -> int` — 
  - `is_known(self) -> bool` — 
  - `format(self) -> str` — Formatiert den Source-Bereich.
- **`class CompilerDiagnostic`** — Strukturierte Compiler-Diagnose.
  - `format(self) -> str` — Erzeugt eine deterministische Textdarstellung.
- **`class CompileErrorCode`** — Zentrale ATCLang Compiler Error-Codes.
- **`class CompileError`** — Basisklasse aller ATCLang Compiler-Fehler.
  - `__init__(self, message: str, *, code: str | None=None, node: Any=None, span: SourceSpan | None=None, hint: str | None=None, note: str | None=None) -> None` — 
  - `format(self) -> str` — 
- **`class CompileSyntaxError`** — Compiler-Syntax-/AST-Fehler.
- **`class InvalidASTError`** — AST entspricht nicht den Compiler-Anforderungen.
- **`class CompileNameError`** — Fehler bei Symbolauflösung.
- **`class UndefinedSymbolError`** — Symbol wurde nicht gefunden.
  - `__init__(self, name: str, *, node: Any=None, hint: str | None=None) -> None` — 
- **`class DuplicateSymbolError`** — Symbol wurde mehrfach definiert.
  - `__init__(self, name: str, *, node: Any=None) -> None` — 
- **`class InvalidScopeError`** — Ungültiger Scope-Kontext.
- **`class CompileTypeError`** — Statischer Typfehler.
- **`class TypeMismatchError`** — Inkompatible Typen.
  - `__init__(self, expected: str, actual: str, *, node: Any=None, hint: str | None=None) -> None` — 
- **`class InvalidCastError`** — Nicht erlaubter Cast.
- **`class InvalidOperationError`** — Nicht erlaubte Operation für einen Typ.
- **`class UnknownTypeError`** — Unbekannter Typ.
- **`class InvalidGenericError`** — Ungültige generische Typdefinition.
- **`class CompileControlFlowError`** — Fehler in der Kontrollflussanalyse.
- **`class BreakOutsideLoopError`** — break außerhalb einer Schleife.
- **`class ContinueOutsideLoopError`** — continue außerhalb einer Schleife.
- **`class InvalidReturnError`** — Ungültiges return.
- **`class UnreachableCodeError`** — Nicht erreichbarer Code.
- **`class CompileFunctionError`** — Fehler beim Kompilieren einer Funktion.
- **`class InvalidCallError`** — Ungültiger Funktionsaufruf.
- **`class ArgumentCountError`** — Falsche Anzahl von Argumenten.
  - `__init__(self, function_name: str, expected: int, actual: int, *, node: Any=None) -> None` — 
- **`class DuplicateParameterError`** — Doppelter Funktionsparameter.
- **`class InvalidFunctionError`** — Ungültige Funktionsdefinition.
- **`class CompileContractError`** — Fehler beim Kompilieren eines Contracts.
- **`class InvalidContractError`** — Ungültige Contract-Struktur.
- **`class InvalidStateError`** — Ungültiger Contract-State.
- **`class InvalidEventError`** — Ungültige Event-Definition.
- **`class InvalidErrorDefinitionError`** — Ungültige Contract-Error-Definition.
- **`class InvalidStorageError`** — Ungültige Storage-Definition.
- **`class CompileBytecodeError`** — Fehler beim Erzeugen von ATC-Bytecode.
- **`class InvalidOpcodeError`** — Ungültiger Opcode.
- **`class InvalidOperandError`** — Ungültiger Bytecode-Operand.
- **`class InvalidJumpError`** — Ungültiges Sprungziel.
- **`class InvalidBytecodeError`** — Strukturell ungültiger Bytecode.
- **`class ConstantPoolError`** — Fehler im Constant Pool.
- **`class ConstantPoolOverflowError`** — Constant Pool hat die maximale Größe überschritten.
- **`class InvalidConstantError`** — Ungültiger Constant-Pool-Eintrag.
- **`class OptimizationError`** — Fehler während einer Optimierung.
- **`class InvalidOptimizationError`** — Optimierung erzeugt einen ungültigen Zustand.
- **`class CompileInternalError`** — Interner Compilerfehler.
- **`def location_from_node(node: Any) -> SourceSpan | None`** — Konvertiert einen AST-Node sicher in einen SourceSpan.
- **`def raise_compile_error(message: str, *, code: str=CompileErrorCode.GENERAL, node: Any=None, span: SourceSpan | None=None, hint: str | None=None, note: str | None=None) -> None`** — Convenience-Helper zum Werfen eines CompileError.

### `src/atclang/compiler/expressions.py` (965 Zeilen)

> ATCLang Compiler — Expression Compilation
> ==========================================
> 
> Compiles ATCLang AST expressions into ATC bytecode.

- **`class ExpressionCompiler`** — Compile ATCLang expressions into ATC bytecode.
  - `__init__(self, context: CompilerContext)` — 
  - `compile(self, node: ASTNode, *, scope=None) -> None` — Compile one expression.
  - `error(self, message: str, node: ASTNode | None=None) -> None` — Raise a compiler error with source location.
- **`def compile_expression(context: CompilerContext, node: ASTNode, scope=None) -> None`** — Functional API for callers that do not need a persistent

### `src/atclang/compiler/functions.py` (670 Zeilen)

> ATCLang Function Compiler
> =========================
> 
> Function-level compilation for ATCLang.

- **`class CompiledFunction`** — Result of compiling one ATCLang function.
  - `instruction_count(self) -> int` — 
- **`class FunctionCompiler`** — Compiles ATCLang FunctionDef nodes.
  - `__init__(self, context: CompilerContext)` — 
  - `compile(self, function: FunctionDef, *, qualified_name: str | None=None) -> CompiledFunction` — Compile a FunctionDef into an isolated instruction stream.
  - `compile_many(self, functions: list[FunctionDef], *, namespace: str | None=None) -> dict[str, CompiledFunction]` — Compile multiple functions deterministically.
- **`class FunctionCompileError`** — Function-level compiler error.
  - `__init__(self, message: str, *, line: int=0, column: int=0)` — 
- **`def compile_function(context: CompilerContext, function: FunctionDef, *, qualified_name: str | None=None) -> CompiledFunction`** — Convenience wrapper around FunctionCompiler.
- **`def compile_functions(context: CompilerContext, functions: list[FunctionDef], *, namespace: str | None=None) -> dict[str, CompiledFunction]`** — Convenience wrapper for compiling multiple functions.

### `src/atclang/compiler/optimizer.py` (1152 Zeilen)

> ATCLang Optimizer
> =================
> 
> ATC-92 | Compiler Optimization Pipeline

- **`class OptimizerConfig`** — Optimizer configuration.
  - `normalized(self) -> OptimizerConfig` — 
- **`class OptimizationStats`** — 
  - `as_dict(self) -> dict[str, int]` — 
  - `reset(self) -> None` — 
- **`class ConstantInfo`** — 
- **`class ATCOptimizer`** — ATCLang AST + bytecode optimizer.
  - `__init__(self, level: int=1, config: OptimizerConfig | None=None)` — 
  - `optimize_ast(self, program: Program) -> Program` — Optimize an AST in-place and return it.
  - `optimize_bytecode(self, instructions: list[Instruction]) -> list[Instruction]` — Optimize one bytecode instruction stream.
  - `get_stats(self) -> dict[str, int]` — 
  - `reset_stats(self) -> None` — 

### `src/atclang/compiler/source_map.py` (653 Zeilen)

> ATCLang Compiler Source Map
> ===========================
> 
> Source-Mapping-System des ATCLang Compilers.

- **`class SourceMapEntry`** — Mapping eines Bytecode-Bereichs auf einen Source-Bereich.
  - `length(self) -> int` — Anzahl der gemappten Bytecode-Instructions.
  - `contains_bytecode(self, offset: int) -> bool` — Prüft, ob ein Bytecode-Offset im Mapping liegt.
- **`class SourceMap`** — Zentrale Source-Map eines kompilierten Moduls.
  - `__init__(self) -> None` — 
  - `add(self, bytecode_start: int, bytecode_end: int, span: SourceSpan) -> SourceMapEntry` — Fügt einen Source-Map-Eintrag hinzu.
  - `add_instruction(self, instruction_offset: int, span: SourceSpan) -> SourceMapEntry` — Fügt ein Mapping für genau eine Instruction hinzu.
  - `lookup(self, bytecode_offset: int) -> SourceMapEntry | None` — Liefert den Source-Map-Eintrag für einen Bytecode-Offset.
  - `lookup_span(self, bytecode_offset: int) -> SourceSpan | None` — Liefert direkt den SourceSpan eines Bytecode-Offsets.
  - `lookup_location(self, bytecode_offset: int) -> SourceLocation | None` — Liefert die Startposition des zugehörigen Source-Bereichs.
  - `lookup_source(self, line: int, column: int=0) -> list[SourceMapEntry]` — Liefert alle Bytecode-Einträge, die zu einer Source-Position
  - `lookup_line(self, line: int) -> list[SourceMapEntry]` — Liefert alle Mappings für eine Source-Zeile.
  - `normalize(self) -> None` — Sortiert und konsolidiert die Source Map.
  - `remap_offsets(self, old_to_new: dict[int, int]) -> None` — Aktualisiert Bytecode-Offsets nach einer Transformation.
  - `entries(self) -> tuple[SourceMapEntry, ...]` — Read-only Sicht auf die Source-Map-Einträge.
  - `clear(self) -> None` — Entfernt alle Source-Map-Einträge.
  - `diagnostic(self, code: str, message: str, *, bytecode_offset: int | None=None, severity: ErrorSeverity=ErrorSeverity.ERROR, hint: str | None=None, note: str | None=None) -> CompilerDiagnostic` — Erstellt eine CompilerDiagnostic mit Source-Mapping.
  - `to_dict(self) -> list[dict]` — Serialisiert die Source Map in eine JSON-kompatible Struktur.
  - `from_dict(cls, data: Iterable[dict]) -> SourceMap` — Erstellt eine SourceMap aus einer JSON-kompatiblen Struktur.
- **`class SourceMapBuilder`** — Convenience-Builder für den Compiler.
  - `__init__(self) -> None` — 
  - `mark(self, bytecode_offset: int, span: SourceSpan) -> None` — Markiert eine einzelne Instruction.
  - `mark_range(self, bytecode_start: int, bytecode_end: int, span: SourceSpan) -> None` — Markiert einen Bytecode-Bereich.
  - `mark_node(self, bytecode_offset: int, node: object) -> None` — Markiert eine Instruction anhand eines AST-Nodes.
  - `build(self) -> SourceMap` — Erstellt die finale SourceMap.

### `src/atclang/compiler/statements.py` (563 Zeilen)

> ATCLang Compiler — Statement Compilation
> ========================================
> 
> Compiles ATCLang AST statements into ATC bytecode.

- **`class StatementCompiler`** — Statement-level ATCLang compiler.
  - `__init__(self, context: CompilerContext)` — 
  - `compile(self, node: ASTNode, scope: SymbolTable | None=None) -> None` — Compile one AST statement.
  - `compile_let(self, node: LetStatement, scope: SymbolTable) -> None` — Compile:
  - `compile_assignment(self, node: Assignment, scope: SymbolTable) -> None` — Compile assignment expressions used as statements.
  - `compile_expression_statement(self, node: ExprStatement, scope: SymbolTable) -> None` — 
  - `compile_return(self, node: ReturnStatement, scope: SymbolTable) -> None` — 
  - `compile_emit(self, node: EmitStatement, scope: SymbolTable) -> None` — 
  - `compile_require(self, node: RequireStatement, scope: SymbolTable) -> None` — 
  - `compile_if(self, node: IfStatement, scope: SymbolTable) -> None` — Compile conditional control flow through the control-flow manager.
  - `compile_while(self, node: WhileStatement, scope: SymbolTable) -> None` — Compile:
  - `compile_for(self, node: ForStatement, scope: SymbolTable) -> None` — Compile:
  - `compile_break(self, node: BreakStatement) -> None` — 
  - `compile_continue(self, node: ContinueStatement) -> None` — 
  - `compile_state_field(self, node: StateField, scope: SymbolTable) -> None` — State fields are represented as persistent contract metadata.
  - `compile_wallet(self, node: WalletDef, scope: SymbolTable) -> None` — Compile wallet declaration.
  - `compile_import(self, node: ImportStatement, scope: SymbolTable) -> None` — Compile module import.
  - `compile_enum(self, node: EnumDef, scope: SymbolTable) -> None` — Compile enum metadata.
- **`def compile_statement(context: CompilerContext, node: ASTNode, scope: SymbolTable | None=None) -> None`** — Functional convenience API.

### `src/atclang/compiler/symbols.py` (751 Zeilen)

> ATCLang Compiler — Symbol System
> ================================
> 
> ATC-92 | ATCLang Compiler v0.3.0

- **`class SymbolKind`** — Semantische Kategorie eines Symbols.
- **`class Symbol`** — Einzelnes Compiler-Symbol.
  - `is_local(self) -> bool` — 
  - `is_global(self) -> bool` — 
  - `is_function(self) -> bool` — 
  - `is_state(self) -> bool` — 
  - `is_constant(self) -> bool` — 
- **`class SymbolError`** — Basisfehler der Symbolverwaltung.
- **`class DuplicateSymbolError`** — Ein Symbol wurde innerhalb desselben Scopes doppelt definiert.
- **`class SymbolNotFoundError`** — Ein Symbol konnte nicht aufgelöst werden.
- **`class InvalidSymbolNameError`** — Ungültiger Symbolname.
- **`class Scope`** — Lexikalischer Compiler-Scope.
  - `__init__(self, parent: Scope | None=None, *, name: str='', kind: str='block') -> None` — 
  - `define(self, name: str, kind: SymbolKind | str, typ: str='', *, mutable: bool=True, exported: bool=False, metadata: dict[str, object] | None=None, allow_replace: bool=False) -> Symbol` — Definiert ein Symbol im aktuellen Scope.
  - `define_local(self, name: str, typ: str='', *, mutable: bool=True) -> Symbol` — 
  - `define_parameter(self, name: str, typ: str='') -> Symbol` — 
  - `define_global(self, name: str, typ: str='', *, mutable: bool=True, exported: bool=False) -> Symbol` — 
  - `define_constant(self, name: str, typ: str='', *, exported: bool=False) -> Symbol` — 
  - `define_function(self, name: str, typ: str='', *, exported: bool=False) -> Symbol` — 
  - `define_state(self, name: str, typ: str='', *, mutable: bool=True) -> Symbol` — 
  - `resolve_local(self, name: str) -> Symbol | None` — Sucht ausschließlich im aktuellen Scope.
  - `resolve(self, name: str) -> Symbol | None` — Lexikalische Symbolauflösung.
  - `require(self, name: str) -> Symbol` — Resolve mit Exception bei fehlendem Symbol.
  - `child(self, *, name: str='', kind: str='block') -> Scope` — 
  - `function_scope(self, name: str) -> Scope` — 
  - `contract_scope(self, name: str) -> Scope` — 
  - `display_name(self) -> str` — 
  - `depth(self) -> int` — 
  - `contains(self, name: str) -> bool` — 
  - `shadows(self, name: str) -> bool` — Prüft, ob eine lokale Definition ein Parent-Symbol überschattet.
  - `iter_local(self) -> Iterator[Symbol]` — 
  - `all_visible(self) -> dict[str, Symbol]` — Liefert alle aktuell sichtbaren Symbole.
- **`class SymbolTable`** — Kompatibilitäts- und High-Level-Wrapper um Scope.
  - `__init__(self, parent: SymbolTable | None=None, *, scope: Scope | None=None, name: str='', kind: str='block') -> None` — 
  - `symbols(self) -> dict[str, Symbol]` — 
  - `parent(self) -> SymbolTable | None` — 
  - `next_index(self) -> int` — 
  - `define(self, name: str, kind: SymbolKind | str, typ: str='', **kwargs) -> Symbol` — 
  - `resolve(self, name: str) -> Symbol | None` — 
  - `resolve_local(self, name: str) -> Symbol | None` — 
  - `require(self, name: str) -> Symbol` — 
  - `child(self) -> SymbolTable` — 
  - `function_scope(self, name: str) -> SymbolTable` — 
  - `contract_scope(self, name: str) -> SymbolTable` — 
  - `contains(self, name: str) -> bool` — 
- **`def create_global_scope() -> Scope`** — Erstellt den Root-Scope des Compilers.
- **`def register_builtin(scope: Scope, name: str, typ: str='builtin') -> Symbol`** — Registriert ein einzelnes Builtin.

### `src/atclang/compiler/type_checker.py` (601 Zeilen)

> ATCLang Type Checker — Statische Typ-Prüfung zur Compile-Zeit.
> ATC-92 | Sprint 2.1

- **`class ATCType`** — Base type class.
  - `__init__(self, name: str, nullable: bool=False)` — 
- **`class ATCGenericType`** — 
  - `__init__(self, name: str, elem_type: ATCType=T_ANY)` — 
- **`class TypeError`** — 
- **`class TypeEnvironment`** — Scope for type tracking.
  - `__init__(self, parent: Optional['TypeEnvironment']=None)` — 
  - `define_var(self, name: str, t: ATCType)` — 
  - `lookup_var(self, name: str) -> ATCType | None` — 
  - `define_function(self, name: str, params: list[ATCType], ret: ATCType)` — 
  - `lookup_function(self, name: str) -> tuple[list[ATCType], ATCType] | None` — 
  - `child(self) -> 'TypeEnvironment'` — 
- **`class ATCTypeChecker`** — Statische Typ-Prüfung für ATCLang ASTs.
  - `__init__(self)` — 
  - `check(self, program: Program) -> list[TypeError]` — Type-check a full program. Returns list of errors.
  - `check_and_report(self, program: Program) -> bool` — Type-check and print errors. Returns True if no errors.


## Paket `contracts`
*Contract-Utilities*

### `src/atclang/contracts/__init__.py` (15 Zeilen)

> ATCLang Smart Contract Engine — Deploy/Call/Storage/Events (ATC-99, ATC-8300).


### `src/atclang/contracts/engine.py` (219 Zeilen)

> ATCLang Smart Contract Engine.
> 
> Laufzeit-Ausfuehrung kompilierter Contracts auf der ATC-VM:
> - deploy: Contract-Adresse deterministisch aus Artifact-ID + Nonce

- **`class ContractDeployError`** — Deployment fehlgeschlagen (Artefakt ungueltig / Name belegt).
- **`class ContractCallError`** — Methodenaufruf fehlgeschlagen (Unbekannter Selektor / Revert / Gas).
- **`class ContractStorage`** — Persistenter Contract-State — deterministisch, key-sortiert serialisierbar.
  - `get(self, key: str, default: Any=None) -> Any` — 
  - `set(self, key: str, value: Any) -> None` — 
  - `delete(self, key: str) -> None` — 
  - `root_hash(self) -> str` — Kanonischer State-Hash: sha3-256 der sortierten JSON-Darstellung.
  - `snapshot(self) -> dict[str, Any]` — 
  - `restore(self, data: dict[str, Any]) -> None` — 
- **`class ContractInstance`** — Ein konkreter deployed Contract.
  - `abi(self) -> list[str]` — 
- **`class ContractEngine`** — Deploy- und Call-Engine ueber CompiledModule-Artefakte.
  - `__init__(self, chain_id: int=658467, codec: ABICodec | None=None)` — 
  - `deploy(self, name: str, functions: dict[str, list[str]], standards: list[str] | None=None, block_number: int=0, artifact_id: str | None=None) -> ContractInstance` — Contract registrieren; Adresse = sha3-256(artifact|name|nonce)[12:32].
  - `call(self, contract: str, selector: str, args: dict[str, Any] | None=None, caller: str='0x' + '00' * 20, value: int=0, block_number: int=0) -> dict[str, Any]` — Methodenaufruf mit ABI-Dispatch: setzt Caller/Kontext ins Storage-Fundament.
  - `transfer(self, contract: str, state_key: str, frm: str, to: str, amount: int) -> bool` — Kanonischer ATC-8300-Transfer auf Map-State (Modellebene).
  - `balance_of(self, contract: str, state_key: str, holder: str) -> int` — 
  - `by_address(self, address: str) -> ContractInstance` — 


## Paket `frontend`
*Lexer/Parser-Frontend (Tokenisierung, AST)*

### `src/atclang/frontend/__init__.py` (1 Zeilen)

> ATCLang 1.0 Frontend: Lexer, Parser, AST.


### `src/atclang/frontend/lexer/__init__.py` (2 Zeilen)

> ATCLang Lexer-Paket: Tokenisierung (Token-Typen, Scanner). Kanonisch: Rust-Frontend.


### `src/atclang/frontend/lexer/lexer.py` (751 Zeilen)

> ATCLang Lexer — Tokenizer v0.2.0
> Eigene Programmiersprache für das A-TownChain Ökosystem
> Erweitert: Alle Keywords, Typen, Operatoren für atcos_main.atc

- **`class TT`** — 
- **`class Token`** — 
- **`class LexError`** — 
  - `__init__(self, msg: str, line: int, col: int)` — 
- **`class ATCLexer`** — ATCLang Tokenizer v0.2.0
  - `__init__(self, source: str)` — 
  - `current(self) -> str | None` — 
  - `peek(self, offset: int=1) -> str | None` — 
  - `advance(self) -> str` — 
  - `match(self, expected: str) -> bool` — 
  - `add(self, tt: TT, value=None) -> Token` — 
  - `error(self, msg: str)` — 
  - `tokenize(self) -> list[Token]` — 
- **`def tokenize(source: str) -> list[Token]`** — 

### `src/atclang/frontend/parser/__init__.py` (2 Zeilen)

> ATCLang Parser-Paket: AST-Erzeugung aus dem Token-Strom. Kanonisch: Rust-Frontend.


### `src/atclang/frontend/parser/ast_nodes.py` (450 Zeilen)

> ATCLang AST-Nodes — Abstract Syntax Tree
> Alle Knoten-Typen der ATCLang Grammatik
> Version: 0.1.0-alpha

- **`class ASTNode`** — 
- **`class IntLiteral`** — 
- **`class FloatLiteral`** — 
- **`class StringLiteral`** — 
- **`class BoolLiteral`** — 
- **`class ListLiteral`** — 
- **`class MapLiteral`** — 
- **`class NullLiteral`** — 
- **`class Identifier`** — 
- **`class BinaryOp`** — 
- **`class UnaryOp`** — 
- **`class Assignment`** — 
- **`class IndexAccess`** — 
- **`class DotAccess`** — 
- **`class NamespaceAccess`** — 
- **`class FunctionCall`** — 
- **`class TypeAnnotation`** — 
- **`class StructLiteral`** — 
- **`class LetStatement`** — 
- **`class ReturnStatement`** — 
- **`class EmitStatement`** — 
- **`class RequireStatement`** — 
- **`class IfStatement`** — 
- **`class ForStatement`** — 
- **`class WhileStatement`** — 
- **`class BreakStatement`** — 
- **`class ContinueStatement`** — 
- **`class ExprStatement`** — 
- **`class Parameter`** — 
- **`class FunctionDef`** — 
- **`class StateField`** — 
- **`class EventDef`** — 
- **`class ErrorDef`** — 
- **`class ContractDef`** — 
- **`class WalletDef`** — 
- **`class ImportStatement`** — 
- **`class StructDef`** — 
- **`class EnumDef`** — 
- **`class Program`** — 
- **`class MatchStatement`** — 
  - `__init__(self, subject, arms, line=0, col=0)` — 
  - `children(self)` — 
- **`class SliceExpr`** — 
  - `__init__(self, start, end, line=0, col=0)` — 
  - `children(self)` — 
- **`class RangeExpr`** — 
  - `__init__(self, start, end, step=None, line=0, col=0)` — 
  - `children(self)` — 
- **`class LambdaExpr`** — 
  - `__init__(self, params, body, line=0, col=0)` — 
  - `children(self)` — 
- **`class CastExpr`** — 
  - `__init__(self, expr, target_type, line=0, col=0)` — 
  - `children(self)` — 
- **`class TernaryExpr`** — 
  - `__init__(self, cond, then_expr, else_expr, line=0, col=0)` — 
  - `children(self)` — 
- **`class TupleExpr`** — 
  - `__init__(self, elements, line=0, col=0)` — 
  - `children(self)` — 
- **`class ClassDef`** — class X implements Y { ... } — wird wie ContractDef behandelt.
- **`class StorageBlock`** — storage { field: Type, ... } — Storage-Deklaration.
- **`class TypeAliasDef`** — type Set<T> = Any — Type-Alias.

### `src/atclang/frontend/parser/parser.py` (1019 Zeilen)

> ATCLang Parser — Recursive Descent Parser
> Wandelt Token-Liste in einen AST um
> Version: 0.1.0-alpha

- **`class ATCParser`** — Recursive Descent Parser für ATCLang.
  - `__init__(self, tokens: list[Token])` — 
  - `error(self, msg: str)` — 
  - `current(self) -> Token` — 
  - `peek(self, offset=1) -> Token` — 
  - `advance(self) -> Token` — 
  - `check(self, ttype: TT, value=None) -> bool` — 
  - `expect(self, ttype: TT, value=None) -> Token` — 
  - `match(self, ttype: TT, value=None) -> Token | None` — 
  - `parse_type(self) -> TypeAnnotation` — 
  - `parse_expr(self) -> ASTNode` — 
  - `parse_logical(self) -> ASTNode` — 
  - `parse_comparison(self) -> ASTNode` — 
  - `parse_addition(self) -> ASTNode` — 
  - `parse_multiplication(self) -> ASTNode` — 
  - `parse_unary(self) -> ASTNode` — 
  - `parse_postfix(self) -> ASTNode` — 
  - `parse_primary(self) -> ASTNode` — 
  - `parse_statement(self) -> ASTNode` — 
  - `parse_let(self) -> LetStatement` — 
  - `parse_return(self) -> ReturnStatement` — 
  - `parse_emit(self) -> EmitStatement` — 
  - `parse_require(self) -> RequireStatement` — 
  - `parse_if(self) -> IfStatement` — 
  - `parse_for(self) -> ForStatement` — 
  - `parse_while(self) -> WhileStatement` — 
  - `parse_block(self) -> list[ASTNode]` — 
  - `parse_param(self) -> Parameter` — 
  - `parse_function(self) -> FunctionDef` — 
  - `parse_contract(self) -> ContractDef` — 
  - `parse_match_expr(self)` — 
  - `parse_struct(self) -> StructDef` — 
  - `parse_enum(self) -> EnumDef` — 
  - `parse_module(self)` — Parse 'module name { ... }' — treats it as a namespace wrapper.
  - `parse_match_stmt(self)` — Parse 'match expr { pattern => body, ... }'
  - `parse_class(self) -> ClassDef` — 
  - `parse_program(self) -> Program` — 
- **`def parse(source: str) -> Program`** — Hilfsfunktion: Quellcode → AST


## Paket `host`
*Hostcalls (ATCHost)*

### `src/atclang/host/__init__.py` (5 Zeilen)

> ATCLang Host-Layer — deterministische Host-Funktionen und Chain-Kontext.


### `src/atclang/host/context.py` (84 Zeilen)

> HostContext — die einzige Quelle fuer Umgebungszustaende in der Contract-Ausfuehrung.
> 
> Determinismus-Regel (ATC-99 / ATC-STD-100 L4): Contracts duerfen NIE direkt
> auf Wanduhr, Zufall oder OS zugreifen. Alle Umgebungswerte kommen aus dem

- **`class HostPolicy`** — Ausfuehrungs-Politik: was der Host erlaubt.
- **`class HostContext`** — Deterministischer Ausfuehrungskontext eines Blocks.
  - `for_block(cls, chain_id: int, block_number: int, block_timestamp: int, block_hash: str, policy: HostPolicy | None=None) -> HostContext` — Kanonischer Konstruktor: Node baut Context aus Block-Header.
  - `now(self) -> int` — Zeitquelle fuer Contracts — Konsens-Pflicht: block_timestamp.
  - `emit(self, name: str, **fields: Any) -> None` — Event-Log (Evidence-Spur, geordnet, replizierbar).
  - `log(self, message: str) -> None` — 
  - `events(self) -> list[dict[str, Any]]` — 
  - `gas_consume(self, amount: int, used: int) -> int` — 


## Paket `ir`
*Zwischendarstellung (IR)*

### `src/atclang/ir/__init__.py` (5 Zeilen)

> ATCLang IR — normalisierte JSON-Zwischendarstellung (Tooling-Basis).


### `src/atclang/ir/json_ir.py` (64 Zeilen)

> JSON-IR: AST -> normalisierte, kanonisch serialisierbare Zwischendarstellung.
> 
> Zweck (Sprint 2.3, Tools-Differential): die IR ist die stabile, sprach-
> versionsunabhaengige Basis fuer Differential-Tests, Formatter, Linter und

- **`class IRValidationError`** — 
- **`def to_json_ir(ast: Any) -> dict[str, Any]`** — ASTNode-Objekt (dataclass-Baum) -> IR-Dict.
- **`def _convert(node: Any) -> Any`** — 
- **`def validate_ir(ir: Any) -> None`** — 
- **`def ir_hash(ir: dict[str, Any]) -> str`** — Kanonischer IR-Hash (Vergleichbarkeit, Differential-Gates).


## Paket `package`
*Paket-Handling*

### `src/atclang/package/__init__.py` (5 Zeilen)

> ATCLang Package-System — atcpkg-Manifest (Abhaengigkeiten und Entry-Points).


### `src/atclang/package/manifest.py` (55 Zeilen)

> atcpkg-Manifest — deterministisches Paketformat fuer ATCLang-Module.
> 
> Felder (SemVer, SPDX-License-Identifier, Entry, Deps als Constraint-Range):
>   name / version / license / entry / profile / dependencies / artifacts

- **`class PackageError`** — 
- **`class PackageManifest`** — 
  - `validate(self) -> None` — 
  - `add_artifact(self, artifact_id: str) -> str` — 


## Paket `profiles`
*Build-Profile*

### `src/atclang/profiles/__init__.py` (5 Zeilen)

> ATCLang Execution Profiles — consensus / off_chain / debug (ATC-STD-100 L4).


### `src/atclang/profiles/profiles.py` (36 Zeilen)

> Execution Profiles: gleiche Sprache, unterschiedliche Vertrauenskontexte.
> 
> - consensus:   Determinismus-Pflicht (SecurityGate BLOCKER), Gas-Limit, kein OS
> - off_chain:   erweiterte Host-Freigaben (Wanduhr erlaubt), lockeres Gate

- **`class ExecutionProfile`** — 
- **`def get_profile(name: str) -> ExecutionProfile`** — 


## Paket `runtime`
*Treiber-Laufzeit (driver_framework, event-Handling)*

### `src/atclang/runtime/driver_framework.py` (546 Zeilen)

> ATCLang Driver Framework — Python-Referenz-Implementierung fuer Tests (kanonisch: driver_framework.atc)
> =================================================
> Version: 1.0.0-alpha | ATC-22+ | Sprint 3.1
> 

- **`class DriverState`** — 
- **`class DeviceClass`** — 
- **`class BusType`** — 
- **`class IoctlCode`** — 
- **`class PowerState`** — 
- **`class DeviceInfo`** — 
- **`class DriverInfo`** — 
- **`class IRQRoute`** — 
- **`class OpenHandle`** — 
- **`class DriverRegistry`** — Python Runtime für den ATCLang Driver Framework Contract.
  - `__init__(self)` — 
  - `register_driver(self, name, version, device_class, supported_vendors, init_fn, cleanup_fn, gas_per_io=10)` — Treiber registrieren → driver_id
  - `init_driver(self, driver_id)` — Treiber initialisieren → bool
  - `activate_driver(self, driver_id)` — Treiber aktivieren → bool
  - `unload_driver(self, driver_id, reason='')` — Treiber entladen → bool
  - `get_driver_info(self, driver_id)` — 
  - `list_drivers_by_class(self, device_class)` — 
  - `enumerate_device(self, device_class, bus, vendor_id, product_id, bus_address=0, irq_line=255, mmio_base=0, mmio_size=0, port_base=0, name='', description='')` — Gerät enumerieren → device_id
  - `bind_driver(self, device_id, driver_id)` — Treiber an Gerät binden → bool
  - `unbind_driver(self, device_id)` — Treiber von Gerät trennen → bool
  - `get_device_info(self, device_id)` — 
  - `list_devices_by_class(self, device_class)` — 
  - `list_devices_by_bus(self, bus_type)` — 
  - `open(self, device_id, flags=3, owner_pid=0)` — Gerät öffnen → handle_id
  - `read(self, handle_id, buffer_size=4096)` — Von Gerät lesen → str
  - `write(self, handle_id, data)` — Auf Gerät schreiben → bytes written
  - `ioctl(self, handle_id, code, arg=0)` — I/O-Control → u64
  - `close(self, handle_id)` — Gerät schließen → bool
  - `seek(self, handle_id, offset, whence=0)` — 
  - `register_irq(self, irq_line, device_id, driver_id, handler_fn, priority=128)` — 
  - `trigger_irq(self, irq_line)` — 
  - `unregister_irq(self, irq_line)` — 
  - `setup_dma(self, device_id, size)` — 
  - `set_power_state(self, device_id, state)` — 
  - `get_stats(self)` — 
  - `report_error(self, driver_id, error)` — 

### `src/atclang/runtime/kernel_runtime.py` (664 Zeilen)

> ATCLang Kernel Runtime — Dezentrales KI-Betriebssystem Runtime
> ===============================================================
> Version: 1.0.0-alpha | ATC-97 | Sprint 3.2
> 

- **`class ContractState`** — Laufzeit-Zustand eines ATCLang Contracts.
- **`class ATCModule`** — Ein geladenes ATCLang-Modul.
  - `summary(self) -> str` — 
- **`class KernelRuntimeError`** — Runtime-Fehler im ATCLang Kernel.
- **`class ContractCallError`** — Fehler bei Contract-Aufruf.
- **`class ModuleLoadError`** — Fehler beim Laden eines .atc Moduls.
- **`class KernelRuntime`** — ATCLang Kernel Runtime — Lädt, kompiliert und führt .atc Module aus.
  - `__init__(self, gas_limit: int=50000000)` — 
  - `load_file(self, path: str, module_name: str=None) -> ATCModule` — Lädt eine .atc Datei, kompiliert sie und registriert Contracts.
  - `load_source(self, source: str, module_name: str, path: str='<inline>') -> ATCModule` — Lädt ATCLang-Quellcode, kompiliert und registriert ihn.
  - `load_directory(self, dir_path: str, pattern: str='*.atc') -> list[ATCModule]` — Lädt alle .atc Dateien aus einem Verzeichnis.
  - `call(self, fn_path: str, *args) -> Any` — Ruft eine Contract-Funktion auf.
  - `call_contract(self, contract_name: str, fn_name: str, *args) -> Any` — Convenience: Contract-Funktion aufrufen.
  - `get_contract_state(self, contract_name: str) -> ContractState | None` — 
  - `get_state(self, contract_name: str, field_name: str) -> Any` — 
  - `set_state(self, contract_name: str, field_name: str, value: Any)` — 
  - `get_events(self, contract_name: str=None) -> list[dict]` — 
  - `export_state(self) -> dict` — 
  - `import_state(self, state: dict)` — 
  - `stats(self) -> dict` — 
  - `list_modules(self) -> list[dict]` — 
  - `list_contracts(self) -> list[dict]` — 
  - `disassemble(self, module_name: str=None) -> str` — 
  - `reset(self)` — 
- **`def create_runtime(gas_limit: int=50000000) -> KernelRuntime`** — Erstellt eine neue Kernel Runtime.
- **`def compile_atc(path: str) -> CompiledModule`** — Kompiliert eine .atc Datei ohne sie auszuführen.


## Paket `security`
*Security-Gate (statische Analyse, fail-closed Verboets-Importe)*

### `src/atclang/security/__init__.py` (5 Zeilen)

> ATCLang Security — statische Analyse und Konsens-Determinismus-Gate (Gate G2+).


### `src/atclang/security/static_analysis.py` (115 Zeilen)

> Determinism and capability static analysis for ATCLang source.
> 
> This gate is intentionally conservative for the consensus profile: host clock,
> OS/process access, filesystem, unrestricted network and randomness are rejected

- **`class Severity`** — 
- **`class Finding`** — 
- **`class SecurityGate`** — Static source gate with fail-closed consensus semantics.
  - `analyse(self, source: str, profile: str='consensus') -> list[Finding]` — 
  - `check(self, source: str, profile: str='consensus') -> bool` — 


## Paket `semantics`
*Semantik-Analyse (Gate-Checks vor Codegen)*

### `src/atclang/semantics/__init__.py` (15 Zeilen)

> ATCLang Semantics (Subsystem) — unabhaengige semantische Analyse (Gate G2).
> 
> Normativ: specs/semantics/SPEC.md. Vertrauensgrenze: Der TypeChecker
> validiert nur — er erzeugt keinen Code und mutiert nichts (AD-022).


### `src/atclang/semantics/type_checker.py` (609 Zeilen)

> ATCLang Semantics — TypeChecker (Subsystem, Gate G2)
> 
> Normativ: specs/semantics/SPEC.md | Quelle: specs/language/SPEC.md §5-6.
> 

- **`class SemanticDiagnostic`** — Eine semantische Verletzung (Regel-ID gemaess specs/semantics/SPEC.md).
- **`class TypeChecker`** — G2 — unabhaengige semantische Analyse (AST rein, Diagnosen raus).
  - `__init__(self) -> None` — 
  - `check_and_report(self, program)` — 
  - `analyze_source(self, source: str) -> list[SemanticDiagnostic]` — Komfort-Entry: Quelle direkt analysieren (parse + check_and_report).
  - `check(self, program)` — 
- **`def analyze_source(source)`** — Komfort-Entry: Quelle direkt analysieren (parse + check_and_report).


## Paket `(root)`
### `src/atclang/setup.py` (21 Zeilen)



## Paket `stdlib`
*Standardbibliothek (collections, chain, crypto, io, math, net, strings, types, wallet)*

### `src/atclang/stdlib/__init__.py` (50 Zeilen)

> ATCLang Standard Library — ATC-94
> 
> 6 Module:
>   crypto      — SHA-256, ECDSA, Base58/64, Hex


### `src/atclang/stdlib/chain.py` (50 Zeilen)

> ATC::Chain reference bindings.
> 
> Consensus-safe rule: chain environment values are supplied by the host
> context. This module never reads the local wall clock and never prints

- **`class ATCChain`** — Deterministic chain-state view supplied by the execution host.
  - `__init__(self, state: dict[str, Any] | None=None)` — 
  - `block_number(self) -> int` — 
  - `block_hash(self) -> str` — 
  - `block_timestamp(self) -> int` — Return the host-supplied block timestamp; never the local clock.
  - `chain_id(self) -> int` — 
  - `require(self, condition: bool, message: str='Condition failed') -> None` — 
  - `emit(self, event_name: str, **kwargs: Any) -> None` — Record an event for deterministic host-side collection.
  - `events(self) -> list[dict[str, Any]]` — 
  - `revert(self, message: str='Transaction reverted') -> None` — 

### `src/atclang/stdlib/collections.py` (219 Zeilen)

> ATCLang Stdlib — ATC::Collections
> Datenstrukturen für ATCLang Smart Contracts.
> ATC-94 | Sprint 2.5

- **`class ATCCollections`** — ATC::Collections — Map, Array, Set, Queue, Stack.
  - `map_new() -> dict` — Create empty Map. Gas: 10
  - `map_get(m: dict, key: Any) -> Any` — Get value by key. Gas: 5
  - `map_set(m: dict, key: Any, value: Any) -> dict` — Set key-value. Gas: 5
  - `map_delete(m: dict, key: Any) -> dict` — Delete key. Gas: 5
  - `map_contains(m: dict, key: Any) -> bool` — Check key exists. Gas: 5
  - `map_keys(m: dict) -> list` — Get all keys. Gas: 5
  - `map_values(m: dict) -> list` — Get all values. Gas: 5
  - `map_size(m: dict) -> int` — Map size. Gas: 2
  - `array_new() -> list` — Create empty Array. Gas: 10
  - `array_push(arr: list, value: Any) -> list` — Append value. Gas: 5
  - `array_pop(arr: list) -> Any` — Remove and return last. Gas: 5
  - `array_get(arr: list, idx: int) -> Any` — Get by index. Gas: 3
  - `array_set(arr: list, idx: int, value: Any) -> list` — Set by index. Gas: 3
  - `array_len(arr: list) -> int` — Array length. Gas: 2
  - `array_contains(arr: list, value: Any) -> bool` — Check value exists. Gas: 5
  - `array_slice(arr: list, start: int, end: int) -> list` — Slice array. Gas: 5
  - `array_reverse(arr: list) -> list` — Reverse array. Gas: 10
  - `array_sort(arr: list, reverse: bool=False) -> list` — Sort array. Gas: 20
  - `set_new() -> set` — Create empty Set. Gas: 10
  - `set_add(s: set, value: Any) -> set` — Add value. Gas: 5
  - `set_contains(s: set, value: Any) -> bool` — Check value exists. Gas: 5
  - `set_remove(s: set, value: Any) -> set` — Remove value. Gas: 5
  - `set_size(s: set) -> int` — Set size. Gas: 2
  - `set_union(a: set, b: set) -> set` — Union. Gas: 10
  - `set_intersection(a: set, b: set) -> set` — Intersection. Gas: 10
  - `set_difference(a: set, b: set) -> set` — Difference. Gas: 10
  - `queue_new() -> list` — Create empty Queue. Gas: 10
  - `queue_enqueue(q: list, value: Any) -> list` — Add to back. Gas: 5
  - `queue_dequeue(q: list) -> Any` — Remove from front. Gas: 5
  - `queue_peek(q: list) -> Any` — Peek front. Gas: 3
  - `queue_size(q: list) -> int` — Queue size. Gas: 2
  - `stack_new() -> list` — Create empty Stack. Gas: 10
  - `stack_push(s: list, value: Any) -> list` — Push onto stack. Gas: 5
  - `stack_pop(s: list) -> Any` — Pop from stack. Gas: 5
  - `stack_peek(s: list) -> Any` — Peek top. Gas: 3
  - `stack_size(s: list) -> int` — Stack size. Gas: 2

### `src/atclang/stdlib/crypto.py` (164 Zeilen)

> ATCLang Stdlib — ATC::Crypto
> Kryptografische Operationen für ATCLang Smart Contracts.
> ATC-94 | Sprint 2.5 | Non-EVM: SHA-256 only

- **`class ATCCrypto`** — ATC::Crypto — SHA-256 based cryptography (Non-EVM Standard).
  - `sha256(data) -> str` — SHA-256 Hash → hex string. Gas: 30
  - `sha256_bytes(data) -> bytes` — SHA-256 Hash → raw bytes. Gas: 30
  - `double_sha256(data) -> str` — Double SHA-256 (Bitcoin-style). Gas: 60
  - `hmac_sha256(key, msg) -> str` — HMAC-SHA256. Gas: 50
  - `base58_encode(data) -> str` — Base58 Encode (Bitcoin alphabet). Gas: 20
  - `base58_decode(s: str) -> bytes` — Base58 Decode. Gas: 20
  - `base64_encode(data) -> str` — Base64 Encode. Gas: 15
  - `base64_decode(s: str) -> bytes` — Base64 Decode. Gas: 15
  - `hex_encode(data) -> str` — Hex Encode. Gas: 10
  - `hex_decode(s: str) -> bytes` — Hex Decode. Gas: 10
  - `generate_keypair() -> tuple[str, str]` — Generate ECDSA keypair. Gas: 1000
  - `sign(message: str, private_key: str) -> str` — Sign message with private key. Gas: 100
  - `verify(message: str, signature: str, public_key: str) -> bool` — Verify signature. Gas: 100
  - `random_bytes(n: int) -> bytes` — Cryptographic random bytes. Gas: 50
  - `random_int(min_val: int, max_val: int) -> int` — Cryptographic random integer. Gas: 50
  - `address_from_pubkey(pubkey: str) -> str` — Derive ATC address from public key. Gas: 30
  - `is_valid_address(addr: str) -> bool` — Validate ATC address format. Gas: 5

### `src/atclang/stdlib/encoding.py` (211 Zeilen)

> ATCLang Stdlib — ATC::Encoding
> Serialisierung und Encoding für ATCLang.
> ATC-94 | Sprint 2.5 | Non-EVM: JSON + CBOR, RLP deprecated

- **`class ATCEncoding`** — ATC::Encoding — JSON, CBOR, Hex, Base58, Base64.
  - `json_encode(obj: Any) -> str` — Encode object to JSON string. Gas: 15
  - `json_decode(s: str) -> Any` — Decode JSON string to object. Gas: 15
  - `cbor_encode(obj: Any) -> bytes` — Encode to CBOR bytes. Gas: 20
  - `cbor_decode(data: bytes) -> Any` — Decode CBOR bytes. Gas: 20
  - `hex_encode(data: bytes) -> str` — Bytes to hex string. Gas: 10
  - `hex_decode(s: str) -> bytes` — Hex string to bytes. Gas: 10
  - `rlp_encode(obj: Any) -> bytes` — RLP Encode (DEPRECATED — use CBOR). Gas: 20
  - `rlp_decode(data: bytes) -> Any` — RLP Decode (DEPRECATED — use CBOR). Gas: 20
  - `scale_encode(obj: Any) -> bytes` — SCALE Encode (DEPRECATED — use CBOR). Gas: 20
  - `scale_decode(data: bytes) -> Any` — SCALE Decode (DEPRECATED — use CBOR). Gas: 20

### `src/atclang/stdlib/io.py` (107 Zeilen)

> ATCLang Stdlib — ATC::IO
> Input/Output für ATCLang. Context-isoliert.
> ATC-94 | Sprint 2.5

- **`class ATCIO`** — ATC::IO — Console, File, Network (context-isoliert).
  - `print(*args) -> None` — Print to console. Gas: 5
  - `println(*args) -> None` — Print with newline. Gas: 5
  - `format(template: str, *args) -> str` — Format string with args. Gas: 10
  - `file_write(path: str, data: str) -> bool` — Write file. Gas: 50. Node context only.
  - `file_read(path: str) -> str | None` — Read file. Gas: 50. Node context only.
  - `file_exists(path: str) -> bool` — Check file exists. Gas: 10
  - `file_append(path: str, data: str) -> bool` — Append to file. Gas: 50
  - `file_delete(path: str) -> bool` — Delete file. Gas: 50
  - `dir_create(path: str) -> bool` — Create directory. Gas: 50
  - `dir_list(path: str) -> list` — List directory. Gas: 20
  - `net_send(host: str, port: int, data: str) -> bool` — Send network packet. Gas: 50. Node context only.
  - `net_recv(port: int) -> str | None` — Receive network packet. Gas: 50. Node context only.

### `src/atclang/stdlib/math.py` (140 Zeilen)

> ATCLang Stdlib — ATC::Math
> Safe integer arithmetic for smart contracts.
> Issue: #48 | Wiki: Kap. 36

- **`class ATCMath`** — ATC::Math — Safe arithmetic for ATCLang contracts.
  - `add(a: int, b: int) -> int` — 
  - `sub(a: int, b: int) -> int` — 
  - `mul(a: int, b: int) -> int` — 
  - `div(a: int, b: int) -> int` — 
  - `mod(a: int, b: int) -> int` — 
  - `pow(base: int, exp: int) -> int` — 
  - `sqrt(x: int) -> int` — 
  - `min(a: int, b: int) -> int` — 
  - `max(a: int, b: int) -> int` — 
  - `clamp(value: int, lo: int, hi: int) -> int` — 
  - `percentage(amount: int, bps: int) -> int` — Calculate percentage using basis points (100 bps = 1%).
  - `is_power_of_two(n: int) -> bool` — 
  - `safe_add(a: int, b: int) -> int` — Safe addition with overflow check. Gas: 3
  - `safe_sub(a: int, b: int) -> int` — Safe subtraction with underflow check. Gas: 3
  - `safe_mul(a: int, b: int) -> int` — Safe multiplication with overflow check. Gas: 5
  - `safe_div(a: int, b: int) -> int` — Safe division with zero check. Gas: 5
  - `safe_mod(a: int, b: int) -> int` — Safe modulo with zero check. Gas: 5
  - `mod_exp(base: int, exp: int, mod: int) -> int` — Modular exponentiation. Gas: 50
  - `abs(x: int) -> int` — Absolute value. Gas: 2
  - `gcd(a: int, b: int) -> int` — Greatest common divisor. Gas: 20
  - `lcm(a: int, b: int) -> int` — Least common multiple. Gas: 30

### `src/atclang/stdlib/primitives.py` (257 Zeilen)

> ATCLang Stdlib — ATC::Primitives
> Core Blockchain-Typen für ATCLang.
> ATC-94 | Sprint 2.5 | Non-EVM: SHA-256, Chain-ID 658467

- **`class ATCAddress`** — ATC Address — 35 chars (ATC + 32 hex).
  - `__init__(self, value: str)` — 
  - `from_pubkey(pubkey: str) -> 'ATCAddress'` — Derive address from public key.
  - `zero() -> 'ATCAddress'` — Zero address.
  - `as_string(self) -> str` — 
  - `as_bytes(self) -> bytes` — 
- **`class ATCHash`** — ATC Hash256 — 64 char hex string (SHA-256).
  - `__init__(self, value: str)` — 
  - `compute(data: bytes) -> 'ATCHash'` — Compute SHA-256 hash.
  - `zero() -> 'ATCHash'` — Zero hash.
  - `as_string(self) -> str` — 
  - `as_bytes(self) -> bytes` — 
- **`class ATCSignature`** — ATC Signature — 64 byte hex string (simplified).
  - `__init__(self, value: str)` — 
  - `create(message: str, private_key: str) -> 'ATCSignature'` — Create signature (simplified HMAC-SHA256).
  - `as_string(self) -> str` — 
- **`class ATCTransaction`** — ATC Transaction — core transaction structure.
  - `__init__(self, sender: str, receiver: str, amount: int, gas_price: int=1, gas_limit: int=30000000, data: str='', nonce: int=0)` — 
  - `compute_hash(self) -> str` — Compute transaction hash.
  - `sign(self, private_key: str) -> str` — Sign transaction.
  - `to_dict(self) -> dict[str, Any]` — 
- **`class ATCBlockHeader`** — ATC Block Header.
  - `__init__(self, number: int, prev_hash: str, merkle_root: str, timestamp: int=None, nonce: int=0, difficulty: int=1)` — 
  - `compute_hash(self) -> str` — Compute block header hash.
  - `to_dict(self) -> dict[str, Any]` — 
- **`class ATCPrimitives`** — ATC::Primitives — Factory functions for blockchain types.
  - `new_address(pubkey: str) -> ATCAddress` — Create address from pubkey. Gas: 30
  - `zero_address() -> ATCAddress` — Zero address. Gas: 5
  - `is_valid_address(addr: str) -> bool` — Validate address. Gas: 5
  - `compute_hash(data: bytes) -> ATCHash` — SHA-256 hash. Gas: 30
  - `zero_hash() -> ATCHash` — Zero hash. Gas: 5
  - `sign(message: str, private_key: str) -> ATCSignature` — Sign message. Gas: 100
  - `new_transaction(sender: str, receiver: str, amount: int, gas_price: int=1, nonce: int=0) -> ATCTransaction` — Create transaction. Gas: 50
  - `new_block_header(number: int, prev_hash: str, merkle_root: str) -> ATCBlockHeader` — Create block header. Gas: 50

### `src/atclang/stdlib/string.py` (100 Zeilen)

> ATCLang Standard Library — String Module v1.0
> Erweiterte String-Operationen für ATCLang.
> Standard: ATC-94

- **`class ATCString`** — Erweiterte String-Operationen.
  - `len(s: str) -> int` — 
  - `upper(s: str) -> str` — 
  - `lower(s: str) -> str` — 
  - `split(s: str, delim: str=' ') -> list` — 
  - `join(parts: list, delim: str=' ') -> str` — 
  - `format(template: str, **kwargs) -> str` — 
  - `trim(s: str) -> str` — 
  - `trim_left(s: str) -> str` — 
  - `trim_right(s: str) -> str` — 
  - `starts_with(s: str, prefix: str) -> bool` — 
  - `ends_with(s: str, suffix: str) -> bool` — 
  - `contains(s: str, substr: str) -> bool` — 
  - `replace(s: str, old: str, new: str) -> str` — 
  - `repeat(s: str, n: int) -> str` — 
  - `reverse(s: str) -> str` — 
  - `slice(s: str, start: int, end: int=None) -> str` — 
  - `to_bytes(s: str) -> bytes` — 
  - `from_bytes(b: bytes) -> str` — 
  - `pad_left(s: str, width: int, pad: str=' ') -> str` — 
  - `pad_right(s: str, width: int, pad: str=' ') -> str` — 
  - `to_hex(s: str) -> str` — 
  - `from_hex(h: str) -> str` — 

### `src/atclang/stdlib/wallet.py` (77 Zeilen)

> ATCLang Stdlib — ATC::Wallet
> Standard wallet operations accessible from ATCLang contracts.
> Issue: #48 | Wiki: Kap. 36

- **`class ATCWallet`** — ATC::Wallet — ATCLang standard library for wallet operations.
  - `transfer(balances: dict[str, int], sender: str, recipient: str, amount: int) -> bool` — Transfer ATC tokens between addresses.
  - `balance(balances: dict[str, int], address: str) -> int` — Get balance of address in atoshi (1 ATC = 10^8 atoshi).
  - `mint(balances: dict[str, int], address: str, amount: int) -> bool` — Mint new tokens (genesis only).
  - `burn(balances: dict[str, int], address: str, amount: int) -> bool` — Burn tokens (reduce supply).
  - `generate_address(public_key: bytes) -> str` — Generate ATC address from public key (RIPEMD160(SHA256(pubkey))).
  - `format_atc(atoshi: int) -> str` — Format atoshi as human-readable ATC string.
  - `parse_atc(atc_str: str) -> int` — Parse 'X.XXXXXXXX ATC' to atoshi integer.
  - `is_valid_address(address: str) -> bool` — 


## Paket `vm`
*Stack-VM (ATCStdlib-Hostcalls, ATCVM-Interpreter, OP-Opcode-Tabelle)*

### `src/atclang/vm/__init__.py` (4 Zeilen)


### `src/atclang/vm/atcvm.py` (1321 Zeilen)

> ATCLang VM — Stack-basierte virtuelle Maschine
> Version: 0.2.0 | A-TownChain Ökosystem
> Erweitert für vollständige atcos_main.atc Ausführung.

- **`class OP`** — 
- **`class Instruction`** — 
- **`class ATCFunction`** — 
- **`class CallFrame`** — 
- **`class ATCObject`** — Struct / Contract Instanz.
- **`class ATCVMError`** — 
- **`class RequireError`** — 
- **`class GasError`** — 
- **`class ATCStdlib`** — Vollständige ATC:: Standardbibliothek.
  - `hash_sha256(data) -> str` — 
  - `hash_sha3(data) -> str` — 
  - `hash_sha3_atc(data) -> str` — ATC-eigene SHA3-Variante mit Domain-Separator.
  - `leading_zeros(hash_str: str) -> int` — 
  - `random_bytes(n: int=32) -> bytes` — 
  - `random_int(max_val: int) -> int` — 
  - `rand_nonce() -> int` — 
  - `ecdsa_pub_key(priv_key) -> str` — Public-Key der Simulations-Suite: H(priv). Kryptografisch NICHT
  - `ecdsa_sign(data, priv_key) -> str` — Deterministische Signatur-Simulation: sig = H(data|H(priv)) —
  - `ecdsa_verify(data, sig: str, pub_key) -> bool` — Prueft die deterministische Bindung sig <-> (data, pub_key) im
  - `bip39_mnemonic(seed: bytes, word_count: int=24) -> list[str]` — 
  - `generate_atc_address(pub_key_data=None) -> str` — Deterministische Adress-Ableitung: ATC + H(pub_key_data)[:32].
  - `verify_jwt(token: str) -> bool` — Strukturelle JWT-Referenz-Pruefung: 3 Base64url-Segmente,
  - `net_send(addr: str, port: int, data) -> bool` — Referenz-VM ohne Transport: fail-closed — KEIN virtueller Erfolg.
  - `kademlia_find_node(node_id: str, addr: str, port: int, k: int) -> list[dict]` — 
  - `storage_store(cls, key: str, value: Any)` — 
  - `storage_load(cls, key: str) -> Any` — 
  - `mem_alloc(size: int) -> bytes` — 
  - `rpc_register(cls, handler: str, fn: Callable) -> None` — Registriert einen RPC-Handler fuer die Referenz-VM.
  - `rpc_call(handler: str, request) -> dict` — Dispatch an registrierte Handler; ohne Handler: 404 fail-closed
- **`def _build_stdlib_dispatch() -> dict[str, Callable]`** — 
- **`class ATCVM`** — Stack-basierte VM für ATCLang v0.2.0.
  - `__init__(self, gas_limit: int=10000000)` — 
  - `push(self, val: Any)` — 
  - `pop(self) -> Any` — 
  - `peek(self) -> Any` — 
  - `gas(self, cost: int=1)` — 
  - `get_var(self, name: str, frame: CallFrame | None) -> Any` — 
  - `set_var(self, name: str, value: Any, frame: CallFrame | None)` — 
  - `execute(self, instructions: list[Instruction], frame: CallFrame | None=None) -> Any` — 
  - `run_program(self, instructions: list[Instruction]) -> Any` — Haupteinstieg — Programm ausführen.
  - `register_function(self, fn: ATCFunction)` — 
  - `get_events(self)` — Return emitted events.
  - `stats(self) -> dict` — 
