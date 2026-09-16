# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""ATCLang Stdlib — ATC::Crypto.

Hashing and encoding are deterministic reference operations. Canonical
cryptographic signing, verification and wallet derivation remain outside the
Python reference trust boundary until a protocol-conformant backend is bound.
"""

import base64
import hashlib
import hmac

from atclang.security.reference_boundary import (
    ecdsa_sign,
    ecdsa_verify,
    wallet_operation,
)


class ATCCrypto:
    """ATC::Crypto — deterministic non-canonical reference primitives."""

    @staticmethod
    def sha256(data) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sha256_bytes(data) -> bytes:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(data).digest()

    @staticmethod
    def double_sha256(data) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return hashlib.sha256(hashlib.sha256(data).digest()).hexdigest()

    @staticmethod
    def hmac_sha256(key, msg) -> str:
        if isinstance(key, str):
            key = key.encode("utf-8")
        if isinstance(msg, str):
            msg = msg.encode("utf-8")
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    @staticmethod
    def base58_encode(data) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        num = int.from_bytes(data, "big")
        result = ""
        while num > 0:
            num, rem = divmod(num, 58)
            result = alphabet[rem] + result
        for byte in data:
            if byte == 0:
                result = "1" + result
            else:
                break
        return result or "1"

    @staticmethod
    def base58_decode(s: str) -> bytes:
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        num = 0
        for char in s:
            num = num * 58 + alphabet.index(char)
        leading = 0
        for char in s:
            if char == "1":
                leading += 1
            else:
                break
        if num == 0:
            return b"\x00" * leading
        byte_length = (num.bit_length() + 7) // 8
        return b"\x00" * leading + num.to_bytes(byte_length, "big")

    @staticmethod
    def base64_encode(data) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return base64.b64encode(data).decode("ascii")

    @staticmethod
    def base64_decode(s: str) -> bytes:
        return base64.b64decode(s)

    @staticmethod
    def hex_encode(data) -> str:
        if isinstance(data, str):
            data = data.encode("utf-8")
        return data.hex()

    @staticmethod
    def hex_decode(s: str) -> bytes:
        return bytes.fromhex(s)

    @staticmethod
    def _seed_bytes(seed) -> bytes:
        if isinstance(seed, str):
            seed = seed.encode("utf-8")
        if not isinstance(seed, (bytes, bytearray)) or not seed:
            raise ValueError("explicit deterministic vm_seed is required")
        return bytes(seed)

    @staticmethod
    def _deterministic_bytes(seed, n: int, domain: bytes = b"ATC::Crypto") -> bytes:
        if n < 0:
            raise ValueError("length must be non-negative")
        seed_bytes = ATCCrypto._seed_bytes(seed)
        out = bytearray()
        counter = 0
        while len(out) < n:
            block = hmac.new(
                seed_bytes,
                domain + counter.to_bytes(8, "big"),
                hashlib.sha256,
            ).digest()
            out.extend(block)
            counter += 1
        return bytes(out[:n])

    @staticmethod
    def generate_keypair(seed=None):
        return wallet_operation("generate_keypair", seed)

    @staticmethod
    def sign(message: str, private_key: str):
        return ecdsa_sign(message, private_key)

    @staticmethod
    def verify(message: str, signature: str, public_key: str):
        return ecdsa_verify(message, signature, public_key)

    @staticmethod
    def random_bytes(n: int, vm_seed=None) -> bytes:
        return ATCCrypto._deterministic_bytes(vm_seed, n, b"ATC::Crypto::random_bytes")

    @staticmethod
    def random_int(min_val: int, max_val: int, vm_seed=None) -> int:
        if max_val < min_val:
            raise ValueError("max_val must be >= min_val")
        span = max_val - min_val + 1
        raw = int.from_bytes(
            ATCCrypto._deterministic_bytes(vm_seed, 8, b"ATC::Crypto::random_int"),
            "big",
        )
        return min_val + raw % span

    @staticmethod
    def address_from_pubkey(pubkey: str):
        return wallet_operation("address_from_pubkey", pubkey)

    @staticmethod
    def is_valid_address(addr: str) -> bool:
        if not isinstance(addr, str) or not addr.startswith("ATC"):
            return False
        if len(addr) != 35:
            return False
        try:
            int(addr[3:], 16)
            return True
        except ValueError:
            return False
