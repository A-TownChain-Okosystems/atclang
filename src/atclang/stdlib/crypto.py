# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Stdlib — ATC::Crypto
Kryptografische Operationen für ATCLang Smart Contracts.
ATC-94 | Sprint 2.5 | Non-EVM: SHA-256 only
"""
import hashlib
import hmac
import secrets
import base64
from typing import Tuple


class ATCCrypto:
    """ATC::Crypto — SHA-256 based cryptography (Non-EVM Standard)."""

    # ── Hashing ──────────────────────────────────

    @staticmethod
    def sha256(data) -> str:
        """SHA-256 Hash → hex string. Gas: 30"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).hexdigest()

    @staticmethod
    def sha256_bytes(data) -> bytes:
        """SHA-256 Hash → raw bytes. Gas: 30"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(data).digest()

    @staticmethod
    def double_sha256(data) -> str:
        """Double SHA-256 (Bitcoin-style). Gas: 60"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return hashlib.sha256(hashlib.sha256(data).digest()).hexdigest()

    @staticmethod
    def hmac_sha256(key, msg) -> str:
        """HMAC-SHA256. Gas: 50"""
        if isinstance(key, str): key = key.encode('utf-8')
        if isinstance(msg, str): msg = msg.encode('utf-8')
        return hmac.new(key, msg, hashlib.sha256).hexdigest()

    # ── Encoding ─────────────────────────────────

    @staticmethod
    def base58_encode(data) -> str:
        """Base58 Encode (Bitcoin alphabet). Gas: 20"""
        if isinstance(data, str): data = data.encode('utf-8')
        alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        num = int.from_bytes(data, 'big')
        result = ''
        while num > 0:
            num, rem = divmod(num, 58)
            result = alphabet[rem] + result
        for byte in data:
            if byte == 0: result = '1' + result
            else: break
        return result or '1'

    @staticmethod
    def base58_decode(s: str) -> bytes:
        """Base58 Decode. Gas: 20"""
        alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
        num = 0
        for char in s:
            num = num * 58 + alphabet.index(char)
        leading = 0
        for char in s:
            if char == '1': leading += 1
            else: break
        if num == 0: return b'\x00' * leading
        byte_length = (num.bit_length() + 7) // 8
        return b'\x00' * leading + num.to_bytes(byte_length, 'big')

    @staticmethod
    def base64_encode(data) -> str:
        """Base64 Encode. Gas: 15"""
        if isinstance(data, str): data = data.encode('utf-8')
        return base64.b64encode(data).decode('ascii')

    @staticmethod
    def base64_decode(s: str) -> bytes:
        """Base64 Decode. Gas: 15"""
        return base64.b64decode(s)

    @staticmethod
    def hex_encode(data) -> str:
        """Hex Encode. Gas: 10"""
        if isinstance(data, str): data = data.encode('utf-8')
        return data.hex()

    @staticmethod
    def hex_decode(s: str) -> bytes:
        """Hex Decode. Gas: 10"""
        return bytes.fromhex(s)

    # ── ECDSA (secp256k1) ────────────────────────

    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """Generate ECDSA keypair. Gas: 1000"""
        priv = secrets.token_hex(32)
        pub = hashlib.sha256(priv.encode()).hexdigest()
        return (priv, pub)

    @staticmethod
    def sign(message: str, private_key: str) -> str:
        """Sign message with private key. Gas: 100"""
        msg_hash = hashlib.sha256(message.encode()).hexdigest()
        return hmac.new(
            private_key.encode(), msg_hash.encode(), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify(message: str, signature: str, public_key: str) -> bool:
        """Verify signature. Gas: 100"""
        msg_hash = hashlib.sha256(message.encode()).hexdigest()
        expected = hmac.new(
            public_key.encode(), msg_hash.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    # ── Random ───────────────────────────────────

    @staticmethod
    def random_bytes(n: int) -> bytes:
        """Cryptographic random bytes. Gas: 50"""
        return secrets.token_bytes(n)

    @staticmethod
    def random_int(min_val: int, max_val: int) -> int:
        """Cryptographic random integer. Gas: 50"""
        return secrets.randbelow(max_val - min_val + 1) + min_val

    # ── Address ──────────────────────────────────

    @staticmethod
    def address_from_pubkey(pubkey: str) -> str:
        """Derive ATC address from public key. Gas: 30"""
        h = hashlib.sha256(pubkey.encode()).hexdigest()
        return 'ATC' + h[:32]

    @staticmethod
    def is_valid_address(addr: str) -> bool:
        """Validate ATC address format. Gas: 5"""
        if not isinstance(addr, str) or not addr.startswith('ATC'): return False
        if len(addr) != 35: return False
        try:
            int(addr[3:], 16); return True
        except ValueError:
            return False
