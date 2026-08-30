# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Bytecode ABI v1.0
=========================

Normative Binary Application Binary Interface für ATCLang / ATC-92.

Dieses Modul definiert die kanonische Binary-Repräsentation des
ATCLang-Bytecodes.

Architecture
------------

Source
  -> Lexer
  -> Parser
  -> AST
  -> TypeChecker
  -> Compiler
  -> ConstantPool
  -> BytecodeBuilder
  -> CompiledModule
  -> bytecode_abi.py
  -> ATCB Binary
  -> ATC VM

Dependency Boundary
-------------------

Dieses Modul darf ausschließlich von den Bytecode-/Constant-Pool-Schichten
abhängen.

Erlaubte Abhängigkeiten:

    bytecode.py
    constants.py
    errors.py

Nicht erlaubt:

    Parser
    AST
    Compiler
    VM
    Runtime
    Optimizer

ABI Properties
--------------

* Big-endian für alle Mehrbyte-Zahlen.
* Keine Host-Endianness.
* Explizite Feldgrößen.
* Keine Python-Objektgrößen.
* Deterministische Binary-Ausgabe.
* Keine implizite Padding-/Alignment-Abhängigkeit.
* ABI 1.0 akzeptiert ausschließlich exakt definierte Werte.
* Reserved-Felder müssen Null sein.
* Nicht unterstützte Flags müssen abgelehnt werden.

ATCB Container
--------------

Header:

    4 bytes  magic
    1 byte   ABI major
    1 byte   ABI minor
    1 byte   flags
    1 byte   reserved
    4 bytes  section count
    4 bytes  payload length
    4 bytes  header checksum

Header size:

    20 bytes

ABI 1.0 definiert derzeit:

    flags    = 0
    reserved = 0
    checksum = 0

Section Layout
--------------

Die sechs Sections müssen exakt in dieser Reihenfolge erscheinen:

    1. METADATA
    2. CONSTANTS
    3. MAIN_CODE
    4. FUNCTIONS
    5. EXPORTS
    6. SOURCE_MAP

Jede Section:

    4 bytes  section type
    4 bytes  payload length
    N bytes  payload

Alle Section-IDs und Payload-Längen sind explizit.

Integer Encoding
----------------

    u8
    u16
    u32
    u64
    i64

Floating Point
--------------

    IEEE-754 binary64 / f64
    Big-endian

Nicht-finite Werte sind nicht Bestandteil des ABI.

Strings
-------

UTF-8 mit expliziter u32 Byte-Länge.

Bytes
-----

Explizite u32 Byte-Länge.

Determinism
-----------

Die ABI-Ausgabe darf nicht von:

    * Dictionary-Zufallsordnung
    * Host-Endianness
    * Python object layout
    * Alignment
    * Pointer-Werten
    * Memory addresses

abhängen.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import math
import struct
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .bytecode import (
    BYTECODE_MAGIC,
    BYTECODE_VERSION,
    BytecodeFormatError,
    BytecodeValidationError,
    CompiledModule,
    FunctionBytecode,
    Instruction,
)
from .constants import Constant, ConstantPool


# ============================================================================
# ABI VERSION
# ============================================================================

ABI_MAGIC = BYTECODE_MAGIC

ABI_VERSION_MAJOR = 1
ABI_VERSION_MINOR = 0

ABI_VERSION: Tuple[int, int] = (
    ABI_VERSION_MAJOR,
    ABI_VERSION_MINOR,
)


# ============================================================================
# HEADER
# ============================================================================

HEADER_SIZE = 20

HEADER_FLAGS_NONE = 0
HEADER_RESERVED_NONE = 0
HEADER_CHECKSUM_NONE = 0

_HEADER_STRUCT = struct.Struct(">4sBBBBIII")


# ============================================================================
# SECTION TYPES
# ============================================================================


class SectionType(IntEnum):
    """
    Normative ATCB section identifiers.
    """

    METADATA = 0x00000001
    CONSTANTS = 0x00000002
    MAIN_CODE = 0x00000003
    FUNCTIONS = 0x00000004
    EXPORTS = 0x00000005
    SOURCE_MAP = 0x00000006


SECTION_HEADER_SIZE = 8

_SECTION_HEADER_STRUCT = struct.Struct(">II")

EXPECTED_SECTION_ORDER: Tuple[SectionType, ...] = (
    SectionType.METADATA,
    SectionType.CONSTANTS,
    SectionType.MAIN_CODE,
    SectionType.FUNCTIONS,
    SectionType.EXPORTS,
    SectionType.SOURCE_MAP,
)


# ============================================================================
# CONSTANT TYPES
# ============================================================================


class ABIConstantType(IntEnum):
    """
    Normative constant record identifiers.

    These values are independent from the Python ConstantType enum.
    """

    NULL = 0x01
    BOOL = 0x02
    INT = 0x03
    FLOAT = 0x04
    STRING = 0x05
    BYTES = 0x06


# ============================================================================
# OPERAND TYPES
# ============================================================================


class OperandType(IntEnum):
    """
    Normative instruction operand identifiers.
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


# ============================================================================
# METADATA
# ============================================================================


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
        _require_string(self.module_name, "module_name")
        _require_string(self.language_version, "language_version")
        _require_string(self.compiler_version, "compiler_version")
        _require_string(self.entry_point, "entry_point")


# ============================================================================
# SECTION
# ============================================================================


@dataclass(frozen=True, slots=True)
class ABISection:
    """
    Complete ATCB section.
    """

    type: SectionType
    payload: bytes

    def __post_init__(self) -> None:
        if not isinstance(self.type, SectionType):
            raise BytecodeValidationError(
                "ABISection.type must be SectionType."
            )

        _require_bytes(self.payload, "section.payload")

        if len(self.payload) > 0xFFFFFFFF:
            raise BytecodeValidationError(
                "Section payload exceeds u32 size."
            )

    def encode(self) -> bytes:
        return (
            _SECTION_HEADER_STRUCT.pack(
                int(self.type),
                len(self.payload),
            )
            + self.payload
        )


# ============================================================================
# VALIDATION HELPERS
# ============================================================================


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


def _require_available(
    data: bytes,
    offset: int,
    length: int,
) -> None:
    _require_bytes(data, "data")

    if type(offset) is not int:
        raise BytecodeFormatError(
            "Decode offset must be an integer."
        )

    if type(length) is not int:
        raise BytecodeFormatError(
            "Decode length must be an integer."
        )

    if offset < 0:
        raise BytecodeFormatError(
            "Negative decode offset."
        )

    if length < 0:
        raise BytecodeFormatError(
            "Negative decode length."
        )

    end = offset + length

    if end < offset:
        raise BytecodeFormatError(
            "Decode offset overflow."
        )

    if end > len(data):
        raise BytecodeFormatError(
            "Unexpected end of ATCB payload."
        )


# ============================================================================
# INTEGER ENCODING
# ============================================================================


def encode_u8(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u8",
        minimum=0,
        maximum=0xFF,
    )

    return struct.pack(">B", value)


def decode_u8(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(data, offset, 1)

    return data[offset], offset + 1


def encode_u16(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u16",
        minimum=0,
        maximum=0xFFFF,
    )

    return struct.pack(">H", value)


def decode_u16(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(data, offset, 2)

    return (
        struct.unpack(">H", data[offset:offset + 2])[0],
        offset + 2,
    )


def encode_u32(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u32",
        minimum=0,
        maximum=0xFFFFFFFF,
    )

    return struct.pack(">I", value)


def decode_u32(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(data, offset, 4)

    return (
        struct.unpack(">I", data[offset:offset + 4])[0],
        offset + 4,
    )


def encode_u64(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u64",
        minimum=0,
        maximum=0xFFFFFFFFFFFFFFFF,
    )

    return struct.pack(">Q", value)


def decode_u64(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(data, offset, 8)

    return (
        struct.unpack(">Q", data[offset:offset + 8])[0],
        offset + 8,
    )


def encode_i64(value: int) -> bytes:
    _require_exact_int(
        value,
        name="i64",
        minimum=-(1 << 63),
        maximum=(1 << 63) - 1,
    )

    return struct.pack(">q", value)


def decode_i64(
    data: bytes,
    offset: int = 0,
) -> Tuple[int, int]:
    _require_available(data, offset, 8)

    return (
        struct.unpack(">q", data[offset:offset + 8])[0],
        offset + 8,
    )


# ============================================================================
# FLOAT ENCODING
# ============================================================================


def encode_f64(value: float) -> bytes:
    if type(value) is not float:
        raise BytecodeValidationError(
            "f64 value must be a float."
        )

    if not math.isfinite(value):
        raise BytecodeValidationError(
            "Non-finite floating-point values are forbidden."
        )

    return struct.pack(">d", value)


def decode_f64(
    data: bytes,
    offset: int = 0,
) -> Tuple[float, int]:
    _require_available(data, offset, 8)

    value = struct.unpack(
        ">d",
        data[offset:offset + 8],
    )[0]

    if not math.isfinite(value):
        raise BytecodeFormatError(
            "Non-finite f64 value in ATCB binary."
        )

    return value, offset + 8


# ============================================================================
# BYTES / STRING
# ============================================================================


def encode_bytes(value: bytes) -> bytes:
    _require_bytes(value, "bytes")

    if len(value) > 0xFFFFFFFF:
        raise BytecodeValidationError(
            "Byte sequence exceeds u32 size."
        )

    return encode_u32(len(value)) + value


def decode_bytes(
    data: bytes,
    offset: int = 0,
) -> Tuple[bytes, int]:
    length, offset = decode_u32(data, offset)

    _require_available(
        data,
        offset,
        length,
    )

    end = offset + length

    return data[offset:end], end


def encode_string(value: str) -> bytes:
    _require_string(value, "string")

    try:
        encoded = value.encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeEncodeError as exc:
        raise BytecodeValidationError(
            "String cannot be encoded as UTF-8."
        ) from exc

    return encode_bytes(encoded)


def decode_string(
    data: bytes,
    offset: int = 0,
) -> Tuple[str, int]:
    raw, offset = decode_bytes(data, offset)

    try:
        value = raw.decode(
            "utf-8",
            errors="strict",
        )
    except UnicodeDecodeError as exc:
        raise BytecodeFormatError(
            "Invalid UTF-8 string in ATCB binary."
        ) from exc

    return value, offset


# ============================================================================
# CONSTANT TYPE
# ============================================================================


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


# ============================================================================
# CONSTANT ENCODING
# ============================================================================


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

        return encode_u8(1 if value else 0)

    if constant_type is ABIConstantType.INT:
        return encode_i64(value)

    if constant_type is ABIConstantType.FLOAT:
        return encode_f64(value)

    if constant_type is ABIConstantType.STRING:
        return encode_string(value)

    if constant_type is ABIConstantType.BYTES:
        return encode_bytes(value)

    raise BytecodeValidationError(
        f"Unsupported constant type: {constant_type!r}"
    )


def encode_constant(
    constant: Constant,
) -> bytes:
    """
    Encode one constant.

    Layout:

        u32 index
        u8  type
        type-specific payload
    """

    if not isinstance(constant, Constant):
        raise BytecodeValidationError(
            "Expected Constant."
        )

    _require_exact_int(
        constant.index,
        name="constant.index",
        minimum=0,
        maximum=0xFFFFFFFF,
    )

    constant_type = _constant_type(constant)

    payload = _encode_constant_payload(
        constant_type,
        constant.value,
    )

    return (
        encode_u32(constant.index)
        + encode_u8(int(constant_type))
        + payload
    )


def encode_constant_pool(
    pool: ConstantPool,
) -> bytes:
    """
    Constant pool:

        u32 count
        repeated constant records
    """

    if not isinstance(pool, ConstantPool):
        raise BytecodeValidationError(
            "Expected ConstantPool."
        )

    constants = list(pool)

    if len(constants) > 0xFFFFFFFF:
        raise BytecodeValidationError(
            "Constant pool exceeds u32 count."
        )

    output = bytearray()

    output += encode_u32(len(constants))

    expected_index = 0

    for constant in constants:
        if constant.index != expected_index:
            raise BytecodeValidationError(
                "Constant pool indices must be contiguous and "
                f"deterministic: expected {expected_index}, "
                f"got {constant.index}."
            )

        output += encode_constant(constant)
        expected_index += 1

    return bytes(output)


# ============================================================================
# OPERANDS
# ============================================================================


def _infer_operand_type(
    value: Any,
) -> OperandType:
    if isinstance(value, Constant):
        return OperandType.CONSTANT_INDEX

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

    raise BytecodeValidationError(
        "Unsupported instruction operand type: "
        f"{type(value).__name__}"
    )


def _encode_operand_payload(
    operand_type: OperandType,
    value: Any,
) -> bytes:
    if operand_type is OperandType.NULL:
        if value is not None:
            raise BytecodeValidationError(
                "NULL operand requires None."
            )

        return b""

    if operand_type is OperandType.BOOL:
        if type(value) is not bool:
            raise BytecodeValidationError(
                "BOOL operand requires bool."
            )

        return encode_u8(1 if value else 0)

    if operand_type is OperandType.INT:
        return encode_i64(value)

    if operand_type is OperandType.UINT:
        return encode_u64(value)

    if operand_type is OperandType.FLOAT:
        return encode_f64(value)

    if operand_type is OperandType.STRING:
        return encode_string(value)

    if operand_type is OperandType.BYTES:
        return encode_bytes(value)

    if operand_type is OperandType.CONSTANT_INDEX:
        if not isinstance(value, Constant):
            raise BytecodeValidationError(
                "CONSTANT_INDEX operand requires Constant."
            )

        return encode_u32(value.index)

    raise BytecodeValidationError(
        f"Unsupported operand type: {operand_type!r}"
    )


def encode_operand(
    value: Any,
) -> bytes:
    operand_type = _infer_operand_type(value)

    payload = _encode_operand_payload(
        operand_type,
        value,
    )

    return (
        encode_u8(int(operand_type))
        + encode_u32(len(payload))
        + payload
    )


# ============================================================================
# OPCODE
# ============================================================================


def opcode_value(op: Any) -> int:
    """
    Convert an opcode to its normative u8 representation.
    """

    if isinstance(op, IntEnum):
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


# ============================================================================
# INSTRUCTION ENCODING
# ============================================================================


def encode_instruction(
    instruction: Instruction,
) -> bytes:
    """
    Instruction:

        u8 opcode
        u8 operand_count
        operands...
    """

    if not isinstance(instruction, Instruction):
        raise BytecodeValidationError(
            "Expected Instruction."
        )

    opcode = opcode_value(instruction.op)

    operand_count = len(instruction.args)

    if operand_count > 0xFF:
        raise BytecodeValidationError(
            "Instruction has more than 255 operands."
        )

    output = bytearray()

    output += encode_u8(opcode)
    output += encode_u8(operand_count)

    for argument in instruction.args:
        output += encode_operand(argument)

    return bytes(output)


def encode_instruction_stream(
    instructions: Sequence[Instruction],
) -> bytes:
    if len(instructions) > 0xFFFFFFFF:
        raise BytecodeValidationError(
            "Instruction stream exceeds u32 instruction count."
        )

    output = bytearray()

    output += encode_u32(len(instructions))

    for instruction in instructions:
        encoded = encode_instruction(instruction)

        if len(encoded) > 0xFFFFFFFF:
            raise BytecodeFormatError(
                "Encoded instruction exceeds u32 size."
            )

        output += encode_u32(len(encoded))
        output += encoded

    return bytes(output)


# ============================================================================
# FUNCTION ENCODING
# ============================================================================


def encode_function(
    function: FunctionBytecode,
) -> bytes:
    """
    Function record:

        string name
        u32 parameter count
        string parameters...
        u8 export flag
        u32 instruction stream length
        instruction stream
    """

    function.validate()

    output = bytearray()

    output += encode_string(function.name)

    if len(function.parameters) > 0xFFFFFFFF:
        raise BytecodeValidationError(
            "Function parameter count exceeds u32."
        )

    output += encode_u32(len(function.parameters))

    for parameter in function.parameters:
        output += encode_string(parameter)

    if type(function.exports) is not bool:
        raise BytecodeValidationError(
            "Function export flag must be bool."
        )

    output += encode_u8(
        1 if function.exports else 0
    )

    instructions = encode_instruction_stream(
        function.instructions
    )

    output += encode_u32(len(instructions))
    output += instructions

    return bytes(output)


def encode_functions(
    functions: Mapping[str, Sequence[Instruction]],
    function_params: Mapping[str, Sequence[str]],
    exports: Sequence[str],
) -> bytes:
    """
    Functions are sorted lexicographically by their canonical UTF-8
    function name.

    This guarantees deterministic output independent of mapping insertion
    order.
    """

    names = list(functions.keys())

    for name in names:
        _require_string(name, "function name")

    names.sort(
        key=lambda value: value.encode("utf-8")
    )

    if len(names) > 0xFFFFFFFF:
        raise BytecodeValidationError(
            "Function count exceeds u32."
        )

    export_set = set(exports)

    output = bytearray()
    output += encode_u32(len(names))

    for name in names:
        function = FunctionBytecode(
            name=name,
            instructions=list(functions[name]),
            parameters=list(
                function_params.get(name, [])
            ),
            exports=name in export_set,
        )

        output += encode_function(function)

    return bytes(output)


# ============================================================================
# EXPORTS
# ============================================================================


def encode_exports(
    exports: Sequence[str],
) -> bytes:
    """
    Exports are encoded in canonical UTF-8 byte ordering.
    """

    normalized = list(exports)

    for export in normalized:
        _require_string(export, "export")

    normalized.sort(
        key=lambda value: value.encode("utf-8")
    )

    if len(normalized) > 0xFFFFFFFF:
        raise BytecodeValidationError(
            "Export count exceeds u32."
        )

    for index in range(1, len(normalized)):
        if normalized[index] == normalized[index - 1]:
            raise BytecodeValidationError(
                f"Duplicate export: {normalized[index]!r}"
            )

    output = bytearray()
    output += encode_u32(len(normalized))

    for export in normalized:
        output += encode_string(export)

    return bytes(output)


# ============================================================================
# SOURCE MAP
# ============================================================================


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

    entries = list(source_map)

    if len(entries) > 0xFFFFFFFF:
        raise BytecodeValidationError(
            "Source-map entry count exceeds u32."
        )

    output = bytearray()

    output += encode_u32(1)
    output += encode_u32(len(entries))

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
                "Source-map entries must be sorted by instruction."
            )

        output += encode_u32(instruction)
        output += encode_u32(line)
        output += encode_u32(column)

        previous = instruction

    return bytes(output)


# ============================================================================
# METADATA
# ============================================================================


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

    output += encode_string(metadata.module_name)
    output += encode_string(metadata.language_version)
    output += encode_string(metadata.compiler_version)
    output += encode_string(metadata.entry_point)

    return bytes(output)


# ============================================================================
# SECTION CONSTRUCTION
# ============================================================================


def build_sections(
    module: CompiledModule,
) -> List[ABISection]:
    module.validate()

    sections = [
        ABISection(
            type=SectionType.METADATA,
            payload=encode_metadata(module),
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

    actual = tuple(
        section.type
        for section in sections
    )

    if actual != EXPECTED_SECTION_ORDER:
        raise BytecodeValidationError(
            "Internal ABI section construction violation."
        )

    return sections


# ============================================================================
# MODULE ENCODING
# ============================================================================


def encode_module(
    module: CompiledModule,
) -> bytes:
    """
    Encode a CompiledModule into canonical ATCB ABI 1.0.
    """

    module.validate()

    if module.bytecode_version != BYTECODE_VERSION:
        raise BytecodeValidationError(
            "Module bytecode version does not match ABI."
        )

    sections = build_sections(module)

    encoded_sections = b"".join(
        section.encode()
        for section in sections
    )

    payload_length = len(encoded_sections)

    if payload_length > 0xFFFFFFFF:
        raise BytecodeFormatError(
            "ATCB payload exceeds u32 size."
        )

    section_count = len(sections)

    if section_count > 0xFFFFFFFF:
        raise BytecodeFormatError(
            "ATCB section count exceeds u32."
        )

    header = _HEADER_STRUCT.pack(
        ABI_MAGIC,
        ABI_VERSION_MAJOR,
        ABI_VERSION_MINOR,
        HEADER_FLAGS_NONE,
        HEADER_RESERVED_NONE,
        section_count,
        payload_length,
        HEADER_CHECKSUM_NONE,
    )

    return header + encoded_sections


# ============================================================================
# HEADER DECODING
# ============================================================================


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

    if major != ABI_VERSION_MAJOR:
        raise BytecodeFormatError(
            "Unsupported ATCB ABI major version: "
            f"{major}"
        )

    if minor != ABI_VERSION_MINOR:
        raise BytecodeFormatError(
            "Unsupported ATCB ABI minor version: "
            f"{major}.{minor}"
        )

    if flags != HEADER_FLAGS_NONE:
        raise BytecodeFormatError(
            f"Unsupported ATCB flags: {flags:#x}"
        )

    if reserved != HEADER_RESERVED_NONE:
        raise BytecodeFormatError(
            "Reserved ATCB header byte must be zero."
        )

    if checksum != HEADER_CHECKSUM_NONE:
        raise BytecodeFormatError(
            "ABI 1.0 requires header checksum to be zero."
        )

    actual_payload_length = len(data) - HEADER_SIZE

    if payload_length != actual_payload_length:
        raise BytecodeFormatError(
            "ATCB payload length mismatch: "
            f"declared={payload_length}, "
            f"actual={actual_payload_length}."
        )

    if section_count != len(EXPECTED_SECTION_ORDER):
        raise BytecodeFormatError(
            "ABI 1.0 requires exactly six sections."
        )

    return {
        "magic": magic,
        "abi_version": (major, minor),
        "flags": flags,
        "reserved": reserved,
        "section_count": section_count,
        "payload_length": payload_length,
        "checksum": checksum,
    }


# ============================================================================
# SECTION DECODING
# ============================================================================


def decode_sections(
    data: bytes,
) -> List[ABISection]:
    header = decode_header(data)

    offset = HEADER_SIZE
    sections: List[ABISection] = []

    for index in range(header["section_count"]):
        _require_available(
            data,
            offset,
            SECTION_HEADER_SIZE,
        )

        section_id, length = _SECTION_HEADER_STRUCT.unpack(
            data[
                offset:
                offset + SECTION_HEADER_SIZE
            ]
        )

        offset += SECTION_HEADER_SIZE

        try:
            section_type = SectionType(section_id)
        except ValueError as exc:
            raise BytecodeFormatError(
                f"Unknown ATCB section type: {section_id:#x}"
            ) from exc

        expected_type = EXPECTED_SECTION_ORDER[index]

        if section_type is not expected_type:
            raise BytecodeFormatError(
                "Invalid ATCB section order: "
                f"expected {expected_type.name}, "
                f"got {section_type.name}."
            )

        _require_available(
            data,
            offset,
            length,
        )

        end = offset + length

        payload = data[offset:end]

        sections.append(
            ABISection(
                type=section_type,
                payload=payload,
            )
        )

        offset = end

    if offset != len(data):
        raise BytecodeFormatError(
            "Trailing bytes after ATCB sections."
        )

    return sections


# ============================================================================
# SECTION PAYLOAD VALIDATION
# ============================================================================


def _validate_metadata_payload(
    payload: bytes,
) -> None:
    offset = 0

    _, offset = decode_string(payload, offset)
    _, offset = decode_string(payload, offset)
    _, offset = decode_string(payload, offset)
    _, offset = decode_string(payload, offset)

    if offset != len(payload):
        raise BytecodeFormatError(
            "Trailing bytes in METADATA section."
        )


def _validate_constant_pool_payload(
    payload: bytes,
) -> None:
    offset = 0

    count, offset = decode_u32(payload, offset)

    previous_index = -1

    for _ in range(count):
        index, offset = decode_u32(payload, offset)

        if index != previous_index + 1:
            raise BytecodeFormatError(
                "Constant indices must be contiguous."
            )

        previous_index = index

        type_id, offset = decode_u8(payload, offset)

        try:
            constant_type = ABIConstantType(type_id)
        except ValueError as exc:
            raise BytecodeFormatError(
                f"Unknown constant type: {type_id:#x}"
            ) from exc

        if constant_type is ABIConstantType.NULL:
            pass

        elif constant_type is ABIConstantType.BOOL:
            value, offset = decode_u8(payload, offset)

            if value not in (0, 1):
                raise BytecodeFormatError(
                    "BOOL constant must be encoded as 0 or 1."
                )

        elif constant_type is ABIConstantType.INT:
            _, offset = decode_i64(payload, offset)

        elif constant_type is ABIConstantType.FLOAT:
            _, offset = decode_f64(payload, offset)

        elif constant_type is ABIConstantType.STRING:
            _, offset = decode_string(payload, offset)

        elif constant_type is ABIConstantType.BYTES:
            _, offset = decode_bytes(payload, offset)

    if offset != len(payload):
        raise BytecodeFormatError(
            "Trailing bytes in CONSTANTS section."
        )


def _validate_operand(
    payload: bytes,
) -> None:
    if len(payload) < OPERAND_HEADER_SIZE:
        raise BytecodeFormatError(
            "Operand is smaller than operand header."
        )

    type_id = payload[0]

    length = struct.unpack(
        ">I",
        payload[1:5],
    )[0]

    if length != len(payload) - OPERAND_HEADER_SIZE:
        raise BytecodeFormatError(
            "Operand payload length mismatch."
        )

    try:
        operand_type = OperandType(type_id)
    except ValueError as exc:
        raise BytecodeFormatError(
            f"Unknown operand type: {type_id:#x}"
        ) from exc

    body = payload[OPERAND_HEADER_SIZE:]

    if operand_type is OperandType.NULL:
        if body:
            raise BytecodeFormatError(
                "NULL operand must have empty payload."
            )

    elif operand_type is OperandType.BOOL:
        if len(body) != 1:
            raise BytecodeFormatError(
                "BOOL operand requires exactly one byte."
            )

        if body[0] not in (0, 1):
            raise BytecodeFormatError(
                "BOOL operand must be encoded as 0 or 1."
            )

    elif operand_type is OperandType.UINT:
        if len(body) != 8:
            raise BytecodeFormatError(
                "UINT operand requires 8 bytes."
            )

    elif operand_type is OperandType.INT:
        if len(body) != 8:
            raise BytecodeFormatError(
                "INT operand requires 8 bytes."
            )

    elif operand_type is OperandType.FLOAT:
        if len(body) != 8:
            raise BytecodeFormatError(
                "FLOAT operand requires 8 bytes."
            )

        decode_f64(body)

    elif operand_type is OperandType.STRING:
        _, end = decode_string(body)

        if end != len(body):
            raise BytecodeFormatError(
                "Invalid STRING operand payload."
            )

    elif operand_type is OperandType.BYTES:
        _, end = decode_bytes(body)

        if end != len(body):
            raise BytecodeFormatError(
                "Invalid BYTES operand payload."
            )

    elif operand_type is OperandType.CONSTANT_INDEX:
        if len(body) != 4:
            raise BytecodeFormatError(
                "CONSTANT_INDEX operand requires 4 bytes."
            )


def _validate_instruction(
    payload: bytes,
) -> None:
    if len(payload) < 2:
        raise BytecodeFormatError(
            "Instruction is smaller than instruction header."
        )

    opcode = payload[0]
    operand_count = payload[1]

    _require_exact_int(
        opcode,
        name="opcode",
        minimum=0,
        maximum=0xFF,
    )

    offset = 2

    for _ in range(operand_count):
        _require_available(
            payload,
            offset,
            OPERAND_HEADER_SIZE,
        )

        operand_length = struct.unpack(
            ">I",
            payload[offset + 1:offset + 5],
        )[0]

        total_operand_length = (
            OPERAND_HEADER_SIZE
            + operand_length
        )

        _require_available(
            payload,
            offset,
            total_operand_length,
        )

        operand_end = offset + total_operand_length

        _validate_operand(
            payload[offset:operand_end]
        )

        offset = operand_end

    if offset != len(payload):
        raise BytecodeFormatError(
            "Instruction contains trailing bytes."
        )


def _validate_instruction_stream_payload(
    payload: bytes,
) -> None:
    offset = 0

    count, offset = decode_u32(payload, offset)

    for _ in range(count):
        length, offset = decode_u32(payload, offset)

        _require_available(
            payload,
            offset,
            length,
        )

        end = offset + length

        _validate_instruction(
            payload[offset:end]
        )

        offset = end

    if offset != len(payload):
        raise BytecodeFormatError(
            "Trailing bytes in instruction stream."
        )


def _validate_functions_payload(
    payload: bytes,
) -> None:
    offset = 0

    count, offset = decode_u32(payload, offset)

    names: List[bytes] = []

    for _ in range(count):
        name, offset = decode_string(payload, offset)

        names.append(
            name.encode("utf-8")
        )

        parameter_count, offset = decode_u32(
            payload,
            offset,
        )

        for _ in range(parameter_count):
            _, offset = decode_string(
                payload,
                offset,
            )

        export_flag, offset = decode_u8(
            payload,
            offset,
        )

        if export_flag not in (0, 1):
            raise BytecodeFormatError(
                "Function export flag must be 0 or 1."
            )

        instruction_length, offset = decode_u32(
            payload,
            offset,
        )

        _require_available(
            payload,
            offset,
            instruction_length,
        )

        end = offset + instruction_length

        _validate_instruction_stream_payload(
            payload[offset:end]
        )

        offset = end

    if names != sorted(names):
        raise BytecodeFormatError(
            "Functions are not in canonical UTF-8 order."
        )

    if len(set(names)) != len(names):
        raise BytecodeFormatError(
            "Duplicate function name in FUNCTIONS section."
        )

    if offset != len(payload):
        raise BytecodeFormatError(
            "Trailing bytes in FUNCTIONS section."
        )


def _validate_exports_payload(
    payload: bytes,
) -> None:
    offset = 0

    count, offset = decode_u32(payload, offset)

    exports: List[bytes] = []

    for _ in range(count):
        value, offset = decode_string(
            payload,
            offset,
        )

        exports.append(
            value.encode("utf-8")
        )

    if exports != sorted(exports):
        raise BytecodeFormatError(
            "Exports are not in canonical UTF-8 order."
        )

    if len(set(exports)) != len(exports):
        raise BytecodeFormatError(
            "Duplicate export."
        )

    if offset != len(payload):
        raise BytecodeFormatError(
            "Trailing bytes in EXPORTS section."
        )


def _validate_source_map_payload(
    payload: bytes,
) -> None:
    offset = 0

    version, offset = decode_u32(
        payload,
        offset,
    )

    if version != 1:
        raise BytecodeFormatError(
            f"Unsupported source-map version: {version}"
        )

    count, offset = decode_u32(
        payload,
        offset,
    )

    previous = -1

    for _ in range(count):
        instruction, offset = decode_u32(
            payload,
            offset,
        )

        _, offset = decode_u32(
            payload,
            offset,
        )

        _, offset = decode_u32(
            payload,
            offset,
        )

        if instruction < previous:
            raise BytecodeFormatError(
                "Source-map entries are not sorted."
            )

        previous = instruction

    if offset != len(payload):
        raise BytecodeFormatError(
            "Trailing bytes in SOURCE_MAP section."
        )


# ============================================================================
# BINARY VALIDATION
# ============================================================================


def validate_binary(
    data: bytes,
) -> None:
    """
    Validate an ATCB binary without executing it.
    """

    sections = decode_sections(data)

    if len(sections) != 6:
        raise BytecodeFormatError(
            "ATCB ABI 1.0 requires exactly six sections."
        )

    validators = {
        SectionType.METADATA: _validate_metadata_payload,
        SectionType.CONSTANTS: _validate_constant_pool_payload,
        SectionType.MAIN_CODE: _validate_instruction_stream_payload,
        SectionType.FUNCTIONS: _validate_functions_payload,
        SectionType.EXPORTS: _validate_exports_payload,
        SectionType.SOURCE_MAP: _validate_source_map_payload,
    }

    for section in sections:
        validator = validators[section.type]
        validator(section.payload)


# ============================================================================
# FILE I/O
# ============================================================================


def write_abi(
    module: CompiledModule,
    path: str,
) -> None:
    data = encode_module(module)

    with open(path, "wb") as handle:
        handle.write(data)


def read_abi(
    path: str,
) -> bytes:
    with open(path, "rb") as handle:
        data = handle.read()

    validate_binary(data)

    return data


# ============================================================================
# ABI INFORMATION
# ============================================================================


def abi_info() -> Dict[str, Any]:
    """
    Return machine-readable ABI information.
    """

    return {
        "name": "ATCLang Bytecode ABI",
        "standard": "ATC-92",
        "version": list(ABI_VERSION),
        "magic": ABI_MAGIC.decode("ascii"),
        "endianness": "big",
        "header_size": HEADER_SIZE,
        "section_header_size": SECTION_HEADER_SIZE,
        "header": {
            "magic_bytes": 4,
            "abi_major": 1,
            "abi_minor": 1,
            "flags": 1,
            "reserved": 1,
            "section_count": 4,
            "payload_length": 4,
            "checksum": 4,
        },
        "sections": {
            section.name: int(section)
            for section in SectionType
        },
        "section_order": [
            section.name
            for section in EXPECTED_SECTION_ORDER
        ],
        "constant_types": {
            constant.name: int(constant)
            for constant in ABIConstantType
        },
        "operand_types": {
            operand.name: int(operand)
            for operand in OperandType
        },
        "float": {
            "format": "IEEE-754 binary64",
            "finite_only": True,
        },
        "strings": {
            "encoding": "UTF-8",
            "length_encoding": "u32",
        },
        "deterministic": True,
    }


# ============================================================================
# PUBLIC API
# ============================================================================


__all__ = [
    # ABI
    "ABI_MAGIC",
    "ABI_VERSION_MAJOR",
    "ABI_VERSION_MINOR",
    "ABI_VERSION",

    # Header
    "HEADER_SIZE",
    "HEADER_FLAGS_NONE",

    # Sections
    "SectionType",
    "EXPECTED_SECTION_ORDER",
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

    # Exports
    "encode_exports",

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

    # Validation
    "decode_header",
    "decode_sections",
    "validate_binary",

    # File I/O
    "write_abi",
    "read_abi",

    # Information
    "abi_info",
]