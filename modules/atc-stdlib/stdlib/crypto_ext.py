# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Standard Library — Crypto Module v1.0
Erweiterte Krypto-Funktionen für ATCLang.
Standard: ATC-95
"""

import hashlib
import hmac
import os
import struct

class ATCCryptoExt:
    """Erweiterte Krypto-Funktionen über ATCCrypto hinaus."""

    # ── Hash-Funktionen ──────────────────────────────
    @staticmethod
    def keccak256(data: bytes) -> bytes:
        return hashlib.sha3_256(data).digest()

    @staticmethod
    def ripemd160(data: bytes) -> bytes:
        h = hashlib.new("ripemd160")
        h.update(data)
        return h.digest()

    @staticmethod
    def blake2b(data: bytes, size: int = 32) -> bytes:
        return hashlib.blake2b(data, digest_size=size).digest()

    @staticmethod
    def blake2s(data: bytes, size: int = 32) -> bytes:
        return hashlib.blake2s(data, digest_size=size).digest()

    @staticmethod
    def hash160(data: bytes) -> bytes:
        """Bitcoin-style: SHA256 + RIPEMD160."""
        sha = hashlib.sha256(data).digest()
        return ATCCryptoExt.ripemd160(sha)

    # ── MAC / Signatur ───────────────────────────────
    @staticmethod
    def hmac_sha512(key: bytes, msg: bytes) -> bytes:
        return hmac.new(key, msg, hashlib.sha512).digest()

    @staticmethod
    def hmac_blake2b(key: bytes, msg: bytes) -> bytes:
        return hmac.new(key, msg, hashlib.blake2b).digest()

    # ── Encoding ─────────────────────────────────────
    @staticmethod
    def base58_encode_ext(data: bytes) -> str:
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        num = int.from_bytes(data, "big")
        result = ""
        while num > 0:
            num, rem = divmod(num, 58)
            result = alphabet[rem] + result
        # Leading zero bytes
        pad = 0
        for b in data:
            if b == 0:
                pad += 1
            else:
                break
        return alphabet[0] * pad + result

    @staticmethod
    def base58_decode_ext(s: str) -> bytes:
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        num = 0
        for c in s:
            num = num * 58 + alphabet.index(c)
        # Determine byte length
        byte_len = (num.bit_length() + 7) // 8
        result = num.to_bytes(byte_len, "big")
        # Leading '1's → leading zero bytes
        pad = 0
        for c in s:
            if c == alphabet[0]:
                pad += 1
            else:
                break
        return b"\x00" * pad + result

    # ── Zufall ───────────────────────────────────────
    @staticmethod
    def random_bytes(n: int) -> bytes:
        return os.urandom(n)

    @staticmethod
    def random_int(min_val: int, max_val: int) -> int:
        import secrets
        return secrets.randbelow(max_val - min_val) + min_val

    @staticmethod
    def random_hex(n: int) -> str:
        return os.urandom(n).hex()

    # ── Merkle-Tree ──────────────────────────────────
    @staticmethod
    def merkle_root(hashes: list) -> bytes:
        if not hashes:
            return b"\x00" * 32
        if len(hashes) == 1:
            return hashes[0]
        # Pad to even
        if len(hashes) % 2 == 1:
            hashes = hashes + [hashes[-1]]
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            next_level.append(hashlib.sha256(combined).digest())
        return ATCCryptoExt.merkle_root(next_level)

    @staticmethod
    def merkle_proof(hashes: list, index: int) -> list:
        if len(hashes) <= 1:
            return []
        if len(hashes) % 2 == 1:
            hashes = hashes + [hashes[-1]]
        proof = []
        sibling_idx = index + 1 if index % 2 == 0 else index - 1
        if sibling_idx < len(hashes):
            proof.append(hashes[sibling_idx])
        parent_idx = index // 2
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            next_level.append(hashlib.sha256(combined).digest())
        proof.extend(ATCCryptoExt.merkle_proof(next_level, parent_idx))
        return proof

    # ── Difficulty / Mining ──────────────────────────
    @staticmethod
    def leading_zeros(hash_hex: str) -> int:
        count = 0
        for c in hash_hex:
            if c == "0":
                count += 1
            else:
                break
        return count

    @staticmethod
    def check_difficulty(hash_bytes: bytes, difficulty: int) -> bool:
        target = (2 ** 256 - 1) >> difficulty
        value = int.from_bytes(hash_bytes, "big")
        return value < target
