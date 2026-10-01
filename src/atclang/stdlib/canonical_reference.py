"""ATCLang reference standard library.

This module is explicitly REFERENCE-only. It contains deterministic pure functions
used for differential conformance; it is never a consensus/runtime trust anchor.
"""

from __future__ import annotations
import hashlib
from collections.abc import Iterable


def encode_u128_be(value: int) -> bytes:
    if not 0 <= value < (1 << 128):
        raise ValueError("u128 out of range")
    return value.to_bytes(16, "big")


def decode_u128_be(data: bytes) -> int:
    if len(data) != 16:
        raise ValueError("u128 requires exactly 16 bytes")
    return int.from_bytes(data, "big")


def encode_u256_be(value: int) -> bytes:
    if not 0 <= value < (1 << 256):
        raise ValueError("u256 out of range")
    return value.to_bytes(32, "big")


def canonical_bytes(parts: Iterable[bytes]) -> bytes:
    out = bytearray()
    for part in parts:
        if not isinstance(part, bytes):
            raise TypeError("canonical encoding accepts bytes only")
        out.extend(len(part).to_bytes(4, "big"))
        out.extend(part)
    return bytes(out)


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def u256_add(a: int, b: int) -> int:
    if not 0 <= a < (1 << 256) or not 0 <= b < (1 << 256):
        raise ValueError("u256 out of range")
    result = a + b
    if result >= (1 << 256):
        raise OverflowError("u256 addition overflow")
    return result


def u256_sub(a: int, b: int) -> int:
    if not 0 <= a < (1 << 256) or not 0 <= b < (1 << 256):
        raise ValueError("u256 out of range")
    if b > a:
        raise OverflowError("u256 subtraction underflow")
    return a - b


def checked_cast_u128(value: int) -> int:
    return int.from_bytes(encode_u128_be(value), "big")


def require(condition: bool, message: str = "requirement failed") -> None:
    if not condition:
        raise ValueError(message)
