# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Bytecode
===========================

Zentrale Bytecode-Datenstrukturen für ATCLang v0.3.1.

Verantwortlichkeiten
--------------------
- Instruction-Repräsentation
- CompiledModule
- FunctionBytecode
- Bytecode-Versionierung
- Bytecode-Validierung
- Source-Map-Anbindung
- Function-/Export-Metadaten
- Bytecode-Disassembly
- Debug-/Interchange-Serialisierung
- Versionierter äußerer ATCB-Container

Architektur
-----------

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
ConstantPool
  ↓
BytecodeBuilder
  ↓
CompiledModule
  ↓
Bytecode ABI / Emitter
  ↓
ATC VM

Dependency Boundary
-------------------

bytecode.py
    ├── constants.py
    └── errors.py

Dieses Modul darf NICHT von folgenden Schichten abhängen:

- Parser
- AST
- Compiler
- VM
- Runtime
- Optimizer

Constant-Pool Boundary
----------------------

Die semantische Constant-Pool-Verwaltung gehört ausschließlich
in constants.py.

Insbesondere werden hier NICHT erneut implementiert:

- Constant Deduplication
- Constant Index Allocation
- Constant Validation
- Constant Pool Quotas
- Constant Freeze Semantics

Die finale binäre Kodierung von Konstanten gehört ebenfalls NICHT
in dieses Modul.

Die normative ABI-Schicht wird separat definiert:

    bytecode_abi.py

Dort müssen insbesondere festgelegt werden:

- Integer-Breite / Integer-Encoding
- Float-Encoding
- String-Encoding
- Bytes-Encoding
- Constant Record Encoding
- Instruction Encoding
- ATCB Section Layout

Der hier implementierte ATCB-Container ist daher ausdrücklich
KEIN finales normatives Bytecode-ABI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import struct
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
)

from .constants import (
    Constant,
    ConstantPool,
    ConstantPoolLimits,
    ConstantType,
    infer_constant_type,
)


# ══════════════════════════════════════════════════════════════════════════════
# VERSION
# ══════════════════════════════════════════════════════════════════════════════

ATCLANG_VERSION = "0.3.1"

BYTECODE_VERSION_MAJOR = 1
BYTECODE_VERSION_MINOR = 0

BYTECODE_VERSION: Tuple[int, int] = (
    BYTECODE_VERSION_MAJOR,
    BYTECODE_VERSION_MINOR,
)

BYTECODE_MAGIC = b"ATCB"

SOURCE_MAP_VERSION = 1
SOURCE_MAP_ENTRY_SIZE = 3

UNKNOWN_SOURCE_LINE = 0
UNKNOWN_SOURCE_COLUMN = 0


# ══════════════════════════════════════════════════════════════════════════════
# LIMITS
# ══════════════════════════════════════════════════════════════════════════════


class BytecodeLimits:
    """
    Modulweite Bytecode-Grenzen.

    Diese Grenzen betreffen die semantische Compiler-Repräsentation.

    Die exakten Feldbreiten und Wire-Format-Grenzen des finalen
    ATC-Bytecode-ABI werden separat in bytecode_abi.py definiert.
    """

    MAX_CONSTANTS = ConstantPoolLimits.MAX_ENTRIES
    MAX_INSTRUCTIONS = 1_000_000
    MAX_FUNCTIONS = 65_535
    MAX_EXPORTS = 65_535
    MAX_PARAMETERS = 65_535
    MAX_MODULE_NAME_LENGTH = 4_096


MAX_CONSTANTS = BytecodeLimits.MAX_CONSTANTS
MAX_INSTRUCTIONS = BytecodeLimits.MAX_INSTRUCTIONS
MAX_FUNCTIONS = BytecodeLimits.MAX_FUNCTIONS
MAX_EXPORTS = BytecodeLimits.MAX_EXPORTS
MAX_PARAMETERS = BytecodeLimits.MAX_PARAMETERS
MAX_MODULE_NAME_LENGTH = BytecodeLimits.MAX_MODULE_NAME_LENGTH


# ══════════════════════════════════════════════════════════════════════════════
# ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class BytecodeError(Exception):
    """Base exception for bytecode errors."""


class BytecodeValidationError(BytecodeError):
    """Raised when bytecode violates compiler invariants."""


class BytecodeFormatError(BytecodeError):
    """Raised when serialized bytecode has an invalid format."""


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def _require_exact_int(
    value: Any,
    *,
    name: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> None:
    """
    Validate an exact Python int.

    bool is deliberately rejected.
    """

    if type(value) is not int:
        raise BytecodeValidationError(
            f"{name} must be an integer."
        )

    if minimum is not None and value < minimum:
        raise BytecodeValidationError(
            f"{name} must be >= {minimum}."
        )

    if maximum is not None and value > maximum:
        raise BytecodeValidationError(
            f"{name} must be <= {maximum}."
        )


def _validate_identifier(
    value: Any,
    *,
    name: str,
    maximum_length: Optional[int] = None,
) -> None:
    """Validate a compiler identifier-like string."""

    if type(value) is not str:
        raise BytecodeValidationError(
            f"{name} must be a string."
        )

    if not value:
        raise BytecodeValidationError(
            f"{name} must not be empty."
        )

    if maximum_length is not None and len(value) > maximum_length:
        raise BytecodeValidationError(
            f"{name} exceeds maximum length "
            f"{maximum_length}."
        )


# ══════════════════════════════════════════════════════════════════════════════
# INSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(slots=True)
class Instruction:
    """
    Single ATC VM instruction.

    The compiler deliberately does not own the VM opcode enum.

    op
        Opcode object or opcode identifier.

    args
        Positional operands.

    line, column
        Convenience source metadata.

    The final binary representation is defined by the ABI layer.
    """

    op: Any
    args: List[Any] = field(default_factory=list)
    line: int = UNKNOWN_SOURCE_LINE
    column: int = UNKNOWN_SOURCE_COLUMN

    def __post_init__(self) -> None:
        if isinstance(self.args, list):
            self.args = list(self.args)
        else:
            try:
                self.args = list(self.args)
            except TypeError as exc:
                raise BytecodeValidationError(
                    "Instruction args must be iterable."
                ) from exc

        _require_exact_int(
            self.line,
            name="Instruction.line",
            minimum=0,
        )

        _require_exact_int(
            self.column,
            name="Instruction.column",
            minimum=0,
        )

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

        name = getattr(
            self.op,
            "name",
            None,
        )

        if isinstance(name, str) and name:
            return name

        return str(self.op)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "op": self.opcode_name,
            "args": _json_safe(self.args),
            "line": self.line,
            "column": self.column,
        }

    def __str__(self) -> str:
        if self.args:
            arguments = " ".join(
                repr(argument)
                for argument in self.args
            )

            return (
                f"{self.opcode_name:<12} "
                f"{arguments}"
            )

        return self.opcode_name


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION BYTECODE
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(slots=True)
class FunctionBytecode:
    """
    Compiled function metadata.

    Functions retain their own instruction streams.

    This preserves the existing ATCLang function model while keeping
    function metadata explicit for downstream emitters and the VM ABI.
    """

    name: str
    instructions: List[Instruction] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    exports: bool = False

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _validate_identifier(
            self.name,
            name="Function name",
            maximum_length=MAX_MODULE_NAME_LENGTH,
        )

        if not isinstance(self.instructions, list):
            raise BytecodeValidationError(
                f"Function '{self.name}' instructions "
                "must be a list."
            )

        if len(self.instructions) > MAX_INSTRUCTIONS:
            raise BytecodeValidationError(
                f"Function '{self.name}' contains too many "
                "instructions."
            )

        if not isinstance(self.parameters, list):
            raise BytecodeValidationError(
                f"Function '{self.name}' parameters "
                "must be a list."
            )

        if len(self.parameters) > MAX_PARAMETERS:
            raise BytecodeValidationError(
                f"Function '{self.name}' has too many "
                "parameters."
            )

        if type(self.exports) is not bool:
            raise BytecodeValidationError(
                f"Function '{self.name}' exports must be bool."
            )

        seen = set()

        for parameter in self.parameters:
            _validate_identifier(
                parameter,
                name="Function parameter",
                maximum_length=MAX_MODULE_NAME_LENGTH,
            )

            if parameter in seen:
                raise BytecodeValidationError(
                    f"Duplicate parameter '{parameter}' "
                    f"in function '{self.name}'."
                )

            seen.add(parameter)

        for instruction in self.instructions:
            if not isinstance(
                instruction,
                Instruction,
            ):
                raise BytecodeValidationError(
                    f"Function '{self.name}' contains "
                    "an invalid instruction."
                )

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
    Maps an instruction index to a source position.
    """

    instruction: int
    line: int = UNKNOWN_SOURCE_LINE
    column: int = UNKNOWN_SOURCE_COLUMN

    def __post_init__(self) -> None:
        _require_exact_int(
            self.instruction,
            name="SourceMapEntry.instruction",
            minimum=0,
        )

        _require_exact_int(
            self.line,
            name="SourceMapEntry.line",
            minimum=0,
        )

        _require_exact_int(
            self.column,
            name="SourceMapEntry.column",
            minimum=0,
        )

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
    """
    Canonical source-map container.

    Entries must be stored in monotonically increasing
    instruction order.
    """

    version: int = SOURCE_MAP_VERSION
    entries: List[SourceMapEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require_exact_int(
            self.version,
            name="SourceMap.version",
            minimum=1,
        )

        self.entries = list(self.entries)

        self.validate()

    def validate(
        self,
        *,
        instruction_count: Optional[int] = None,
    ) -> None:
        previous_instruction = -1

        for entry in self.entries:
            if not isinstance(
                entry,
                SourceMapEntry,
            ):
                raise BytecodeValidationError(
                    "SourceMap contains an invalid entry."
                )

            if entry.instruction < previous_instruction:
                raise BytecodeValidationError(
                    "Source-map entries must be sorted."
                )

            if (
                instruction_count is not None
                and entry.instruction >= instruction_count
            ):
                raise BytecodeValidationError(
                    "Source-map instruction index is "
                    "out of range."
                )

            previous_instruction = entry.instruction

    def add(
        self,
        instruction: int,
        line: int,
        column: int = UNKNOWN_SOURCE_COLUMN,
    ) -> None:
        _require_exact_int(
            instruction,
            name="instruction",
            minimum=0,
        )

        _require_exact_int(
            line,
            name="line",
            minimum=0,
        )

        _require_exact_int(
            column,
            name="column",
            minimum=0,
        )

        if self.entries:
            previous = self.entries[-1]

            if instruction < previous.instruction:
                raise BytecodeValidationError(
                    "Source-map instruction indices "
                    "must be monotonically increasing."
                )

        self.entries.append(
            SourceMapEntry(
                instruction=instruction,
                line=line,
                column=column,
            )
        )

    def lookup(
        self,
        instruction: int,
    ) -> Optional[SourceMapEntry]:
        _require_exact_int(
            instruction,
            name="instruction",
            minimum=0,
        )

        result: Optional[SourceMapEntry] = None

        for entry in self.entries:
            if entry.instruction > instruction:
                break

            result = entry

        return result

    def to_list(self) -> List[Tuple[int, int, int]]:
        return [
            entry.to_tuple()
            for entry in self.entries
        ]

    @classmethod
    def from_list(
        cls,
        entries: Iterable[Sequence[int]],
        version: int = SOURCE_MAP_VERSION,
    ) -> "SourceMap":
        source_map = cls(
            version=version,
            entries=[],
        )

        for raw_entry in entries:
            if (
                not isinstance(
                    raw_entry,
                    Sequence,
                )
                or isinstance(
                    raw_entry,
                    (str, bytes),
                )
            ):
                raise BytecodeFormatError(
                    "Invalid source-map entry."
                )

            if len(raw_entry) != SOURCE_MAP_ENTRY_SIZE:
                raise BytecodeFormatError(
                    "Invalid source-map entry size."
                )

            values: List[int] = []

            for value in raw_entry:
                if type(value) is not int:
                    raise BytecodeFormatError(
                        "Source-map values must be integers."
                    )

                values.append(value)

            source_map.add(
                instruction=values[0],
                line=values[1],
                column=values[2],
            )

        return source_map


# ══════════════════════════════════════════════════════════════════════════════
# COMPILED MODULE
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class CompiledModule:
    """
    Complete compiler output.

    Constant-Pool Boundary
    ----------------------

    `constants` uses the canonical ConstantPool from constants.py.

    Legacy list-based construction is intentionally supported for
    migration compatibility. Such lists are normalized into a
    ConstantPool during initialization.

    This module does not define the final binary representation.
    """

    name: str

    instructions: List[Instruction] = field(
        default_factory=list
    )

    constants: ConstantPool | List[Any] = field(
        default_factory=ConstantPool
    )

    functions: Dict[
        str,
        List[Instruction],
    ] = field(
        default_factory=dict
    )

    exports: List[str] = field(
        default_factory=list
    )

    function_params: Dict[
        str,
        List[str],
    ] = field(
        default_factory=dict
    )

    source_map: List[
        Tuple[int, int, int]
    ] = field(
        default_factory=list
    )

    bytecode_version: Tuple[int, int] = (
        BYTECODE_VERSION
    )

    compiler_version: str = ATCLANG_VERSION

    source_map_version: int = (
        SOURCE_MAP_VERSION
    )

    language_version: str = "0.3.1"

    entry_point: str = "main"

    def __post_init__(self) -> None:
        self._normalize_constants()
        self.validate()

    # ──────────────────────────────────────────────────────────────────────
    # NORMALIZATION
    # ──────────────────────────────────────────────────────────────────────

    def _normalize_constants(self) -> None:
        if isinstance(
            self.constants,
            ConstantPool,
        ):
            return

        if not isinstance(
            self.constants,
            list,
        ):
            raise BytecodeValidationError(
                "constants must be a ConstantPool "
                "or a list."
            )

        pool = ConstantPool(
            max_size=MAX_CONSTANTS,
        )

        for value in self.constants:
            pool.add(value)

        self.constants = pool

    # ──────────────────────────────────────────────────────────────────────
    # COMPATIBILITY
    # ──────────────────────────────────────────────────────────────────────

    @property
    def constant_pool(self) -> ConstantPool:
        """Canonical ConstantPool accessor."""

        if not isinstance(
            self.constants,
            ConstantPool,
        ):
            self._normalize_constants()

        return self.constants

    def summary(self) -> str:
        return (
            f"Module '{self.name}' | "
            f"{len(self.instructions)} Instrs | "
            f"{len(self.functions)} Fns | "
            f"{self.constant_pool.size} Konstanten"
        )

    @property
    def instruction_count(self) -> int:
        return len(self.instructions)

    @property
    def function_count(self) -> int:
        return len(self.functions)

    @property
    def constant_count(self) -> int:
        return self.constant_pool.size

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
        return list(
            self.function_params.get(
                name,
                [],
            )
        )

    # ──────────────────────────────────────────────────────────────────────
    # SOURCE MAP
    # ──────────────────────────────────────────────────────────────────────

    def source_location(
        self,
        instruction: int,
    ) -> Optional[SourceMapEntry]:
        source_map = SourceMap.from_list(
            self.source_map,
            version=self.source_map_version,
        )

        return source_map.lookup(
            instruction
        )

    # ──────────────────────────────────────────────────────────────────────
    # VALIDATION
    # ──────────────────────────────────────────────────────────────────────

    def validate(self) -> None:
        _validate_identifier(
            self.name,
            name="Module name",
            maximum_length=MAX_MODULE_NAME_LENGTH,
        )

        if (
            not isinstance(
                self.bytecode_version,
                tuple,
            )
            or len(self.bytecode_version) != 2
        ):
            raise BytecodeValidationError(
                "bytecode_version must be a "
                "(major, minor) tuple."
            )

        major, minor = self.bytecode_version

        _require_exact_int(
            major,
            name="bytecode_version.major",
            minimum=0,
            maximum=255,
        )

        _require_exact_int(
            minor,
            name="bytecode_version.minor",
            minimum=0,
            maximum=255,
        )

        if self.bytecode_version != BYTECODE_VERSION:
            raise BytecodeValidationError(
                "Unsupported bytecode version: "
                f"{self.bytecode_version!r}; "
                f"expected {BYTECODE_VERSION!r}."
            )

        _validate_identifier(
            self.compiler_version,
            name="compiler_version",
        )

        _validate_identifier(
            self.language_version,
            name="language_version",
        )

        _require_exact_int(
            self.source_map_version,
            name="source_map_version",
            minimum=1,
        )

        _validate_identifier(
            self.entry_point,
            name="entry_point",
            maximum_length=MAX_MODULE_NAME_LENGTH,
        )

        if not isinstance(
            self.instructions,
            list,
        ):
            raise BytecodeValidationError(
                "Module instructions must be a list."
            )

        if len(self.instructions) > MAX_INSTRUCTIONS:
            raise BytecodeValidationError(
                "Module contains too many instructions."
            )

        for instruction in self.instructions:
            if not isinstance(
                instruction,
                Instruction,
            ):
                raise BytecodeValidationError(
                    "Module contains an invalid instruction."
                )

        pool = self.constant_pool

        if pool.size > MAX_CONSTANTS:
            raise BytecodeValidationError(
                "Module contains too many constants."
            )

        if not isinstance(
            self.functions,
            dict,
        ):
            raise BytecodeValidationError(
                "Module functions must be a dictionary."
            )

        if len(self.functions) > MAX_FUNCTIONS:
            raise BytecodeValidationError(
                "Module contains too many functions."
            )

        if not isinstance(
            self.exports,
            list,
        ):
            raise BytecodeValidationError(
                "Module exports must be a list."
            )

        if len(self.exports) > MAX_EXPORTS:
            raise BytecodeValidationError(
                "Module contains too many exports."
            )

        function_names = set()

        for function_name, instructions in self.functions.items():
            _validate_identifier(
                function_name,
                name="Function name",
                maximum_length=MAX_MODULE_NAME_LENGTH,
            )

            if function_name in function_names:
                raise BytecodeValidationError(
                    f"Duplicate function '{function_name}'."
                )

            function_names.add(function_name)

            if not isinstance(
                instructions,
                list,
            ):
                raise BytecodeValidationError(
                    f"Function '{function_name}' "
                    "instructions must be a list."
                )

            if len(instructions) > MAX_INSTRUCTIONS:
                raise BytecodeValidationError(
                    f"Function '{function_name}' contains "
                    "too many instructions."
                )

            for instruction in instructions:
                if not isinstance(
                    instruction,
                    Instruction,
                ):
                    raise BytecodeValidationError(
                        f"Function '{function_name}' contains "
                        "an invalid instruction."
                    )

        seen_exports = set()

        for export in self.exports:
            _validate_identifier(
                export,
                name="Export",
                maximum_length=MAX_MODULE_NAME_LENGTH,
            )

            if export in seen_exports:
                raise BytecodeValidationError(
                    f"Duplicate export '{export}'."
                )

            seen_exports.add(export)

            if export not in function_names:
                raise BytecodeValidationError(
                    f"Export '{export}' does not reference "
                    "a function."
                )

        if not isinstance(
            self.function_params,
            dict,
        ):
            raise BytecodeValidationError(
                "function_params must be a dictionary."
            )

        for function_name, params in self.function_params.items():
            if function_name not in function_names:
                raise BytecodeValidationError(
                    "Function parameter metadata references "
                    f"unknown function '{function_name}'."
                )

            if not isinstance(
                params,
                list,
            ):
                raise BytecodeValidationError(
                    f"Parameters of function "
                    f"'{function_name}' must be a list."
                )

            if len(params) > MAX_PARAMETERS:
                raise BytecodeValidationError(
                    f"Function '{function_name}' has too "
                    "many parameters."
                )

            seen_params = set()

            for parameter in params:
                _validate_identifier(
                    parameter,
                    name="Function parameter",
                    maximum_length=MAX_MODULE_NAME_LENGTH,
                )

                if parameter in seen_params:
                    raise BytecodeValidationError(
                        f"Duplicate parameter '{parameter}' "
                        f"in function '{function_name}'."
                    )

                seen_params.add(parameter)

        source_map = SourceMap.from_list(
            self.source_map,
            version=self.source_map_version,
        )

        source_map.validate(
            instruction_count=len(
                self.instructions
            ),
        )

    # ──────────────────────────────────────────────────────────────────────
    # FREEZE
    # ──────────────────────────────────────────────────────────────────────

    def freeze_constants(self) -> None:
        """
        Freeze the canonical ConstantPool.

        Nach diesem Punkt können keine neuen Konstanten mehr
        in den Pool aufgenommen werden.
        """

        self.constant_pool.freeze()

    @property
    def constants_frozen(self) -> bool:
        return self.constant_pool.is_frozen

    # ──────────────────────────────────────────────────────────────────────
    # SERIALIZATION
    # ──────────────────────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """
        Deterministische JSON-kompatible Darstellung.

        Dies ist ein Debug-/Interchange-Format.

        Es ist NICHT das normative ATC-Bytecode-Binary-Format.
        """

        self.validate()

        return {
            "magic": BYTECODE_MAGIC.decode("ascii"),
            "bytecode_version": list(
                self.bytecode_version
            ),
            "compiler_version": self.compiler_version,
            "language_version": self.language_version,
            "source_map_version": (
                self.source_map_version
            ),
            "module": self.name,
            "entry_point": self.entry_point,
            "constants": self.constant_pool.to_dict(),
            "instructions": [
                instruction.to_dict()
                for instruction in self.instructions
            ],
            "functions": {
                name: [
                    instruction.to_dict()
                    for instruction in instructions
                ]
                for name, instructions
                in self.functions.items()
            },
            "exports": list(self.exports),
            "function_params": {
                name: list(params)
                for name, params
                in self.function_params.items()
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
            separators=(
                None
                if indent is not None
                else (",", ":")
            ),
        )

    # ──────────────────────────────────────────────────────────────────────
    # DISASSEMBLY
    # ──────────────────────────────────────────────────────────────────────

    def disassemble(
        self,
        *,
        include_source_map: bool = False,
    ) -> str:
        return disassemble(
            self,
            include_source_map=include_source_map,
        )


# ══════════════════════════════════════════════════════════════════════════════
# BYTECODE BUILDER
# ══════════════════════════════════════════════════════════════════════════════


class BytecodeBuilder:
    """
    Stateful helper für Compiler-Komponenten.

    Der Builder besitzt keine AST- oder Compiler-Abhängigkeit.
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

        self.instructions.append(
            instruction
        )

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
        _require_exact_int(
            index,
            name="patch index",
            minimum=0,
        )

        if index >= len(self.instructions):
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
    Human-readable ATC Bytecode Disassembly.
    """

    module.validate()

    lines: List[str] = [
        f"=== ATC Bytecode: {module.name} ===",
        (
            f"Version: "
            f"{module.bytecode_version[0]}."
            f"{module.bytecode_version[1]}"
        ),
        (
            f"Compiler: {module.compiler_version} | "
            f"Instrs: {len(module.instructions)} | "
            f"Fns: {len(module.functions)} | "
            f"Constants: {module.constant_count}"
        ),
        f"Entry: {module.entry_point}",
        f"Exports: {module.exports}",
        "",
        "[CONSTANTS]",
    ]

    if module.constant_pool.size:
        for constant in module.constant_pool:
            lines.append(
                _format_constant(
                    constant
                )
            )
    else:
        lines.append(
            "  <none>"
        )

    lines.append("")
    lines.append("[MAIN]")

    for index, instruction in enumerate(
        module.instructions
    ):
        lines.append(
            _format_instruction(
                index,
                instruction,
                source_map=(
                    module.source_map
                    if include_source_map
                    else None
                ),
            )
        )

    for function_name, instructions in (
        module.functions.items()
    ):
        lines.append("")
        lines.append(
            f"[FN: {function_name}]"
        )

        params = module.function_params.get(
            function_name,
            [],
        )

        if params:
            lines.append(
                "  ; params: "
                + ", ".join(params)
            )

        for index, instruction in enumerate(
            instructions
        ):
            lines.append(
                _format_instruction(
                    index,
                    instruction,
                    source_map=None,
                )
            )

    return "\n".join(lines)


def _format_constant(
    constant: Constant,
) -> str:
    if constant.type is ConstantType.BYTES:
        value = (
            "0x"
            + constant.value.hex()
        )
    else:
        value = repr(
            constant.value
        )

    return (
        f"  [{constant.index:04d}] "
        f"{constant.type.value:<7} "
        f"{value}"
    )


def _format_instruction(
    index: int,
    instruction: Instruction,
    *,
    source_map: Optional[
        List[Tuple[int, int, int]]
    ] = None,
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

            source = (
                f"  ; "
                f"{line}:{column}"
            )

    return (
        f"  {index:04d}  "
        f"{instruction.opcode_name:<12} "
        f"{args}{source}"
    )


def _lookup_source_map(
    source_map: List[
        Tuple[int, int, int]
    ],
    instruction: int,
) -> Optional[
    Tuple[int, int, int]
]:
    result = None

    for entry in source_map:
        if len(entry) != SOURCE_MAP_ENTRY_SIZE:
            continue

        if entry[0] > instruction:
            break

        result = entry

    return result


# ══════════════════════════════════════════════════════════════════════════════
# JSON SERIALIZATION
# ══════════════════════════════════════════════════════════════════════════════


def serialize_json(
    module: CompiledModule,
    *,
    indent: Optional[int] = 2,
) -> bytes:
    """
    Serialize module into UTF-8 JSON.

    Dies ist ausschließlich ein Debug-/Interchange-Format.
    """

    module.validate()

    return module.to_json(
        indent=indent
    ).encode("utf-8")


def write_json(
    module: CompiledModule,
    path: str,
    *,
    indent: Optional[int] = 2,
) -> None:
    data = serialize_json(
        module,
        indent=indent,
    )

    with open(
        path,
        "wb",
    ) as handle:
        handle.write(data)


# ══════════════════════════════════════════════════════════════════════════════
# ATCB OUTER CONTAINER
# ══════════════════════════════════════════════════════════════════════════════


def encode_container(
    module: CompiledModule,
) -> bytes:
    """
    Encode a versioned ATCB outer container.

    Layout
    ------

        4 bytes   MAGIC
        1 byte    major version
        1 byte    minor version
        4 bytes   payload length, big endian
        N bytes   UTF-8 JSON payload

    IMPORTANT
    ---------

    Dies ist kein finales normatives ATC Bytecode ABI.

    Der Container dient ausschließlich dazu, Compiler-Artefakte
    eindeutig zu markieren und versioniert zu transportieren.

    Die finale Binary-Encoding-Schicht wird von bytecode_abi.py
    bereitgestellt.
    """

    module.validate()

    payload = serialize_json(
        module,
        indent=None,
    )

    if len(payload) > 0xFFFFFFFF:
        raise BytecodeFormatError(
            "ATCB payload exceeds container length limit."
        )

    major, minor = module.bytecode_version

    header = (
        BYTECODE_MAGIC
        + bytes(
            (
                major,
                minor,
            )
        )
        + struct.pack(
            ">I",
            len(payload),
        )
    )

    return header + payload


def decode_container(
    data: bytes,
) -> Dict[str, Any]:
    """
    Decode the outer ATCB container.

    Returns the JSON metadata dictionary.

    Opcode and VM-specific instruction reconstruction remains
    outside this module.
    """

    if type(data) is not bytes:
        raise BytecodeFormatError(
            "ATCB container must be bytes."
        )

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

    if (
        major,
        minor,
    ) != BYTECODE_VERSION:
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
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise BytecodeFormatError(
            "Invalid ATCB JSON payload."
        ) from exc

    if not isinstance(
        decoded,
        dict,
    ):
        raise BytecodeFormatError(
            "ATCB root payload must be an object."
        )

    if decoded.get("magic") != BYTECODE_MAGIC.decode(
        "ascii"
    ):
        raise BytecodeFormatError(
            "ATCB metadata magic mismatch."
        )

    return decoded


def write_container(
    module: CompiledModule,
    path: str,
) -> None:
    data = encode_container(
        module
    )

    with open(
        path,
        "wb",
    ) as handle:
        handle.write(data)


def read_container(
    path: str,
) -> Dict[str, Any]:
    with open(
        path,
        "rb",
    ) as handle:
        return decode_container(
            handle.read()
        )


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANT HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def add_constant(
    constants: ConstantPool | List[Any],
    value: Any,
) -> int:
    """
    Compatibility helper.

    Canonical implementation
    ------------------------

    Bei einem ConstantPool wird ausschließlich dessen eigene
    add()-Implementierung verwendet.

    Eine rohe List[Any] wird aus Kompatibilitätsgründen weiterhin
    unterstützt. Neue Compiler-Komponenten sollten jedoch direkt
    ConstantPool verwenden.
    """

    if isinstance(
        constants,
        ConstantPool,
    ):
        return constants.add(value)

    if not isinstance(
        constants,
        list,
    ):
        raise BytecodeValidationError(
            "constants must be a ConstantPool or list."
        )

    if len(constants) >= MAX_CONSTANTS:
        raise BytecodeValidationError(
            "Maximum constant-pool size exceeded."
        )

    constant_type = infer_constant_type(
        value
    )

    key = (
        constant_type,
        value,
    )

    for index, existing in enumerate(
        constants
    ):
        try:
            existing_type = infer_constant_type(
                existing
            )

            if (
                existing_type,
                existing,
            ) == key:
                return index

        except Exception:
            continue

    constants.append(value)

    return len(constants) - 1


# ══════════════════════════════════════════════════════════════════════════════
# JSON SAFETY
# ══════════════════════════════════════════════════════════════════════════════


def _json_safe(
    value: Any,
) -> Any:
    """
    Convert compiler values into deterministic JSON-compatible data.

    Runtime objects are represented by repr().

    bytes are represented explicitly as hexadecimal data.
    """

    if value is None:
        return None

    if type(value) is bool:
        return value

    if type(value) is int:
        return value

    if type(value) is float:
        if not math.isfinite(value):
            raise BytecodeFormatError(
                "Non-finite float cannot be encoded as JSON."
            )

        return value

    if type(value) is str:
        return value

    if type(value) is bytes:
        return {
            "__type__": "bytes",
            "hex": value.hex(),
        }

    if isinstance(
        value,
        Constant,
    ):
        return {
            "index": value.index,
            "type": value.type.value,
            "value": _json_safe(
                value.value
            ),
        }

    if isinstance(
        value,
        tuple,
    ):
        return [
            _json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        list,
    ):
        return [
            _json_safe(item)
            for item in value
        ]

    if isinstance(
        value,
        dict,
    ):
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
    # Version
    "ATCLANG_VERSION",
    "BYTECODE_VERSION_MAJOR",
    "BYTECODE_VERSION_MINOR",
    "BYTECODE_VERSION",
    "BYTECODE_MAGIC",

    # Limits
    "BytecodeLimits",
    "MAX_CONSTANTS",
    "MAX_INSTRUCTIONS",
    "MAX_FUNCTIONS",
    "MAX_EXPORTS",
    "MAX_PARAMETERS",
    "MAX_MODULE_NAME_LENGTH",

    # Errors
    "BytecodeError",
    "BytecodeValidationError",
    "BytecodeFormatError",

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

    # Compatibility constant helper
    "add_constant",
]