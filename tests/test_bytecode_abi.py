"""
ATCLang Bytecode ABI v1.0 Tests
================================

Normative tests for the ATC-92 / ATCLang Bytecode ABI.

These tests verify:

- ABI header layout
- ABI versioning
- Big-endian primitive encoding
- UTF-8 string encoding
- bytes encoding
- IEEE-754 binary64 encoding
- canonical constant encoding
- operand encoding
- instruction encoding
- instruction-stream encoding
- section construction
- deterministic binary output
- section ordering
- malformed/truncated binary rejection
- header validation
- trailing-byte rejection
- ABI information
- file roundtrip validation

The tests intentionally test the public ABI contract rather than
Python implementation details.
"""

from __future__ import annotations

import math
import struct

import pytest

from atclang.bytecode import (
    BYTECODE_MAGIC,
    BYTECODE_VERSION,
    BytecodeFormatError,
    BytecodeValidationError,
    CompiledModule,
    Instruction,
)

from atclang.bytecode_abi import (
    ABI_MAGIC,
    ABI_VERSION,
    ABI_VERSION_MAJOR,
    ABI_VERSION_MINOR,
    ABIConstantType,
    ABISection,
    HEADER_FLAGS_NONE,
    HEADER_SIZE,
    OperandType,
    SectionType,
    SECTION_HEADER_SIZE,
    abi_info,
    decode_bytes,
    decode_f64,
    decode_header,
    decode_i64,
    decode_sections,
    decode_string,
    decode_u16,
    decode_u32,
    decode_u64,
    decode_u8,
    encode_bytes,
    encode_constant,
    encode_f64,
    encode_functions,
    encode_i64,
    encode_instruction,
    encode_instruction_stream,
    encode_metadata,
    encode_module,
    encode_operand,
    encode_string,
    encode_u16,
    encode_u32,
    encode_u64,
    encode_u8,
    validate_binary,
    write_abi,
    read_abi,
)


# ============================================================================
# HELPERS
# ============================================================================


def make_module() -> CompiledModule:
    """
    Construct the smallest representative valid module.

    The helper intentionally uses only the public bytecode model.
    """

    return CompiledModule(
        name="test_module",
        language_version="ATCLang 0.3",
        compiler_version="ATCLang Compiler 1.0",
        entry_point="main",
        bytecode_version=BYTECODE_VERSION,
        constant_pool=[],
        instructions=[],
        functions={},
        function_params={},
        exports=[],
        source_map=[],
    )


def assert_roundtrip(encoded: bytes, decoder) -> None:
    value, offset = decoder(encoded)

    assert offset == len(encoded)
    assert value is not None


# ============================================================================
# ABI VERSION
# ============================================================================


def test_abi_version_is_1_0() -> None:
    assert ABI_VERSION_MAJOR == 1
    assert ABI_VERSION_MINOR == 0
    assert ABI_VERSION == (1, 0)


def test_abi_magic_matches_bytecode_magic() -> None:
    assert ABI_MAGIC == BYTECODE_MAGIC


# ============================================================================
# HEADER
# ============================================================================


def test_header_size_is_20_bytes() -> None:
    assert HEADER_SIZE == 20


def test_header_struct_is_big_endian() -> None:
    module = make_module()
    encoded = encode_module(module)

    assert encoded[:4] == ABI_MAGIC

    assert encoded[4] == ABI_VERSION_MAJOR
    assert encoded[5] == ABI_VERSION_MINOR
    assert encoded[6] == HEADER_FLAGS_NONE
    assert encoded[7] == 0

    # section count = 6
    assert encoded[8:12] == b"\x00\x00\x00\x06"


def test_header_can_be_decoded() -> None:
    module = make_module()
    encoded = encode_module(module)

    header = decode_header(encoded)

    assert header["magic"] == ABI_MAGIC
    assert header["abi_version"] == ABI_VERSION
    assert header["flags"] == 0
    assert header["section_count"] == 6
    assert header["payload_length"] == len(encoded) - HEADER_SIZE
    assert header["checksum"] == 0


def test_header_checksum_is_zero_for_abi_1_0() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[16:20] = b"\x00\x00\x00\x00"

    header = decode_header(bytes(encoded))

    assert header["checksum"] == 0


def test_invalid_magic_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[0:4] = b"XXXX"

    with pytest.raises(BytecodeFormatError):
        decode_header(bytes(encoded))


def test_invalid_major_version_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[4] = ABI_VERSION_MAJOR + 1

    with pytest.raises(BytecodeFormatError):
        decode_header(bytes(encoded))


def test_invalid_minor_version_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[5] = ABI_VERSION_MINOR + 1

    with pytest.raises(BytecodeFormatError):
        decode_header(bytes(encoded))


def test_nonzero_flags_are_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[6] = 0x01

    with pytest.raises(BytecodeFormatError):
        decode_header(bytes(encoded))


def test_nonzero_reserved_header_byte_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[7] = 0x01

    with pytest.raises(BytecodeFormatError):
        decode_header(bytes(encoded))


def test_nonzero_checksum_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[16:20] = b"\x00\x00\x00\x01"

    with pytest.raises(BytecodeFormatError):
        decode_header(bytes(encoded))


def test_payload_length_mismatch_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[12:16] = struct.pack(">I", 0)

    with pytest.raises(BytecodeFormatError):
        decode_header(bytes(encoded))


def test_truncated_header_is_rejected() -> None:
    with pytest.raises(BytecodeFormatError):
        decode_header(b"ATCB")


# ============================================================================
# INTEGER ENCODING
# ============================================================================


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, b"\x00"),
        (1, b"\x01"),
        (0xFF, b"\xFF"),
    ],
)
def test_u8_encoding(value: int, expected: bytes) -> None:
    assert encode_u8(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, b"\x00\x00"),
        (1, b"\x00\x01"),
        (0x1234, b"\x12\x34"),
        (0xFFFF, b"\xFF\xFF"),
    ],
)
def test_u16_big_endian(value: int, expected: bytes) -> None:
    assert encode_u16(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, b"\x00\x00\x00\x00"),
        (1, b"\x00\x00\x00\x01"),
        (0x12345678, b"\x12\x34\x56\x78"),
        (0xFFFFFFFF, b"\xFF\xFF\xFF\xFF"),
    ],
)
def test_u32_big_endian(value: int, expected: bytes) -> None:
    assert encode_u32(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, b"\x00" * 8),
        (1, b"\x00\x00\x00\x00\x00\x00\x00\x01"),
        (
            0x0102030405060708,
            b"\x01\x02\x03\x04\x05\x06\x07\x08",
        ),
    ],
)
def test_u64_big_endian(value: int, expected: bytes) -> None:
    assert encode_u64(value) == expected


def test_i64_negative_value_is_big_endian() -> None:
    assert encode_i64(-1) == b"\xFF" * 8


def test_u8_roundtrip() -> None:
    encoded = encode_u8(0xA5)

    value, offset = decode_u8(encoded)

    assert value == 0xA5
    assert offset == 1


def test_u16_roundtrip() -> None:
    encoded = encode_u16(0x1234)

    value, offset = decode_u16(encoded)

    assert value == 0x1234
    assert offset == 2


def test_u32_roundtrip() -> None:
    encoded = encode_u32(0x12345678)

    value, offset = decode_u32(encoded)

    assert value == 0x12345678
    assert offset == 4


def test_u64_roundtrip() -> None:
    encoded = encode_u64(0x0102030405060708)

    value, offset = decode_u64(encoded)

    assert value == 0x0102030405060708
    assert offset == 8


def test_i64_roundtrip() -> None:
    encoded = encode_i64(-(1 << 62))

    value, offset = decode_i64(encoded)

    assert value == -(1 << 62)
    assert offset == 8


@pytest.mark.parametrize(
    "value",
    [
        -1,
        0x100,
    ],
)
def test_u8_range_validation(value: int) -> None:
    with pytest.raises(BytecodeValidationError):
        encode_u8(value)


def test_u16_range_validation() -> None:
    with pytest.raises(BytecodeValidationError):
        encode_u16(0x10000)


def test_u32_range_validation() -> None:
    with pytest.raises(BytecodeValidationError):
        encode_u32(0x1_0000_0000)


def test_u64_range_validation() -> None:
    with pytest.raises(BytecodeValidationError):
        encode_u64(0x1_0000_0000_0000_0000)


def test_i64_range_validation() -> None:
    with pytest.raises(BytecodeValidationError):
        encode_i64(1 << 63)


# ============================================================================
# FLOAT ENCODING
# ============================================================================


def test_f64_uses_ieee754_binary64_big_endian() -> None:
    value = 1.5

    assert encode_f64(value) == struct.pack(">d", value)


@pytest.mark.parametrize(
    "value",
    [
        0.0,
        -0.0,
        1.0,
        -1.0,
        1.5,
        123456.789,
    ],
)
def test_f64_roundtrip(value: float) -> None:
    encoded = encode_f64(value)

    decoded, offset = decode_f64(encoded)

    assert offset == 8
    assert decoded == value


@pytest.mark.parametrize(
    "value",
    [
        math.nan,
        math.inf,
        -math.inf,
    ],
)
def test_nonfinite_f64_is_rejected(value: float) -> None:
    with pytest.raises(BytecodeValidationError):
        encode_f64(value)


def test_nonfinite_f64_in_binary_is_rejected() -> None:
    encoded = struct.pack(">d", math.inf)

    with pytest.raises(BytecodeFormatError):
        decode_f64(encoded)


# ============================================================================
# STRING / BYTES
# ============================================================================


def test_bytes_encoding_contains_u32_length() -> None:
    payload = b"ABC"

    assert encode_bytes(payload) == b"\x00\x00\x00\x03ABC"


def test_bytes_roundtrip() -> None:
    payload = b"\x00\x01\x02\xFF"

    encoded = encode_bytes(payload)

    decoded, offset = decode_bytes(encoded)

    assert decoded == payload
    assert offset == len(encoded)


def test_string_encoding_is_utf8() -> None:
    value = "ÄΩ𐍈"

    encoded = encode_string(value)
    raw = value.encode("utf-8")

    assert encoded[:4] == struct.pack(">I", len(raw))
    assert encoded[4:] == raw


def test_string_roundtrip() -> None:
    value = "ATCLang / ATC-92 / 漢字 / 🚀"

    encoded = encode_string(value)

    decoded, offset = decode_string(encoded)

    assert decoded == value
    assert offset == len(encoded)


def test_invalid_utf8_is_rejected() -> None:
    encoded = encode_u32(2) + b"\xFF\xFF"

    with pytest.raises(BytecodeFormatError):
        decode_string(encoded)


def test_truncated_bytes_are_rejected() -> None:
    encoded = encode_u32(10) + b"abc"

    with pytest.raises(BytecodeFormatError):
        decode_bytes(encoded)


# ============================================================================
# CONSTANT ABI
# ============================================================================


def test_constant_type_ids_are_explicit() -> None:
    assert int(ABIConstantType.NULL) == 0x01
    assert int(ABIConstantType.BOOL) == 0x02
    assert int(ABIConstantType.INT) == 0x03
    assert int(ABIConstantType.FLOAT) == 0x04
    assert int(ABIConstantType.STRING) == 0x05
    assert int(ABIConstantType.BYTES) == 0x06


def test_null_constant_encoding() -> None:
    from atclang.constants import Constant

    constant = Constant(
        index=0,
        type="NULL",
        value=None,
    )

    encoded = encode_constant(constant)

    assert encoded == (
        b"\x00\x00\x00\x00"
        b"\x01"
    )


def test_bool_constant_encoding() -> None:
    from atclang.constants import Constant

    constant = Constant(
        index=3,
        type="BOOL",
        value=True,
    )

    encoded = encode_constant(constant)

    assert encoded == (
        b"\x00\x00\x00\x03"
        b"\x02"
        b"\x01"
    )


def test_integer_constant_encoding() -> None:
    from atclang.constants import Constant

    constant = Constant(
        index=1,
        type="INT",
        value=-42,
    )

    encoded = encode_constant(constant)

    assert encoded[:4] == encode_u32(1)
    assert encoded[4] == ABIConstantType.INT
    assert encoded[5:] == encode_i64(-42)


def test_float_constant_encoding() -> None:
    from atclang.constants import Constant

    constant = Constant(
        index=2,
        type="FLOAT",
        value=3.5,
    )

    encoded = encode_constant(constant)

    assert encoded[:4] == encode_u32(2)
    assert encoded[4] == ABIConstantType.FLOAT
    assert encoded[5:] == encode_f64(3.5)


def test_string_constant_encoding() -> None:
    from atclang.constants import Constant

    constant = Constant(
        index=4,
        type="STRING",
        value="hello",
    )

    encoded = encode_constant(constant)

    assert encoded[:4] == encode_u32(4)
    assert encoded[4] == ABIConstantType.STRING
    assert encoded[5:] == encode_string("hello")


def test_bytes_constant_encoding() -> None:
    from atclang.constants import Constant

    constant = Constant(
        index=5,
        type="BYTES",
        value=b"\x01\x02",
    )

    encoded = encode_constant(constant)

    assert encoded[:4] == encode_u32(5)
    assert encoded[4] == ABIConstantType.BYTES
    assert encoded[5:] == encode_bytes(b"\x01\x02")


# ============================================================================
# OPERANDS
# ============================================================================


def test_null_operand_encoding() -> None:
    encoded = encode_operand(None)

    assert encoded == (
        b"\x07"
        b"\x00\x00\x00\x00"
    )


def test_bool_operand_encoding() -> None:
    encoded = encode_operand(True)

    assert encoded == (
        b"\x06"
        b"\x00\x00\x00\x01"
        b"\x01"
    )


def test_integer_operand_encoding() -> None:
    encoded = encode_operand(-10)

    assert encoded[:1] == bytes([OperandType.INT])
    assert encoded[1:5] == encode_u32(8)
    assert encoded[5:] == encode_i64(-10)


def test_float_operand_encoding() -> None:
    encoded = encode_operand(2.5)

    assert encoded[:1] == bytes([OperandType.FLOAT])
    assert encoded[1:5] == encode_u32(8)
    assert encoded[5:] == encode_f64(2.5)


def test_string_operand_encoding() -> None:
    encoded = encode_operand("abc")

    assert encoded[:1] == bytes([OperandType.STRING])
    assert encoded[1:5] == encode_u32(
        len(encode_string("abc"))
    )
    assert encoded[5:] == encode_string("abc")


def test_bytes_operand_encoding() -> None:
    encoded = encode_operand(b"abc")

    assert encoded[:1] == bytes([OperandType.BYTES])
    assert encoded[1:5] == encode_u32(
        len(encode_bytes(b"abc"))
    )
    assert encoded[5:] == encode_bytes(b"abc")


# ============================================================================
# OPCODE / INSTRUCTION ABI
# ============================================================================


def test_opcode_is_one_byte() -> None:
    instruction = Instruction(
        op=1,
        args=[],
    )

    encoded = encode_instruction(instruction)

    assert encoded[:2] == b"\x01\x00"


def test_instruction_operand_count_is_explicit() -> None:
    instruction = Instruction(
        op=7,
        args=[1, 2],
    )

    encoded = encode_instruction(instruction)

    assert encoded[0] == 7
    assert encoded[1] == 2


def test_instruction_encoding_is_deterministic() -> None:
    instruction = Instruction(
        op=7,
        args=[1, "abc", True],
    )

    first = encode_instruction(instruction)
    second = encode_instruction(instruction)

    assert first == second


def test_instruction_stream_contains_instruction_count() -> None:
    instructions = [
        Instruction(op=1, args=[]),
        Instruction(op=2, args=[42]),
    ]

    encoded = encode_instruction_stream(instructions)

    assert encoded[:4] == encode_u32(2)


def test_instruction_stream_is_deterministic() -> None:
    instructions = [
        Instruction(op=1, args=[]),
        Instruction(op=2, args=[42]),
    ]

    assert encode_instruction_stream(instructions) == (
        encode_instruction_stream(instructions)
    )


# ============================================================================
# SECTION ABI
# ============================================================================


def test_section_header_is_eight_bytes() -> None:
    assert SECTION_HEADER_SIZE == 8


def test_section_encoding_contains_type_and_length() -> None:
    section = ABISection(
        type=SectionType.METADATA,
        payload=b"abc",
    )

    encoded = section.encode()

    assert encoded[:4] == encode_u32(SectionType.METADATA)
    assert encoded[4:8] == encode_u32(3)
    assert encoded[8:] == b"abc"


def test_module_contains_exactly_six_sections() -> None:
    module = make_module()

    encoded = encode_module(module)
    sections = decode_sections(encoded)

    assert len(sections) == 6


def test_module_section_order_is_normative() -> None:
    module = make_module()

    sections = decode_sections(
        encode_module(module)
    )

    assert [section.type for section in sections] == [
        SectionType.METADATA,
        SectionType.CONSTANTS,
        SectionType.MAIN_CODE,
        SectionType.FUNCTIONS,
        SectionType.EXPORTS,
        SectionType.SOURCE_MAP,
    ]


def test_invalid_section_order_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    first_id = encoded[20:24]

    second_offset = (
        20
        + 8
        + struct.unpack(
            ">I",
            encoded[24:28],
        )[0]
    )

    second_id = encoded[
        second_offset:
        second_offset + 4
    ]

    encoded[20:24] = second_id

    encoded[
        second_offset:
        second_offset + 4
    ] = first_id

    with pytest.raises(BytecodeFormatError):
        decode_sections(bytes(encoded))


def test_unknown_section_type_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[20:24] = encode_u32(0xFFFF)

    with pytest.raises(BytecodeFormatError):
        decode_sections(bytes(encoded))


def test_trailing_bytes_are_rejected() -> None:
    module = make_module()
    encoded = encode_module(module) + b"\x00"

    with pytest.raises(BytecodeFormatError):
        validate_binary(encoded)


# ============================================================================
# METADATA
# ============================================================================


def test_metadata_encoding_is_utf8_based() -> None:
    module = make_module()

    encoded = encode_metadata(module)

    assert module.name.encode("utf-8") in encoded
    assert module.language_version.encode("utf-8") in encoded
    assert module.compiler_version.encode("utf-8") in encoded
    assert module.entry_point.encode("utf-8") in encoded


# ============================================================================
# FUNCTIONS / EXPORTS
# ============================================================================


def test_empty_functions_encoding() -> None:
    encoded = encode_functions(
        functions={},
        function_params={},
        exports=[],
    )

    assert encoded == encode_u32(0)


def test_function_count_is_encoded() -> None:
    instructions = {
        "main": [
            Instruction(
                op=1,
                args=[],
            ),
        ],
    }

    encoded = encode_functions(
        functions=instructions,
        function_params={"main": []},
        exports=["main"],
    )

    assert encoded[:4] == encode_u32(1)


# ============================================================================
# FULL MODULE ABI
# ============================================================================


def test_encode_module_starts_with_atcb() -> None:
    module = make_module()

    encoded = encode_module(module)

    assert encoded[:4] == b"ATCB"


def test_encode_module_is_at_least_header_size() -> None:
    module = make_module()

    encoded = encode_module(module)

    assert len(encoded) >= HEADER_SIZE


def test_encode_module_is_deterministic() -> None:
    module = make_module()

    first = encode_module(module)
    second = encode_module(module)

    assert first == second


def test_validate_binary_accepts_valid_module() -> None:
    module = make_module()

    encoded = encode_module(module)

    validate_binary(encoded)


def test_decode_sections_accepts_valid_module() -> None:
    module = make_module()

    sections = decode_sections(
        encode_module(module)
    )

    assert all(
        isinstance(section.payload, bytes)
        for section in sections
    )


# ============================================================================
# MALFORMED INPUT
# ============================================================================


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"A",
        b"AT",
        b"ATC",
        b"ATCB",
        b"ATCB\x01",
        b"\x00" * 19,
    ],
)
def test_short_binary_is_rejected(payload: bytes) -> None:
    with pytest.raises(BytecodeFormatError):
        validate_binary(payload)


def test_non_bytes_input_is_rejected() -> None:
    with pytest.raises(BytecodeFormatError):
        validate_binary("ATCB")  # type: ignore[arg-type]


def test_corrupt_section_length_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[24:28] = encode_u32(0xFFFFFFFF)

    with pytest.raises(BytecodeFormatError):
        validate_binary(bytes(encoded))


def test_corrupt_section_count_is_rejected() -> None:
    module = make_module()
    encoded = bytearray(encode_module(module))

    encoded[8:12] = encode_u32(7)

    with pytest.raises(BytecodeFormatError):
        validate_binary(bytes(encoded))


# ============================================================================
# FILE I/O
# ============================================================================


def test_write_and_read_abi(tmp_path) -> None:
    module = make_module()
    path = tmp_path / "module.atcb"

    write_abi(
        module,
        str(path),
    )

    assert path.exists()

    data = read_abi(
        str(path)
    )

    assert data == encode_module(module)


def test_written_binary_is_deterministic(tmp_path) -> None:
    module = make_module()

    path_a = tmp_path / "a.atcb"
    path_b = tmp_path / "b.atcb"

    write_abi(module, str(path_a))
    write_abi(module, str(path_b))

    assert path_a.read_bytes() == path_b.read_bytes()


# ============================================================================
# ABI INFORMATION
# ============================================================================


def test_abi_info_is_machine_readable() -> None:
    info = abi_info()

    assert info["name"] == "ATCLang Bytecode ABI"
    assert info["version"] == [1, 0]
    assert info["magic"] == "ATCB"
    assert info["endianness"] == "big"
    assert info["header_size"] == 20
    assert info["section_header_size"] == 8


def test_abi_info_contains_all_sections() -> None:
    info = abi_info()

    assert info["sections"] == {
        "METADATA": 1,
        "CONSTANTS": 2,
        "MAIN_CODE": 3,
        "FUNCTIONS": 4,
        "EXPORTS": 5,
        "SOURCE_MAP": 6,
    }


def test_abi_info_contains_constant_types() -> None:
    info = abi_info()

    assert info["constant_types"] == {
        "NULL": 1,
        "BOOL": 2,
        "INT": 3,
        "FLOAT": 4,
        "STRING": 5,
        "BYTES": 6,
    }


def test_abi_info_contains_operand_types() -> None:
    info = abi_info()

    assert info["operand_types"] == {
        "UINT": 1,
        "INT": 2,
        "FLOAT": 3,
        "STRING": 4,
        "BYTES": 5,
        "BOOL": 6,
        "NULL": 7,
        "CONSTANT_INDEX": 8,
    }