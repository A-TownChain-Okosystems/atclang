# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Bytecode ABI
====================

Normative Binary Application Binary Interface für ATCLang / ATC-92.

Dieses Modul definiert das kanonische Binary-Encoding des ATCLang
Bytecodes.

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
bytecode_abi.py
  ↓
ATCB Binary
  ↓
ATC VM

Verantwortlichkeiten
--------------------

- ATCB Header
- ABI-Versionierung
- Section Layout
- Integer-Encoding
- Float-Encoding
- String-Encoding
- Bytes-Encoding
- Constant Record Encoding
- Instruction Encoding
- Function Encoding
- Export Encoding
- Source-Map Encoding
- Deterministische Binary-Ausgabe
- Binary Decode / Validation
- Roundtrip-Integrität

Dependency Boundary
-------------------

bytecode_abi.py darf nur von den Bytecode-/Constant-Pool-Schichten
abhängen.

Erlaubte Abhängigkeiten:

    bytecode.py
    constants.py
    errors.py

Keine Abhängigkeiten auf:

    Parser
    AST
    Compiler
    VM
    Runtime
    Optimizer

WICHTIG
-------

Dieses Modul definiert die normative Binary-Repräsentation.

Im Gegensatz zum Debug-/Interchange-Container aus bytecode.py ist
das hier definierte Format das kanonische ATCLang/ATC-92 ABI.

Alle Mehrbyte-Zahlen werden Big-Endian kodiert.

Keine implizite Host-Endianness darf verwendet werden.

ABI-Version
-----------

Major-Version:

    Änderung inkompatibel mit älteren Decodern.

Minor-Version:

    Rückwärtskompatible Erweiterung innerhalb derselben ABI-Major-Version.

Container
---------

ATCB:

    Header
    Sections...

Normativer Header:

    4 bytes  magic = "ATCB"
    1 byte   ABI major
    1 byte   ABI minor
    1 byte   flags
    1 byte   reserved
    4 bytes  section count
    4 bytes  total payload length
    4 bytes  header checksum

Alle Offsets/Längen innerhalb des ABI sind explizit und werden nicht
aus Python-Objektgrößen abgeleitet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import math
import struct
from typing import (
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
)

from .bytecode import (
    BYTECODE_MAGIC,
    BYTECODE_VERSION,
    BytecodeFormatError,
    BytecodeValidationError,
    CompiledModule,
    FunctionBytecode,
    Instruction,
    SourceMap,
)
from .constants import (
    Constant,
    ConstantPool,
    ConstantType,
)


# ══════════════════════════════════════════════════════════════════════════════
# ABI VERSION
# ══════════════════════════════════════════════════════════════════════════════

ABI_MAGIC = BYTECODE_MAGIC

ABI_VERSION_MAJOR = 1
ABI_VERSION_MINOR = 0

ABI_VERSION: Tuple[int, int] = (
    ABI_VERSION_MAJOR,
    ABI_VERSION_MINOR,
)


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

HEADER_SIZE = 20

HEADER_FLAGS_NONE = 0

_HEADER_STRUCT = struct.Struct(">4sBBBBIII")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION TYPES
# ══════════════════════════════════════════════════════════════════════════════


class SectionType(IntEnum):
    """
    Normative ATCB section identifiers.
    """

    METADATA = 1
    CONSTANTS = 2
    MAIN_CODE = 3
    FUNCTIONS = 4
    EXPORTS = 5
    SOURCE_MAP = 6


SECTION_HEADER_SIZE = 8

_SECTION_HEADER_STRUCT = struct.Struct(">II")


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANT TYPES
# ══════════════════════════════════════════════════════════════════════════════


class ABIConstantType(IntEnum):
    """
    Normative constant record type identifiers.

    The mapping is intentionally independent from the Python enum values.
    """

    NULL = 0x01
    BOOL = 0x02
    INT = 0x03
    FLOAT = 0x04
    STRING = 0x05
    BYTES = 0x06


# ══════════════════════════════════════════════════════════════════════════════
# INSTRUCTION FORMAT
# ══════════════════════════════════════════════════════════════════════════════


"""
Instruction record:

    1 byte    opcode
    1 byte    operand count
    N bytes   operands

Operand:

    1 byte    operand type
    4 bytes   payload length
    N bytes   payload

This representation is deliberately explicit.

It does not assume that Python values or VM opcode enums have a
particular memory representation.
"""


class OperandType(IntEnum):
    """
    Normative operand encodings.
    """

    UINT = 0x01
    INT = 0x02
    FLOAT = 0x03
    STRING = 0x04
    BYTES = 0x05
    BOOL = 0x06
    NULL = 0x07
    CONSTANT_INDEX = 0x08


OPERAND_HEADER_SIZE = 5


# ══════════════════════════════════════════════════════════════════════════════
# METADATA
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class ABIMetadata:
    """
    Metadata encoded in the METADATA section.
    """

    module_name: str
    language_version: str
    compiler_version: str
    entry_point: str

    def validate(self) -> None:
        _require_string(
            self.module_name,
            "module_name",
        )
        _require_string(
            self.language_version,
            "language_version",
        )
        _require_string(
            self.compiler_version,
            "compiler_version",
        )
        _require_string(
            self.entry_point,
            "entry_point",
        )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class ABISection:
    """
    Complete ABI section.
    """

    type: SectionType
    payload: bytes

    def encode(self) -> bytes:
        return (
            _SECTION_HEADER_STRUCT.pack(
                int(self.type),
                len(self.payload),
            )
            + self.payload
        )


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION
# ══════════════════════════════════════════════════════════════════════════════


def _require_exact_int(
    value: Any,
    *,
    name: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> None:
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


def _require_string(
    value: Any,
    name: str,
) -> None:
    if type(value) is not str:
        raise BytecodeValidationError(
            f"{name} must be a string."
        )


def _require_bytes(
    value: Any,
    name: str,
) -> None:
    if type(value) is not bytes:
        raise BytecodeFormatError(
            f"{name} must be bytes."
        )


# ══════════════════════════════════════════════════════════════════════════════
# INTEGER ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def encode_u8(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u8",
        minimum=0,
        maximum=0xFF,
    )

    return struct.pack(
        ">B",
        value,
    )


def decode_u8(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(
        data,
        offset,
        1,
    )

    return data[offset], offset + 1


def encode_u16(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u16",
        minimum=0,
        maximum=0xFFFF,
    )

    return struct.pack(
        ">H",
        value,
    )


def decode_u16(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(
        data,
        offset,
        2,
    )

    return (
        struct.unpack(
            ">H",
            data[offset:offset + 2],
        )[0],
        offset + 2,
    )


def encode_u32(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u32",
        minimum=0,
        maximum=0xFFFFFFFF,
    )

    return struct.pack(
        ">I",
        value,
    )


def decode_u32(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(
        data,
        offset,
        4,
    )

    return (
        struct.unpack(
            ">I",
            data[offset:offset + 4],
        )[0],
        offset + 4,
    )


def encode_u64(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u64",
        minimum=0,
        maximum=0xFFFFFFFFFFFFFFFF,
    )

    return struct.pack(
        ">Q",
        value,
    )


def decode_u64(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(
        data,
        offset,
        8,
    )

    return (
        struct.unpack(
            ">Q",
            data[offset:offset + 8],
        )[0],
        offset + 8,
    )


def encode_i64(value: int) -> bytes:
    _require_exact_int(
        value,
        name="i64",
        minimum=-(1 << 63),
        maximum=(1 << 63) - 1,
    )

    return struct.pack(
        ">q",
        value,
    )


def decode_i64(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(
        data,
        offset,
        8,
    )

    return (
        struct.unpack(
            ">q",
            data[offset:offset + 8],
        )[0],
        offset + 8,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FLOAT ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def encode_f64(value: float) -> bytes:
    if type(value) is not float:
        raise BytecodeValidationError(
            "f64 value must be a float."
        )

    if not math.isfinite(value):
        raise BytecodeValidationError(
            "Non-finite floating-point values are forbidden."
        )

    return struct.pack(
        ">d",
        value,
    )


def decode_f64(
    data: bytes,
    offset: int = 0,
) -> Tuple[float, int]:
    _require_available(
        data,
        offset,
        8,
    )

    value = struct.unpack(
        ">d",
        data[offset:offset + 8],
    )[0]

    if not math.isfinite(value):
        raise BytecodeFormatError(
            "Non-finite f64 value in bytecode."
        )

    return value, offset + 8


# ══════════════════════════════════════════════════════════════════════════════
# STRING / BYTES ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def encode_bytes(value: bytes) -> bytes:
    _require_bytes(
        value,
        "bytes",
    )

    return (
        encode_u32(len(value))
        + value
    )


def decode_bytes(
    data: bytes,
    offset: int = 0,
) -> Tuple[bytes, int]:
    length, offset = decode_u32(
        data,
        offset,
    )

    _require_available(
        data,
        offset,
        length,
    )

    end = offset + length

    return (
        data[offset:end],
        end,
    )


def encode_string(value: str) -> bytes:
    _require_string(
        value,
        "string",
    )

    encoded = value.encode(
        "utf-8",
        errors="strict",
    )

    return encode_bytes(
        encoded
    )


def decode_string(
    data: bytes,
    offset: int = 0,
) -> Tuple[str, int]:
    raw, offset = decode_bytes(
        data,
        offset,
    )

    try:
        value = raw.decode(
            "utf-8",
            errors="strict",
        )
    except UnicodeDecodeError as exc:
        raise BytecodeFormatError(
            "Invalid UTF-8 string."
        ) from exc

    return value, offset


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANT ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def _constant_type(
    constant: Constant,
) -> ABIConstantType:
    value_type = constant.type

    name = getattr(
        value_type,
        "name",
        str(value_type),
    )

    normalized = str(name).upper()

    mapping = {
        "NULL": ABIConstantType.NULL,
        "NONE": ABIConstantType.NULL,
        "BOOL": ABIConstantType.BOOL,
        "BOOLEAN": ABIConstantType.BOOL,
        "INT": ABIConstantType.INT,
        "INTEGER": ABIConstantType.INT,
        "FLOAT": ABIConstantType.FLOAT,
        "STRING": ABIConstantType.STRING,
        "STR": ABIConstantType.STRING,
        "BYTES": ABIConstantType.BYTES,
    }

    if normalized not in mapping:
        raise BytecodeValidationError(
            f"Unsupported constant type: {value_type!r}"
        )

    return mapping[normalized]


def encode_constant(
    constant: Constant,
) -> bytes:
    """
    Encode one canonical constant record.

    Record:

        4 bytes   constant index
        1 byte    constant type
        N bytes   type payload
    """

    if not isinstance(
        constant,
        Constant,
    ):
        raise BytecodeValidationError(
            "Expected Constant."
        )

    _require_exact_int(
        constant.index,
        name="constant.index",
        minimum=0,
        maximum=0xFFFFFFFF,
    )

    constant_type = _constant_type(
        constant
    )

    payload = _encode_constant_payload(
        constant_type,
        constant.value,
    )

    return (
        encode_u32(
            constant.index
        )
        + encode_u8(
            int(constant_type)
        )
        + payload
    )


def _encode_constant_payload(
    constant_type: ABIConstantType,
    value: Any,
) -> bytes:
    if constant_type is ABIConstantType.NULL:
        if value is not None:
            raise BytecodeValidationError(
                "NULL constant must contain None."
            )

        return b""

    if constant_type is ABIConstantType.BOOL:
        if type(value) is not bool:
            raise BytecodeValidationError(
                "BOOL constant requires bool."
            )

        return encode_u8(
            1 if value else 0
        )

    if constant_type is ABIConstantType.INT:
        return encode_i64(
            value
        )

    if constant_type is ABIConstantType.FLOAT:
        return encode_f64(
            value
        )

    if constant_type is ABIConstantType.STRING:
        return encode_string(
            value
        )

    if constant_type is ABIConstantType.BYTES:
        return encode_bytes(
            value
        )

    raise BytecodeValidationError(
        f"Unsupported constant type: {constant_type!r}"
    )


def encode_constant_pool(
    pool: ConstantPool,
) -> bytes:
    """
    Encode the complete ConstantPool.

    Layout:

        u32 count
        repeated:
            ConstantRecord
    """

    if not isinstance(
        pool,
        ConstantPool,
    ):
        raise BytecodeValidationError(
            "Expected ConstantPool."
        )

    constants = list(pool)

    output = bytearray()

    output += encode_u32(
        len(constants)
    )

    for constant in constants:
        output += encode_constant(
            constant
        )

    return bytes(output)


# ══════════════════════════════════════════════════════════════════════════════
# OPERAND ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def _infer_operand_type(
    value: Any,
) -> OperandType:
    if value is None:
        return OperandType.NULL

    if type(value) is bool:
        return OperandType.BOOL

    if type(value) is int:
        return OperandType.INT

    if type(value) is float:
        return OperandType.FLOAT

    if type(value) is str:
        return OperandType.STRING

    if type(value) is bytes:
        return OperandType.BYTES

    if isinstance(
        value,
        Constant,
    ):
        return OperandType.CONSTANT_INDEX

    raise BytecodeValidationError(
        "Unsupported instruction operand type: "
        f"{type(value).__name__}"
    )


def _encode_operand_payload(
    operand_type: OperandType,
    value: Any,
) -> bytes:
    if operand_type is OperandType.NULL:
        return b""

    if operand_type is OperandType.BOOL:
        return encode_u8(
            1 if value else 0
        )

    if operand_type is OperandType.INT:
        return encode_i64(
            value
        )

    if operand_type is OperandType.UINT:
        return encode_u64(
            value
        )

    if operand_type is OperandType.FLOAT:
        return encode_f64(
            value
        )

    if operand_type is OperandType.STRING:
        return encode_string(
            value
        )

    if operand_type is OperandType.BYTES:
        return encode_bytes(
            value
        )

    if operand_type is OperandType.CONSTANT_INDEX:
        if not isinstance(
            value,
            Constant,
        ):
            raise BytecodeValidationError(
                "CONSTANT_INDEX operand requires Constant."
            )

        return encode_u32(
            value.index
        )

    raise BytecodeValidationError(
        f"Unsupported operand type: {operand_type!r}"
    )


def encode_operand(
    value: Any,
) -> bytes:
    operand_type = _infer_operand_type(
        value
    )

    payload = _encode_operand_payload(
        operand_type,
        value,
    )

    return (
        encode_u8(
            int(operand_type)
        )
        + encode_u32(
            len(payload)
        )
        + payload
    )


# ══════════════════════════════════════════════════════════════════════════════
# OPCODE ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def opcode_value(op: Any) -> int:
    """
    Convert an opcode object into its normative u8 value.

    Supported:

        IntEnum
        int

    String-only opcodes are deliberately rejected because strings do not
    provide a stable binary ABI.
    """

    if isinstance(
        op,
        IntEnum,
    ):
        value = int(op)
    elif type(op) is int:
        value = op
    else:
        raise BytecodeValidationError(
            "Opcode must be an IntEnum or exact int."
        )

    _require_exact_int(
        value,
        name="opcode",
        minimum=0,
        maximum=0xFF,
    )

    return value


def encode_instruction(
    instruction: Instruction,
) -> bytes:
    """
    Encode one instruction.

    Layout:

        u8 opcode
        u8 operand_count
        operand...
    """

    if not isinstance(
        instruction,
        Instruction,
    ):
        raise BytecodeValidationError(
            "Expected Instruction."
        )

    opcode = opcode_value(
        instruction.op
    )

    if len(instruction.args) > 0xFF:
        raise BytecodeValidationError(
            "Instruction has too many operands."
        )

    output = bytearray()

    output += encode_u8(
        opcode
    )

    output += encode_u8(
        len(instruction.args)
    )

    for argument in instruction.args:
        output += encode_operand(
            argument
        )

    return bytes(output)


def encode_instruction_stream(
    instructions: Sequence[Instruction],
) -> bytes:
    output = bytearray()

    output += encode_u32(
        len(instructions)
    )

    for instruction in instructions:
        encoded = encode_instruction(
            instruction
        )

        output += encode_u32(
            len(encoded)
        )

        output += encoded

    return bytes(output)


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def encode_function(
    function: FunctionBytecode,
) -> bytes:
    """
    Function record:

        string   function name
        u32      parameter count
        strings  parameters
        u8       export flag
        u32      instruction stream length
        bytes    instruction stream
    """

    function.validate()

    output = bytearray()

    output += encode_string(
        function.name
    )

    output += encode_u32(
        len(function.parameters)
    )

    for parameter in function.parameters:
        output += encode_string(
            parameter
        )

    output += encode_u8(
        1 if function.exports else 0
    )

    instructions = encode_instruction_stream(
        function.instructions
    )

    output += encode_u32(
        len(instructions)
    )

    output += instructions

    return bytes(output)


def encode_functions(
    functions: Mapping[str, Sequence[Instruction]],
    function_params: Mapping[str, Sequence[str]],
    exports: Sequence[str],
) -> bytes:
    output = bytearray()

    output += encode_u32(
        len(functions)
    )

    export_set = set(
        exports
    )

    for name, instructions in functions.items():
        function = FunctionBytecode(
            name=name,
            instructions=list(
                instructions
            ),
            parameters=list(
                function_params.get(
                    name,
                    [],
                )
            ),
            exports=name in export_set,
        )

        output += encode_function(
            function
        )

    return bytes(output)


# ══════════════════════════════════════════════════════════════════════════════
# EXPORT SECTION
# ══════════════════════════════════════════════════════════════════════════════


def encode_exports(
    exports: Sequence[str],
) -> bytes:
    output = bytearray()

    output += encode_u32(
        len(exports)
    )

    for export in exports:
        output += encode_string(
            export
        )

    return bytes(output)


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE MAP
# ══════════════════════════════════════════════════════════════════════════════


def encode_source_map(
    source_map: Iterable[Sequence[int]],
) -> bytes:
    """
    Source-map section:

        u32 version
        u32 entry count

        repeated:
            u32 instruction
            u32 line
            u32 column
    """

    entries = list(
        source_map
    )

    output = bytearray()

    version = 1

    output += encode_u32(
        version
    )

    output += encode_u32(
        len(entries)
    )

    previous = -1

    for entry in entries:
        if len(entry) != 3:
            raise BytecodeValidationError(
                "Invalid source-map entry."
            )

        instruction, line, column = entry

        _require_exact_int(
            instruction,
            name="source_map.instruction",
            minimum=0,
            maximum=0xFFFFFFFF,
        )

        _require_exact_int(
            line,
            name="source_map.line",
            minimum=0,
            maximum=0xFFFFFFFF,
        )

        _require_exact_int(
            column,
            name="source_map.column",
            minimum=0,
            maximum=0xFFFFFFFF,
        )

        if instruction < previous:
            raise BytecodeValidationError(
                "Source-map entries must be sorted."
            )

        output += encode_u32(
            instruction
        )

        output += encode_u32(
            line
        )

        output += encode_u32(
            column
        )

        previous = instruction

    return bytes(output)


# ══════════════════════════════════════════════════════════════════════════════
# METADATA SECTION
# ══════════════════════════════════════════════════════════════════════════════


def encode_metadata(
    module: CompiledModule,
) -> bytes:
    metadata = ABIMetadata(
        module_name=module.name,
        language_version=module.language_version,
        compiler_version=module.compiler_version,
        entry_point=module.entry_point,
    )

    metadata.validate()

    output = bytearray()

    output += encode_string(
        metadata.module_name
    )

    output += encode_string(
        metadata.language_version
    )

    output += encode_string(
        metadata.compiler_version
    )

    output += encode_string(
        metadata.entry_point
    )

    return bytes(output)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════


def build_sections(
    module: CompiledModule,
) -> List[ABISection]:
    module.validate()

    sections = [
        ABISection(
            type=SectionType.METADATA,
            payload=encode_metadata(
                module
            ),
        ),
        ABISection(
            type=SectionType.CONSTANTS,
            payload=encode_constant_pool(
                module.constant_pool
            ),
        ),
        ABISection(
            type=SectionType.MAIN_CODE,
            payload=encode_instruction_stream(
                module.instructions
            ),
        ),
        ABISection(
            type=SectionType.FUNCTIONS,
            payload=encode_functions(
                module.functions,
                module.function_params,
                module.exports,
            ),
        ),
        ABISection(
            type=SectionType.EXPORTS,
            payload=encode_exports(
                module.exports
            ),
        ),
        ABISection(
            type=SectionType.SOURCE_MAP,
            payload=encode_source_map(
                module.source_map
            ),
        ),
    ]

    return sections


# ══════════════════════════════════════════════════════════════════════════════
# ATCB ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def encode_module(
    module: CompiledModule,
) -> bytes:
    """
    Encode a complete CompiledModule into the normative ATCB ABI.

    Header:

        magic
        ABI major
        ABI minor
        flags
        reserved
        section count
        total payload length
        header checksum

    The checksum is currently defined as zero.

    A future ABI revision may assign checksum semantics to this field,
    but ABI 1.0 requires it to be zero.
    """

    module.validate()

    if module.bytecode_version != BYTECODE_VERSION:
        raise BytecodeValidationError(
            "Module bytecode version does not match ABI."
        )

    sections = build_sections(
        module
    )

    encoded_sections = b"".join(
        section.encode()
        for section in sections
    )

    total_payload_length = len(
        encoded_sections
    )

    if total_payload_length > 0xFFFFFFFF:
        raise BytecodeFormatError(
            "ATCB payload exceeds u32 size."
        )

    header = _HEADER_STRUCT.pack(
        ABI_MAGIC,
        ABI_VERSION_MAJOR,
        ABI_VERSION_MINOR,
        HEADER_FLAGS_NONE,
        0,
        len(sections),
        total_payload_length,
        0,
    )

    return header + encoded_sections


# ══════════════════════════════════════════════════════════════════════════════
# DECODER PRIMITIVES
# ══════════════════════════════════════════════════════════════════════════════


def _require_available(
    data: bytes,
    offset: int,
    length: int,
) -> None:
    if type(data) is not bytes:
        raise BytecodeFormatError(
            "ABI input must be bytes."
        )

    if offset < 0:
        raise BytecodeFormatError(
            "Negative decode offset."
        )

    if length < 0:
        raise BytecodeFormatError(
            "Negative decode length."
        )

    if offset + length > len(data):
        raise BytecodeFormatError(
            "Unexpected end of ATCB payload."
        )


def decode_header(
    data: bytes,
) -> Dict[str, Any]:
    if type(data) is not bytes:
        raise BytecodeFormatError(
            "ATCB input must be bytes."
        )

    if len(data) < HEADER_SIZE:
        raise BytecodeFormatError(
            "ATCB data is smaller than ABI header."
        )

    (
        magic,
        major,
        minor,
        flags,
        reserved,
        section_count,
        payload_length,
        checksum,
    ) = _HEADER_STRUCT.unpack(
        data[:HEADER_SIZE]
    )

    if magic != ABI_MAGIC:
        raise BytecodeFormatError(
            f"Invalid ATCB magic: {magic!r}"
        )

    if (
        major,
        minor,
    ) != ABI_VERSION:
        raise BytecodeFormatError(
            "Unsupported ATCB ABI version: "
            f"{major}.{minor}"
        )

    if flags != HEADER_FLAGS_NONE:
        raise BytecodeFormatError(
            f"Unsupported ATCB flags: {flags:#x}"
        )

    if reserved != 0:
        raise BytecodeFormatError(
            "Reserved ATCB header byte must be zero."
        )

    if checksum != 0:
        raise BytecodeFormatError(
            "ABI 1.0 requires header checksum to be zero."
        )

    actual_payload_length = len(
        data
    ) - HEADER_SIZE

    if payload_length != actual_payload_length:
        raise BytecodeFormatError(
            "ATCB payload length mismatch."
        )

    return {
        "magic": magic,
        "abi_version": (
            major,
            minor,
        ),
        "flags": flags,
        "section_count": section_count,
        "payload_length": payload_length,
        "checksum": checksum,
    }


def decode_sections(
    data: bytes,
) -> List[ABISection]:
    header = decode_header(
        data
    )

    offset = HEADER_SIZE
    sections: List[ABISection] = []

    for _ in range(
        header["section_count"]
    ):
        _require_available(
            data,
            offset,
            SECTION_HEADER_SIZE,
        )

        (
            section_id,
            length,
        ) = _SECTION_HEADER_STRUCT.unpack(
            data[
                offset:
                offset + SECTION_HEADER_SIZE
            ]
        )

        offset += SECTION_HEADER_SIZE

        _require_available(
            data,
            offset,
            length,
        )

        try:
            section_type = SectionType(
                section_id
            )
        except ValueError as exc:
            raise BytecodeFormatError(
                f"Unknown ATCB section type: "
                f"{section_id}"
            ) from exc

        payload = data[
            offset:
            offset + length
        ]

        offset += length

        sections.append(
            ABISection(
                type=section_type,
                payload=payload,
            )
        )

    if offset != len(data):
        raise BytecodeFormatError(
            "Trailing bytes after ATCB sections."
        )

    _validate_section_order(
        sections
    )

    return sections


def _validate_section_order(
    sections: Sequence[ABISection],
) -> None:
    expected = [
        SectionType.METADATA,
        SectionType.CONSTANTS,
        SectionType.MAIN_CODE,
        SectionType.FUNCTIONS,
        SectionType.EXPORTS,
        SectionType.SOURCE_MAP,
    ]

    actual = [
        section.type
        for section in sections
    ]

    if actual != expected:
        raise BytecodeFormatError(
            "Invalid ATCB section order: "
            f"{actual!r}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# MODULE VALIDATION
# ══════════════════════════════════════════════════════════════════════════════


def validate_binary(
    data: bytes,
) -> None:
    """
    Validate an ATCB binary without executing it.
    """

    sections = decode_sections(
        data
    )

    if len(sections) != 6:
        raise BytecodeFormatError(
            "ATCB ABI 1.0 requires exactly six sections."
        )

    for section in sections:
        if type(section.payload) is not bytes:
            raise BytecodeFormatError(
                "Section payload must be bytes."
            )


# ══════════════════════════════════════════════════════════════════════════════
# FILE I/O
# ══════════════════════════════════════════════════════════════════════════════


def write_abi(
    module: CompiledModule,
    path: str,
) -> None:
    data = encode_module(
        module
    )

    with open(
        path,
        "wb",
    ) as handle:
        handle.write(
            data
        )


def read_abi(
    path: str,
) -> bytes:
    with open(
        path,
        "rb",
    ) as handle:
        data = handle.read()

    validate_binary(
        data
    )

    return data


# ══════════════════════════════════════════════════════════════════════════════
# ABI INFORMATION
# ══════════════════════════════════════════════════════════════════════════════


def abi_info() -> Dict[str, Any]:
    """
    Return machine-readable ABI information.
    """

    return {
        "name": "ATCLang Bytecode ABI",
        "version": list(
            ABI_VERSION
        ),
        "magic": ABI_MAGIC.decode(
            "ascii"
        ),
        "endianness": "big",
        "header_size": HEADER_SIZE,
        "section_header_size": SECTION_HEADER_SIZE,
        "sections": {
            section.name: int(section)
            for section in SectionType
        },
        "constant_types": {
            constant.name: int(constant)
            for constant in ABIConstantType
        },
        "operand_types": {
            operand.name: int(operand)
            for operand in OperandType
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════


__all__ = [
    # ABI version
    "ABI_MAGIC",
    "ABI_VERSION_MAJOR",
    "ABI_VERSION_MINOR",
    "ABI_VERSION",

    # Header
    "HEADER_SIZE",
    "HEADER_FLAGS_NONE",

    # Sections
    "SectionType",
    "SECTION_HEADER_SIZE",
    "ABISection",

    # Metadata
    "ABIMetadata",

    # Constants
    "ABIConstantType",
    "encode_constant",
    "encode_constant_pool",

    # Operands
    "OperandType",
    "encode_operand",

    # Instructions
    "opcode_value",
    "encode_instruction",
    "encode_instruction_stream",

    # Functions
    "encode_function",
    "encode_functions",

    # Source map
    "encode_source_map",

    # Primitive encoding
    "encode_u8",
    "decode_u8",
    "encode_u16",
    "decode_u16",
    "encode_u32",
    "decode_u32",
    "encode_u64",
    "decode_u64",
    "encode_i64",
    "decode_i64",
    "encode_f64",
    "decode_f64",
    "encode_string",
    "decode_string",
    "encode_bytes",
    "decode_bytes",

    # Module ABI
    "build_sections",
    "encode_metadata",
    "encode_module",

    # Validation / decoding
    "decode_header",
    "decode_sections",
    "validate_binary",

    # File I/O
    "write_abi",
    "read_abi",

    # ABI information
    "abi_info",
]