from atclang.stdlib.canonical_reference import (
    canonical_bytes,
    decode_u128_be,
    encode_u128_be,
    encode_u256_be,
    u256_add,
    u256_sub,
)


def test_u128_boundaries():
    assert encode_u128_be(0) == b"\x00" * 16
    assert decode_u128_be(encode_u128_be((1 << 128) - 1)) == (1 << 128) - 1


def test_u256_boundaries():
    assert len(encode_u256_be((1 << 256) - 1)) == 32
    assert u256_add(1, 2) == 3
    assert u256_sub(3, 2) == 1


def test_canonical_bytes_is_length_delimited():
    assert canonical_bytes([b"a", b"bc"]) == b"\x00\x00\x00\x01a\x00\x00\x00\x02bc"


def test_overflow_fails_closed():
    try:
        encode_u128_be(1 << 128)
    except ValueError:
        pass
    else:
        raise AssertionError("overflow must fail closed")

    try:
        u256_sub(0, 1)
    except OverflowError:
        pass
    else:
        raise AssertionError("underflow must fail closed")
