# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Bytecode ABI v1.0
=========================

Normative Binary Application Binary Interface für ATCLang / ATC-92.

Dieses Modul definiert die kanonische Binärrepräsentation des
ATCLang-Bytecodes.

Pipeline
--------

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

Normative Eigenschaften
-----------------------

* Big-Endian für alle Mehrbyte-Werte.
* Keine Host-Endianness.
* Keine Python-Objektgrößen.
* Explizite Längenfelder.
* Explizite Typkennungen.
* Deterministische Section-Reihenfolge.
* Deterministische Binary-Ausgabe.
* Strikte Bounds-Prüfung.
* Keine implizite Typkonvertierung.
* Keine nicht-finiten Floating-Point-Werte.
* Reserved-Felder müssen Null sein.
* ABI-Major inkompatibel bei Änderung.
* ABI-Minor ist innerhalb derselben Major-Version erweiterbar.

Dependency Boundary
-------------------

Dieses Modul darf ausschließlich von Bytecode-/Constant-Pool-Schichten
abhängen.

Erlaubt:

    bytecode.py
    constants.py
    errors.py

Nicht erlaubt:

    parser
    AST
    compiler
    VM
    runtime
    optimizer
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
)
from .constants import (
    Constant,
    ConstantPool,
)


# ══════════════════════════════════════════════════════════════════════════════
# ABI VERSION
# ══════════════════════════════════════════════════════════════════════════════

ABI_NAME = "ATCLang Bytecode ABI"

ABI_VERSION_MAJOR = 1
ABI_VERSION_MINOR = 0

ABI_VERSION: Tuple[int, int] = (
    ABI_VERSION_MAJOR,
    ABI_VERSION_MINOR,
)

ABI_MAGIC = BYTECODE_MAGIC


# ══════════════════════════════════════════════════════════════════════════════
# LIMITS
# ══════════════════════════════════════════════════════════════════════════════

MAX_U8 = 0xFF
MAX_U16 = 0xFFFF
MAX_U32 = 0xFFFFFFFF
MAX_U64 = 0xFFFFFFFFFFFFFFFF

MAX_I64 = (1 << 63) - 1
MIN_I64 = -(1 << 63)

MAX_SECTION_COUNT = 0xFFFFFFFF

MAX_STRING_BYTES = MAX_U32
MAX_BYTES = MAX_U32
MAX_OPERANDS = MAX_U8


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

HEADER_SIZE = 20

HEADER_FLAGS_NONE = 0
HEADER_RESERVED = 0

_HEADER_STRUCT = struct.Struct(
    ">4sBBBBIII"
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTIONS
# ══════════════════════════════════════════════════════════════════════════════


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

_SECTION_HEADER_STRUCT = struct.Struct(
    ">II"
)


CANONICAL_SECTION_ORDER: Tuple[SectionType, ...] = (
    SectionType.METADATA,
    SectionType.CONSTANTS,
    SectionType.MAIN_CODE,
    SectionType.FUNCTIONS,
    SectionType.EXPORTS,
    SectionType.SOURCE_MAP,
)


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANT TYPES
# ══════════════════════════════════════════════════════════════════════════════


class ABIConstantType(IntEnum):
    """
    Normative ATC-92 constant type identifiers.
    """

    NULL = 0x01
    BOOL = 0x02
    INT = 0x03
    FLOAT = 0x04
    STRING = 0x05
    BYTES = 0x06


# ══════════════════════════════════════════════════════════════════════════════
# OPERAND TYPES
# ══════════════════════════════════════════════════════════════════════════════


class OperandType(IntEnum):
    """
    Normative instruction operand encodings.
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
# SECTION OBJECT
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class ABISection:
    """
    Complete ABI section.

    Layout:

        u32 section_type
        u32 payload_length
        bytes payload
    """

    type: SectionType
    payload: bytes

    def __post_init__(self) -> None:
        if not isinstance(
            self.type,
            SectionType,
        ):
            raise BytecodeValidationError(
                "ABISection.type must be SectionType."
            )

        if type(self.payload) is not bytes:
            raise BytecodeValidationError(
                "ABISection.payload must be bytes."
            )

        if len(self.payload) > MAX_U32:
            raise BytecodeValidationError(
                "ABI section payload exceeds u32."
            )

    def encode(self) -> bytes:
        return (
            _SECTION_HEADER_STRUCT.pack(
                int(self.type),
                len(self.payload),
            )
            + self.payload
        )


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
        raise BytecodeValidationError(
            f"{name} must be bytes."
        )


def _require_available(
    data: bytes,
    offset: int,
    length: int,
) -> None:
    if type(data) is not bytes:
        raise BytecodeFormatError(
            "ABI input must be bytes."
        )

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


# ══════════════════════════════════════════════════════════════════════════════
# INTEGER ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def encode_u8(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u8",
        minimum=0,
        maximum=MAX_U8,
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

    return (
        data[offset],
        offset + 1,
    )


def encode_u16(value: int) -> bytes:
    _require_exact_int(
        value,
        name="u16",
        minimum=0,
        maximum=MAX_U16,
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
        maximum=MAX_U32,
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
        maximum=MAX_U64,
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
        minimum=MIN_I64,
        maximum=MAX_I64,
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
            "f64 value must be an exact float."
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
            "Non-finite f64 value in ATCB."
        )

    return (
        value,
        offset + 8,
    )


# ══════════════════════════════════════════════════════════════════════════════
# BYTES / STRING
# ══════════════════════════════════════════════════════════════════════════════


def encode_bytes(value: bytes) -> bytes:
    _require_bytes(
        value,
        "bytes",
    )

    if len(value) > MAX_U32:
        raise BytecodeValidationError(
            "Byte sequence exceeds u32 length."
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

    try:
        encoded = value.encode(
            "utf-8",
            errors="strict",
        )
    except UnicodeEncodeError as exc:
        raise BytecodeValidationError(
            "String cannot be encoded as UTF-8."
        ) from exc

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
            "Invalid UTF-8 string in ATCB."
        ) from exc

    return (
        value,
        offset,
    )


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

    try:
        return mapping[normalized]
    except KeyError as exc:
        raise BytecodeValidationError(
            f"Unsupported constant type: {value_type!r}"
        ) from exc


def _encode_constant_payload(
    constant_type: ABIConstantType,
    value: Any,
) -> bytes:
    if constant_type is ABIConstantType.NULL:
        if value is not None:
            raise BytecodeValidationError(
                "NULL constant requires None."
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


def encode_constant(
    constant: Constant,
) -> bytes:
    """
    Constant record:

        u32 constant_index
        u8  constant_type
        payload
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
        maximum=MAX_U32,
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


def encode_constant_pool(
    pool: ConstantPool,
) -> bytes:
    """
    Constant pool:

        u32 count
        ConstantRecord[count]
    """

    if not isinstance(
        pool,
        ConstantPool,
    ):
        raise BytecodeValidationError(
            "Expected ConstantPool."
        )

    constants = list(pool)

    if len(constants) > MAX_U32:
        raise BytecodeValidationError(
            "Constant pool exceeds u32 count."
        )

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

    if isinstance(
        value,
        Constant,
    ):
        return OperandType.CONSTANT_INDEX

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
                "CONSTANT_INDEX requires Constant."
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

    if len(payload) > MAX_U32:
        raise BytecodeValidationError(
            "Operand payload exceeds u32."
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
# OPCODE
# ══════════════════════════════════════════════════════════════════════════════


def opcode_value(op: Any) -> int:
    """
    Convert an opcode to the normative u8 representation.
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
            "Opcode must be IntEnum or exact int."
        )

    _require_exact_int(
        value,
        name="opcode",
        minimum=0,
        maximum=MAX_U8,
    )

    return value


# ══════════════════════════════════════════════════════════════════════════════
# INSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════


def encode_instruction(
    instruction: Instruction,
) -> bytes:
    """
    Instruction:

        u8 opcode
        u8 operand_count
        operand[operand_count]
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

    operand_count = len(
        instruction.args
    )

    if operand_count > MAX_OPERANDS:
        raise BytecodeValidationError(
            "Instruction has too many operands."
        )

    output = bytearray()

    output += encode_u8(
        opcode
    )

    output += encode_u8(
        operand_count
    )

    for argument in instruction.args:
        output += encode_operand(
            argument
        )

    return bytes(output)


def encode_instruction_stream(
    instructions: Sequence[Instruction],
) -> bytes:
    """
    Instruction stream:

        u32 instruction_count

        repeated:
            u32 instruction_length
            bytes instruction
    """

    if len(instructions) > MAX_U32:
        raise BytecodeValidationError(
            "Instruction count exceeds u32."
        )

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
    Function:

        string function_name
        u32 parameter_count
        string parameters[parameter_count]
        u8 exported
        u32 instruction_stream_length
        bytes instruction_stream
    """

    function.validate()

    output = bytearray()

    output += encode_string(
        function.name
    )

    if len(function.parameters) > MAX_U32:
        raise BytecodeValidationError(
            "Parameter count exceeds u32."
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

    instruction_stream = encode_instruction_stream(
        function.instructions
    )

    output += encode_u32(
        len(instruction_stream)
    )

    output += instruction_stream

    return bytes(output)


def encode_functions(
    functions: Mapping[str, Sequence[Instruction]],
    function_params: Mapping[str, Sequence[str]],
    exports: Sequence[str],
) -> bytes:
    if len(functions) > MAX_U32:
        raise BytecodeValidationError(
            "Function count exceeds u32."
        )

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
    if len(exports) > MAX_U32:
        raise BytecodeValidationError(
            "Export count exceeds u32."
        )

    output = bytearray()

    output += encode_u32(
        len(exports)
    )

    for export in exports:
        encode_name = encode_string(
            export
        )

        output += encode_name

    return bytes(output)


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE MAP
# ══════════════════════════════════════════════════════════════════════════════


def encode_source_map(
    source_map: Iterable[Sequence[int]],
) -> bytes:
    """
    Source-map v1:

        u32 version
        u32 entry_count

        repeated:

            u32 instruction
            u32 line
            u32 column

    Entries must be monotonically sorted by instruction index.
    """

    entries = list(
        source_map
    )

    if len(entries) > MAX_U32:
        raise BytecodeValidationError(
            "Source-map entry count exceeds u32."
        )

    output = bytearray()

    output += encode_u32(
        1
    )

    output += encode_u32(
        len(entries)
    )

    previous_instruction = -1

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
            maximum=MAX_U32,
        )

        _require_exact_int(
            line,
            name="source_map.line",
            minimum=0,
            maximum=MAX_U32,
        )

        _require_exact_int(
            column,
            name="source_map.column",
            minimum=0,
            maximum=MAX_U32,
        )

        if instruction < previous_instruction:
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

        previous_instruction = instruction

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
# SECTION BUILDING
# ══════════════════════════════════════════════════════════════════════════════


def build_sections(
    module: CompiledModule,
) -> List[ABISection]:
    module.validate()

    return [
        ABISection(
            SectionType.METADATA,
            encode_metadata(module),
        ),
        ABISection(
            SectionType.CONSTANTS,
            encode_constant_pool(
                module.constant_pool
            ),
        ),
        ABISection(
            SectionType.MAIN_CODE,
            encode_instruction_stream(
                module.instructions
            ),
        ),
        ABISection(
            SectionType.FUNCTIONS,
            encode_functions(
                module.functions,
                module.function_params,
                module.exports,
            ),
        ),
        ABISection(
            SectionType.EXPORTS,
            encode_exports(
                module.exports
            ),
        ),
        ABISection(
            SectionType.SOURCE_MAP,
            encode_source_map(
                module.source_map
            ),
        ),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# HEADER ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def _encode_header(
    *,
    section_count: int,
    payload_length: int,
) -> bytes:
    _require_exact_int(
        section_count,
        name="section_count",
        minimum=0,
        maximum=MAX_U32,
    )

    _require_exact_int(
        payload_length,
        name="payload_length",
        minimum=0,
        maximum=MAX_U32,
    )

    return _HEADER_STRUCT.pack(
        ABI_MAGIC,
        ABI_VERSION_MAJOR,
        ABI_VERSION_MINOR,
        HEADER_FLAGS_NONE,
        HEADER_RESERVED,
        section_count,
        payload_length,
        0,
    )


# ══════════════════════════════════════════════════════════════════════════════
# ATCB ENCODING
# ══════════════════════════════════════════════════════════════════════════════


def encode_module(
    module: CompiledModule,
) -> bytes:
    """
    Encode a CompiledModule into canonical ATCB ABI v1.0.
    """

    module.validate()

    if module.bytecode_version != BYTECODE_VERSION:
        raise BytecodeValidationError(
            "Module bytecode version does not match ABI."
        )

    sections = build_sections(
        module
    )

    actual_order = tuple(
        section.type
        for section in sections
    )

    if actual_order != CANONICAL_SECTION_ORDER:
        raise BytecodeValidationError(
            "Internal ABI section order violation."
        )

    encoded_sections = b"".join(
        section.encode()
        for section in sections
    )

    payload_length = len(
        encoded_sections
    )

    if payload_length > MAX_U32:
        raise BytecodeFormatError(
            "ATCB payload exceeds u32."
        )

    header = _encode_header(
        section_count=len(sections),
        payload_length=payload_length,
    )

    return (
        header
        + encoded_sections
    )


# ══════════════════════════════════════════════════════════════════════════════
# HEADER DECODING
# ══════════════════════════════════════════════════════════════════════════════


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

    # Major mismatch is always incompatible.
    if major != ABI_VERSION_MAJOR:
        raise BytecodeFormatError(
            f"Unsupported ATCB ABI major version: {major}"
        )

    # A decoder may read an older minor version.
    if minor > ABI_VERSION_MINOR:
        raise BytecodeFormatError(
            "ATCB ABI minor version is newer than "
            f"supported version: {major}.{minor}"
        )

    if flags != HEADER_FLAGS_NONE:
        raise BytecodeFormatError(
            f"Unsupported ATCB flags: {flags:#x}"
        )

    if reserved != HEADER_RESERVED:
        raise BytecodeFormatError(
            "ATCB reserved header byte must be zero."
        )

    # ABI 1.0 checksum semantics are explicitly zero.
    if checksum != 0:
        raise BytecodeFormatError(
            "ATCB ABI 1.0 checksum field must be zero."
        )

    actual_payload_length = (
        len(data) - HEADER_SIZE
    )

    if payload_length != actual_payload_length:
        raise BytecodeFormatError(
            "ATCB payload length mismatch: "
            f"declared={payload_length}, "
            f"actual={actual_payload_length}"
        )

    return {
        "magic": magic,
        "abi_version": (
            major,
            minor,
        ),
        "flags": flags,
        "reserved": reserved,
        "section_count": section_count,
        "payload_length": payload_length,
        "checksum": checksum,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION DECODING
# ══════════════════════════════════════════════════════════════════════════════


def decode_sections(
    data: bytes,
) -> List[ABISection]:
    header = decode_header(
        data
    )

    section_count = header[
        "section_count"
    ]

    if section_count != len(
        CANONICAL_SECTION_ORDER
    ):
        raise BytecodeFormatError(
            "ATCB ABI 1.x requires exactly "
            f"{len(CANONICAL_SECTION_ORDER)} sections."
        )

    offset = HEADER_SIZE

    sections: List[ABISection] = []

    for expected_type in CANONICAL_SECTION_ORDER:
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

        try:
            section_type = SectionType(
                section_id
            )
        except ValueError as exc:
            raise BytecodeFormatError(
                f"Unknown ATCB section type: "
                f"{section_id:#x}"
            ) from exc

        if section_type != expected_type:
            raise BytecodeFormatError(
                "Invalid ATCB section order: "
                f"expected={expected_type.name}, "
                f"actual={section_type.name}"
            )

        _require_available(
            data,
            offset,
            length,
        )

        end = offset + length

        payload = data[
            offset:end
        ]

        offset = end

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

    return sections


# ══════════════════════════════════════════════════════════════════════════════
# BINARY VALIDATION
# ══════════════════════════════════════════════════════════════════════════════


def validate_binary(
    data: bytes,
) -> None:
    """
    Validate the ATCB container structure without executing bytecode.

    This function validates:

    * header
    * ABI version
    * flags
    * reserved fields
    * payload length
    * section count
    * section ordering
    * section bounds
    * section identifiers
    * absence of trailing bytes
    """

    sections = decode_sections(
        data
    )

    if len(sections) != len(
        CANONICAL_SECTION_ORDER
    ):
        raise BytecodeFormatError(
            "Invalid ATCB section count."
        )

    for index, section in enumerate(
        sections
    ):
        if section.type != CANONICAL_SECTION_ORDER[
            index
        ]:
            raise BytecodeFormatError(
                "Invalid canonical section order."
            )

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
    if type(path) is not str:
        raise BytecodeValidationError(
            "ABI path must be a string."
        )

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
    if type(path) is not str:
        raise BytecodeValidationError(
            "ABI path must be a string."
        )

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
    Return machine-readable normative ABI information.
    """

    return {
        "name": ABI_NAME,
        "version": [
            ABI_VERSION_MAJOR,
            ABI_VERSION_MINOR,
        ],
        "magic": ABI_MAGIC.decode(
            "ascii"
        ),
        "endianness": "big",
        "header_size": HEADER_SIZE,
        "section_header_size": SECTION_HEADER_SIZE,
        "header_flags": HEADER_FLAGS_NONE,
        "header_reserved": HEADER_RESERVED,
        "sections": {
            section.name: int(section)
            for section in SectionType
        },
        "section_order": [
            section.name
            for section in CANONICAL_SECTION_ORDER
        ],
        "constant_types": {
            constant.name: int(constant)
            for constant in ABIConstantType
        },
        "operand_types": {
            operand.name: int(operand)
            for operand in OperandType
        },
        "limits": {
            "max_u8": MAX_U8,
            "max_u16": MAX_U16,
            "max_u32": MAX_U32,
            "max_u64": MAX_U64,
            "min_i64": MIN_I64,
            "max_i64": MAX_I64,
            "max_operands": MAX_OPERANDS,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # ABI
    "ABI_NAME",
    "ABI_MAGIC",
    "ABI_VERSION_MAJOR",
    "ABI_VERSION_MINOR",
    "ABI_VERSION",

    # Limits
    "MAX_U8",
    "MAX_U16",
    "MAX_U32",
    "MAX_U64",
    "MIN_I64",
    "MAX_I64",

    # Header
    "HEADER_SIZE",
    "HEADER_FLAGS_NONE",
    "HEADER_RESERVED",

    # Sections
    "SectionType",
    "SECTION_HEADER_SIZE",
    "CANONICAL_SECTION_ORDER",
    "ABISection",

    # Metadata
    "ABIMetadata",

    # Constants
    "ABIConstantType",
    "encode_constant",
    "encode_constant_pool",

    # Operands
    "OperandType",
    "OPERAND_HEADER_SIZE",
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