# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Bytecode
===========================

Zentrale Bytecode-Datenstrukturen für ATCLang.

Verantwortlichkeiten
--------------------
- Instruction-Repräsentation
- CompiledModule
- Bytecode-Versionierung
- Bytecode-Validierung
- Source-Map-Anbindung
- Function-/Export-Metadaten
- Bytecode-Disassembly
- .atcb Serialization / Deserialization

Dieses Modul enthält KEINE AST-Compilerlogik.

Compiler Pipeline:

    Source
      ↓
    Lexer
      ↓
    Parser
      ↓
    AST
      ↓
    TypeChecker
      ↓
    Compiler
      ↓
    BytecodeModule
      ↓
    ATC VM

ATC-92
------

Das Bytecode-Format gehört zur ATCLang/ATC-92 Compiler-/VM-Schnittstelle.
Die eigentliche VM-Ausführung verbleibt vollständig in atclang.vm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
import json
import struct
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .constants import (
    ATCLANG_VERSION,
    BYTECODE_MAGIC,
    BYTECODE_VERSION_MAJOR,
    BYTECODE_VERSION_MINOR,
    MAX_CONSTANTS,
    MAX_EXPORTS,
    MAX_FUNCTIONS,
    MAX_INSTRUCTIONS,
    MAX_PARAMETERS,
    MAX_MODULE_NAME_LENGTH,
    SOURCE_MAP_ENTRY_SIZE,
    SOURCE_MAP_VERSION,
    UNKNOWN_SOURCE_COLUMN,
    UNKNOWN_SOURCE_LINE,
)


# ══════════════════════════════════════════════════════════════════════════════
# BYTECODE VERSION
# ══════════════════════════════════════════════════════════════════════════════


BYTECODE_VERSION: Tuple[int, int] = (
    BYTECODE_VERSION_MAJOR,
    BYTECODE_VERSION_MINOR,
)


# ══════════════════════════════════════════════════════════════════════════════
# ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class BytecodeError(Exception):
    """Base exception for bytecode errors."""


class BytecodeValidationError(BytecodeError):
    """Raised when bytecode violates compiler/VM invariants."""


class BytecodeFormatError(BytecodeError):
    """Raised when serialized bytecode has an invalid format."""


# ══════════════════════════════════════════════════════════════════════════════
# INSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(slots=True)
class Instruction:
    """
    Single ATC VM instruction.

    `op`
        VM opcode. The compiler deliberately does not own the OP enum.

    `args`
        Positional instruction operands.

    `line`, `column`
        Optional source position. The canonical source mapping remains in
        SourceMap; these fields are convenience metadata for compiler users.
    """

    op: Any
    args: List[Any] = field(default_factory=list)
    line: int = UNKNOWN_SOURCE_LINE
    column: int = UNKNOWN_SOURCE_COLUMN

    def __post_init__(self) -> None:
        if not isinstance(self.args, list):
            self.args = list(self.args)

    def copy(self) -> "Instruction":
        return Instruction(
            op=self.op,
            args=list(self.args),
            line=self.line,
            column=self.column,
        )

    @property
    def opcode_name(self) -> str:
        """Return a stable human-readable opcode name."""
        return getattr(self.op, "name", str(self.op))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op": self.opcode_name,
            "args": _json_safe(self.args),
            "line": self.line,
            "column": self.column,
        }

    def __str__(self) -> str:
        if self.args:
            args = " ".join(repr(arg) for arg in self.args)
            return f"{self.opcode_name:<12} {args}"
        return self.opcode_name


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION METADATA
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(slots=True)
class FunctionBytecode:
    """
    Compiled function metadata.

    The instruction list is independent from the main module instruction
    stream. This preserves the existing ATCLang function model while giving
    the VM explicit metadata.
    """

    name: str
    instructions: List[Instruction] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    exports: bool = False

    def validate(self) -> None:
        if not self.name:
            raise BytecodeValidationError(
                "Function name must not be empty."
            )

        if len(self.parameters) > MAX_PARAMETERS:
            raise BytecodeValidationError(
                f"Function '{self.name}' has too many parameters: "
                f"{len(self.parameters)} > {MAX_PARAMETERS}"
            )

        if len(self.instructions) > MAX_INSTRUCTIONS:
            raise BytecodeValidationError(
                f"Function '{self.name}' contains too many instructions."
            )

        seen = set()
        for parameter in self.parameters:
            if parameter in seen:
                raise BytecodeValidationError(
                    f"Duplicate parameter '{parameter}' in function "
                    f"'{self.name}'."
                )
            seen.add(parameter)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "parameters": list(self.parameters),
            "exports": self.exports,
            "instructions": [
                instruction.to_dict()
                for instruction in self.instructions
            ],
        }


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE MAP
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(slots=True, frozen=True)
class SourceMapEntry:
    """
    Maps one instruction to a source location.

    Format:

        instruction_index, source_line, source_column
    """

    instruction: int
    line: int = UNKNOWN_SOURCE_LINE
    column: int = UNKNOWN_SOURCE_COLUMN

    def to_tuple(self) -> Tuple[int, int, int]:
        return (
            self.instruction,
            self.line,
            self.column,
        )

    def to_dict(self) -> Dict[str, int]:
        return {
            "instruction": self.instruction,
            "line": self.line,
            "column": self.column,
        }


@dataclass(slots=True)
class SourceMap:
    """Canonical source-map container."""

    version: int = SOURCE_MAP_VERSION
    entries: List[SourceMapEntry] = field(default_factory=list)

    def add(
        self,
        instruction: int,
        line: int,
        column: int = UNKNOWN_SOURCE_COLUMN,
    ) -> None:
        self.entries.append(
            SourceMapEntry(
                instruction=instruction,
                line=line,
                column=column,
            )
        )

    def lookup(self, instruction: int) -> Optional[SourceMapEntry]:
        """
        Return the closest source mapping at or before an instruction.
        """
        result: Optional[SourceMapEntry] = None

        for entry in self.entries:
            if entry.instruction > instruction:
                break

            result = entry

        return result

    def to_list(self) -> List[Tuple[int, int, int]]:
        return [entry.to_tuple() for entry in self.entries]

    @classmethod
    def from_list(
        cls,
        entries: Iterable[Sequence[int]],
        version: int = SOURCE_MAP_VERSION,
    ) -> "SourceMap":
        source_map = cls(version=version)

        for entry in entries:
            if len(entry) != SOURCE_MAP_ENTRY_SIZE:
                raise BytecodeFormatError(
                    "Invalid source-map entry size."
                )

            source_map.entries.append(
                SourceMapEntry(
                    instruction=int(entry[0]),
                    line=int(entry[1]),
                    column=int(entry[2]),
                )
            )

        return source_map


# ══════════════════════════════════════════════════════════════════════════════
# COMPILED MODULE
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class CompiledModule:
    """
    Complete compiler output.

    Compatibility fields are intentionally retained:

        instructions
        constants
        functions
        exports
        function_params
        source_map

    This allows migration from the previous monolithic compiler without
    forcing the VM/runtime to change at the same time.
    """

    name: str

    instructions: List[Instruction] = field(default_factory=list)
    constants: List[Any] = field(default_factory=list)

    functions: Dict[str, List[Instruction]] = field(
        default_factory=dict
    )

    exports: List[str] = field(default_factory=list)

    function_params: Dict[str, List[str]] = field(
        default_factory=dict
    )

    source_map: List[Tuple[int, int, int]] = field(
        default_factory=list
    )

    # Format metadata
    bytecode_version: Tuple[int, int] = BYTECODE_VERSION
    compiler_version: str = ATCLANG_VERSION
    source_map_version: int = SOURCE_MAP_VERSION

    # Optional semantic metadata
    language_version: str = "0.3"
    entry_point: str = "main"

    def __post_init__(self) -> None:
        self.validate()

    # ──────────────────────────────────────────────────────────────────────
    # Compatibility helpers
    # ──────────────────────────────────────────────────────────────────────

    def summary(self) -> str:
        return (
            f"Module '{self.name}' | "
            f"{len(self.instructions)} Instrs | "
            f"{len(self.functions)} Fns | "
            f"{len(self.constants)} Konstanten"
        )

    @property
    def instruction_count(self) -> int:
        return len(self.instructions)

    @property
    def function_count(self) -> int:
        return len(self.functions)

    @property
    def constant_count(self) -> int:
        return len(self.constants)

    @property
    def export_count(self) -> int:
        return len(self.exports)

    def get_function(
        self,
        name: str,
    ) -> Optional[List[Instruction]]:
        return self.functions.get(name)

    def get_function_parameters(
        self,
        name: str,
    ) -> List[str]:
        return list(self.function_params.get(name, []))

    # ──────────────────────────────────────────────────────────────────────
    # Source map
    # ──────────────────────────────────────────────────────────────────────

    def source_location(
        self,
        instruction: int,
    ) -> Optional[SourceMapEntry]:
        source_map = SourceMap.from_list(
            self.source_map,
            version=self.source_map_version,
        )
        return source_map.lookup(instruction)

    # ──────────────────────────────────────────────────────────────────────
    # Validation
    # ──────────────────────────────────────────────────────────────────────

    def validate(self) -> None:
        """
        Validate module-level compiler invariants.

        This does not validate semantic correctness of instructions against
        the VM's complete opcode specification. That belongs to the VM ABI
        validator.
        """

        if not self.name:
            raise BytecodeValidationError(
                "Module name must not be empty."
            )

        if len(self.name) > MAX_MODULE_NAME_LENGTH:
            raise BytecodeValidationError(
                "Module name exceeds compiler limit."
            )

        if self.bytecode_version != BYTECODE_VERSION:
            raise BytecodeValidationError(
                "Unsupported bytecode version: "
                f"{self.bytecode_version!r}; "
                f"expected {BYTECODE_VERSION!r}."
            )

        if len(self.instructions) > MAX_INSTRUCTIONS:
            raise BytecodeValidationError(
                "Module contains too many instructions."
            )

        if len(self.constants) > MAX_CONSTANTS:
            raise BytecodeValidationError(
                "Module contains too many constants."
            )

        if len(self.functions) > MAX_FUNCTIONS:
            raise BytecodeValidationError(
                "Module contains too many functions."
            )

        if len(self.exports) > MAX_EXPORTS:
            raise BytecodeValidationError(
                "Module contains too many exports."
            )

        # Every export must reference a function.
        function_names = set(self.functions)

        for export in self.exports:
            if export not in function_names:
                raise BytecodeValidationError(
                    f"Export '{export}' does not reference a function."
                )

        # Function parameter metadata must not reference unknown functions.
        for function_name in self.function_params:
            if function_name not in function_names:
                raise BytecodeValidationError(
                    "Function parameter metadata references unknown "
                    f"function '{function_name}'."
                )

        for function_name, params in self.function_params.items():
            if len(params) > MAX_PARAMETERS:
                raise BytecodeValidationError(
                    f"Function '{function_name}' has too many parameters."
                )

        # Validate source map.
        previous_instruction = -1

        for entry in self.source_map:
            if len(entry) != SOURCE_MAP_ENTRY_SIZE:
                raise BytecodeValidationError(
                    "Invalid source-map entry."
                )

            instruction, line, column = entry

            if instruction < 0:
                raise BytecodeValidationError(
                    "Source-map instruction index cannot be negative."
                )

            if instruction >= len(self.instructions):
                raise BytecodeValidationError(
                    "Source-map instruction index is out of range."
                )

            if instruction < previous_instruction:
                raise BytecodeValidationError(
                    "Source-map entries must be sorted."
                )

            if line < 0 or column < 0:
                raise BytecodeValidationError(
                    "Source-map line/column cannot be negative."
                )

            previous_instruction = instruction

    # ──────────────────────────────────────────────────────────────────────
    # Serialization
    # ──────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """
        Produce a deterministic JSON-compatible representation.

        This is an interchange/debug representation, not the canonical
        binary .atcb wire format.
        """

        return {
            "magic": BYTECODE_MAGIC.decode("ascii"),
            "bytecode_version": list(self.bytecode_version),
            "compiler_version": self.compiler_version,
            "language_version": self.language_version,
            "source_map_version": self.source_map_version,
            "module": self.name,
            "entry_point": self.entry_point,
            "constants": _json_safe(self.constants),
            "instructions": [
                instruction.to_dict()
                for instruction in self.instructions
            ],
            "functions": {
                name: [
                    instruction.to_dict()
                    for instruction in instructions
                ]
                for name, instructions in self.functions.items()
            },
            "exports": list(self.exports),
            "function_params": {
                name: list(params)
                for name, params in self.function_params.items()
            },
            "source_map": [
                list(entry)
                for entry in self.source_map
            ],
        }

    def to_json(
        self,
        *,
        indent: Optional[int] = 2,
    ) -> str:
        return json.dumps(
            self.to_dict(),
            indent=indent,
            ensure_ascii=False,
            sort_keys=False,
        )

    # ──────────────────────────────────────────────────────────────────────
    # Disassembly
    # ──────────────────────────────────────────────────────────────────────

    def disassemble(self) -> str:
        return disassemble(self)


# ══════════════════════════════════════════════════════════════════════════════
# BYTECODE BUILDER
# ══════════════════════════════════════════════════════════════════════════════


class BytecodeBuilder:
    """
    Small, stateful helper used by compiler submodules.

    This keeps instruction emission out of expressions.py/statements.py
    while retaining a simple compiler API.
    """

    def __init__(self) -> None:
        self.instructions: List[Instruction] = []
        self.source_map = SourceMap()

    def emit(
        self,
        op: Any,
        *args: Any,
        line: int = UNKNOWN_SOURCE_LINE,
        column: int = UNKNOWN_SOURCE_COLUMN,
    ) -> int:
        if len(self.instructions) >= MAX_INSTRUCTIONS:
            raise BytecodeValidationError(
                "Maximum instruction count exceeded."
            )

        index = len(self.instructions)

        instruction = Instruction(
            op=op,
            args=list(args),
            line=line,
            column=column,
        )

        self.instructions.append(instruction)

        if line or column:
            self.source_map.add(
                instruction=index,
                line=line,
                column=column,
            )

        return index

    def patch(
        self,
        index: int,
        *args: Any,
    ) -> None:
        if index < 0 or index >= len(self.instructions):
            raise BytecodeValidationError(
                f"Invalid instruction patch index: {index}"
            )

        self.instructions[index].args = list(args)

    def current_position(self) -> int:
        return len(self.instructions)

    def build(self) -> List[Instruction]:
        return [
            instruction.copy()
            for instruction in self.instructions
        ]


# ══════════════════════════════════════════════════════════════════════════════
# DISASSEMBLER
# ══════════════════════════════════════════════════════════════════════════════


def disassemble(
    module: CompiledModule,
    *,
    include_source_map: bool = False,
) -> str:
    """
    Human-readable ATC bytecode disassembly.

    Example:

        === ATC Bytecode: main ===
        Version: 1.0
        Instrs: 3 | Fns: 1 | Constants: 2

        [MAIN]
          0000  PUSH         42
          0001  STORE        'x'
          0002  HALT
    """

    module.validate()

    lines: List[str] = [
        f"=== ATC Bytecode: {module.name} ===",
        (
            f"Version: {module.bytecode_version[0]}."
            f"{module.bytecode_version[1]}"
        ),
        (
            f"Compiler: {module.compiler_version} | "
            f"Instrs: {len(module.instructions)} | "
            f"Fns: {len(module.functions)} | "
            f"Constants: {len(module.constants)}"
        ),
        f"Exports: {module.exports}",
        "",
        "[CONSTANTS]",
    ]

    if module.constants:
        for index, value in enumerate(module.constants):
            lines.append(
                f"  [{index:04d}] {value!r}"
            )
    else:
        lines.append("  <none>")

    lines.append("")
    lines.append("[MAIN]")

    for index, instruction in enumerate(module.instructions):
        lines.append(
            _format_instruction(
                index,
                instruction,
                source_map=module.source_map
                if include_source_map
                else None,
            )
        )

    for function_name, instructions in module.functions.items():
        lines.append("")
        lines.append(f"[FN: {function_name}]")

        params = module.function_params.get(
            function_name,
            [],
        )

        if params:
            lines.append(
                f"  ; params: {', '.join(params)}"
            )

        for index, instruction in enumerate(instructions):
            lines.append(
                _format_instruction(
                    index,
                    instruction,
                    source_map=None,
                )
            )

    return "\n".join(lines)


def _format_instruction(
    index: int,
    instruction: Instruction,
    *,
    source_map: Optional[List[Tuple[int, int, int]]] = None,
) -> str:
    args = ""

    if instruction.args:
        args = " ".join(
            repr(argument)
            for argument in instruction.args
        )

    source = ""

    if source_map is not None:
        location = _lookup_source_map(
            source_map,
            index,
        )

        if location is not None:
            _, line, column = location
            source = f"  ; {line}:{column}"

    return (
        f"  {index:04d}  "
        f"{instruction.opcode_name:<12} "
        f"{args}{source}"
    )


def _lookup_source_map(
    source_map: List[Tuple[int, int, int]],
    instruction: int,
) -> Optional[Tuple[int, int, int]]:
    result = None

    for entry in source_map:
        if len(entry) != SOURCE_MAP_ENTRY_SIZE:
            continue

        if entry[0] > instruction:
            break

        result = entry

    return result


# ══════════════════════════════════════════════════════════════════════════════
# SERIALIZATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def serialize_json(
    module: CompiledModule,
    *,
    indent: Optional[int] = 2,
) -> bytes:
    """
    Serialize a module into a JSON debug/interchange artifact.

    This intentionally is NOT the canonical .atcb binary encoding.
    """
    return module.to_json(indent=indent).encode("utf-8")


def write_json(
    module: CompiledModule,
    path: str,
    *,
    indent: Optional[int] = 2,
) -> None:
    with open(path, "wb") as handle:
        handle.write(
            serialize_json(
                module,
                indent=indent,
            )
        )


# ══════════════════════════════════════════════════════════════════════════════
# MINIMAL BINARY CONTAINER
# ══════════════════════════════════════════════════════════════════════════════


def encode_container(module: CompiledModule) -> bytes:
    """
    Encode a validated module into a deterministic ATCB container.

    Layout:

        4 bytes   MAGIC
        1 byte    major
        1 byte    minor
        4 bytes   payload length, big endian
        N bytes   UTF-8 JSON payload

    The container is deliberately conservative. VM-specific instruction
    encoding remains the responsibility of the ATC VM/ABI layer.

    This makes compiler artifacts versioned and identifiable without
    coupling the compiler to a particular binary instruction serializer.
    """

    module.validate()

    payload = serialize_json(
        module,
        indent=None,
    )

    header = (
        BYTECODE_MAGIC
        + bytes(
            (
                module.bytecode_version[0],
                module.bytecode_version[1],
            )
        )
        + struct.pack(
            ">I",
            len(payload),
        )
    )

    return header + payload


def decode_container(data: bytes) -> Dict[str, Any]:
    """
    Decode the outer ATCB container.

    Returns the JSON metadata payload as a dictionary.

    Instruction reconstruction is intentionally not performed here because
    opcode resolution belongs to the VM ABI layer.
    """

    minimum_size = 10

    if len(data) < minimum_size:
        raise BytecodeFormatError(
            "ATCB payload is too small."
        )

    magic = data[:4]

    if magic != BYTECODE_MAGIC:
        raise BytecodeFormatError(
            f"Invalid ATCB magic: {magic!r}"
        )

    major = data[4]
    minor = data[5]

    if (major, minor) != BYTECODE_VERSION:
        raise BytecodeFormatError(
            "Unsupported ATCB version: "
            f"{major}.{minor}"
        )

    payload_length = struct.unpack(
        ">I",
        data[6:10],
    )[0]

    payload = data[10:]

    if len(payload) != payload_length:
        raise BytecodeFormatError(
            "ATCB payload length mismatch."
        )

    try:
        decoded = json.loads(
            payload.decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BytecodeFormatError(
            "Invalid ATCB JSON payload."
        ) from exc

    if not isinstance(decoded, dict):
        raise BytecodeFormatError(
            "ATCB root payload must be an object."
        )

    return decoded


def write_container(
    module: CompiledModule,
    path: str,
) -> None:
    with open(path, "wb") as handle:
        handle.write(
            encode_container(module)
        )


def read_container(
    path: str,
) -> Dict[str, Any]:
    with open(path, "rb") as handle:
        return decode_container(
            handle.read()
        )


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANT HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def add_constant(
    constants: List[Any],
    value: Any,
) -> int:
    """
    Add a constant to the pool and return its index.

    Constants are deduplicated using normal Python equality where possible.
    """

    if len(constants) >= MAX_CONSTANTS:
        raise BytecodeValidationError(
            "Maximum constant-pool size exceeded."
        )

    for index, existing in enumerate(constants):
        try:
            if existing == value:
                return index
        except Exception:
            # Objects with unusual equality semantics are treated as
            # distinct constants.
            continue

    constants.append(value)
    return len(constants) - 1


# ══════════════════════════════════════════════════════════════════════════════
# JSON SAFETY
# ══════════════════════════════════════════════════════════════════════════════


def _json_safe(value: Any) -> Any:
    """
    Convert common compiler values into deterministic JSON-compatible data.

    Runtime objects are represented by repr() rather than silently dropped.
    """

    if value is None:
        return None

    if isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, bytes):
        return {
            "__type__": "bytes",
            "hex": value.hex(),
        }

    if isinstance(value, tuple):
        return [
            _json_safe(item)
            for item in value
        ]

    if isinstance(value, list):
        return [
            _json_safe(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            str(key): _json_safe(item)
            for key, item in value.items()
        }

    return {
        "__type__": "repr",
        "value": repr(value),
    }


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════


__all__ = [
    # Errors
    "BytecodeError",
    "BytecodeValidationError",
    "BytecodeFormatError",

    # Version
    "BYTECODE_VERSION",

    # Core structures
    "Instruction",
    "FunctionBytecode",
    "CompiledModule",

    # Source maps
    "SourceMapEntry",
    "SourceMap",

    # Builder
    "BytecodeBuilder",

    # Disassembly
    "disassemble",

    # Serialization
    "serialize_json",
    "write_json",
    "encode_container",
    "decode_container",
    "write_container",
    "read_container",

    # Constants
    "add_constant",
]