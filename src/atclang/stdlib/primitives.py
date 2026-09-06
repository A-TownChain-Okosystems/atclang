# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Stdlib — ATC::Primitives
Core Blockchain-Typen für ATCLang.
ATC-94 | Sprint 2.5 | Non-EVM: SHA-256, Chain-ID 658467
"""
import hashlib
import time
from typing import Optional, Dict, Any, List


class ATCAddress:
    """ATC Address — 35 chars (ATC + 32 hex)."""

    def __init__(self, value: str):
        if not value.startswith('ATC') or len(value) != 35:
            raise ValueError(f"Invalid ATC address: {value}")
        self._value = value

    @staticmethod
    def from_pubkey(pubkey: str) -> 'ATCAddress':
        """Derive address from public key."""
        h = hashlib.sha256(pubkey.encode()).hexdigest()
        return ATCAddress('ATC' + h[:32])

    @staticmethod
    def zero() -> 'ATCAddress':
        """Zero address."""
        return ATCAddress('ATC' + '0' * 32)

    def as_string(self) -> str:
        return self._value

    def as_bytes(self) -> bytes:
        return bytes.fromhex(self._value[3:])

    def __eq__(self, other):
        if isinstance(other, ATCAddress):
            return self._value == other._value
        return False

    def __hash__(self):
        return hash(self._value)

    def __repr__(self):
        return f"ATCAddress({self._value})"


class ATCHash:
    """ATC Hash256 — 64 char hex string (SHA-256)."""

    def __init__(self, value: str):
        if len(value) != 64:
            raise ValueError(f"Invalid hash length: {len(value)}")
        self._value = value

    @staticmethod
    def compute(data: bytes) -> 'ATCHash':
        """Compute SHA-256 hash."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return ATCHash(hashlib.sha256(data).hexdigest())

    @staticmethod
    def zero() -> 'ATCHash':
        """Zero hash."""
        return ATCHash('0' * 64)

    def as_string(self) -> str:
        return self._value

    def as_bytes(self) -> bytes:
        return bytes.fromhex(self._value)

    def __eq__(self, other):
        if isinstance(other, ATCHash):
            return self._value == other._value
        return False

    def __hash__(self):
        return hash(self._value)

    def __repr__(self):
        return f"ATCHash({self._value[:16]}...)"


class ATCSignature:
    """ATC Signature — 64 byte hex string (simplified)."""

    def __init__(self, value: str):
        self._value = value

    @staticmethod
    def create(message: str, private_key: str) -> 'ATCSignature':
        """Create signature (simplified HMAC-SHA256)."""
        import hmac
        msg_hash = hashlib.sha256(message.encode()).hexdigest()
        sig = hmac.new(
            private_key.encode(), msg_hash.encode(), hashlib.sha256
        ).hexdigest()
        return ATCSignature(sig)

    def as_string(self) -> str:
        return self._value

    def __repr__(self):
        return f"ATCSignature({self._value[:16]}...)"


class ATCTransaction:
    """ATC Transaction — core transaction structure."""

    def __init__(self, sender: str, receiver: str, amount: int,
                 gas_price: int = 1, gas_limit: int = 30000000,
                 data: str = "", nonce: int = 0):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.gas_price = gas_price
        self.gas_limit = gas_limit
        self.data = data
        self.nonce = nonce
        self.timestamp = int(time.time())
        self.signature: Optional[str] = None
        self.hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute transaction hash."""
        content = f"{self.sender}{self.receiver}{self.amount}{self.nonce}{self.timestamp}"
        self.hash = hashlib.sha256(content.encode()).hexdigest()
        return self.hash

    def sign(self, private_key: str) -> str:
        """Sign transaction."""
        if not self.hash:
            self.compute_hash()
        self.signature = ATCSignature.create(self.hash, private_key).as_string()
        return self.signature

    def to_dict(self) -> Dict[str, Any]:
        return {
            'sender': self.sender,
            'receiver': self.receiver,
            'amount': self.amount,
            'gas_price': self.gas_price,
            'gas_limit': self.gas_limit,
            'data': self.data,
            'nonce': self.nonce,
            'timestamp': self.timestamp,
            'signature': self.signature,
            'hash': self.hash,
        }


class ATCBlockHeader:
    """ATC Block Header."""

    def __init__(self, number: int, prev_hash: str,
                 merkle_root: str, timestamp: int = None,
                 nonce: int = 0, difficulty: int = 1):
        self.number = number
        self.prev_hash = prev_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp or int(time.time())
        self.nonce = nonce
        self.difficulty = difficulty
        self.hash: Optional[str] = None

    def compute_hash(self) -> str:
        """Compute block header hash."""
        content = f"{self.number}{self.prev_hash}{self.merkle_root}{self.timestamp}{self.nonce}"
        self.hash = hashlib.sha256(content.encode()).hexdigest()
        return self.hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            'number': self.number,
            'prev_hash': self.prev_hash,
            'merkle_root': self.merkle_root,
            'timestamp': self.timestamp,
            'nonce': self.nonce,
            'difficulty': self.difficulty,
            'hash': self.hash,
        }


class ATCPrimitives:
    """ATC::Primitives — Factory functions for blockchain types."""

    # ── Address ──────────────────────────────────

    @staticmethod
    def new_address(pubkey: str) -> ATCAddress:
        """Create address from pubkey. Gas: 30"""
        return ATCAddress.from_pubkey(pubkey)

    @staticmethod
    def zero_address() -> ATCAddress:
        """Zero address. Gas: 5"""
        return ATCAddress.zero()

    @staticmethod
    def is_valid_address(addr: str) -> bool:
        """Validate address. Gas: 5"""
        try:
            ATCAddress(addr)
            return True
        except ValueError:
            return False

    # ── Hash ─────────────────────────────────────

    @staticmethod
    def compute_hash(data: bytes) -> ATCHash:
        """SHA-256 hash. Gas: 30"""
        return ATCHash.compute(data)

    @staticmethod
    def zero_hash() -> ATCHash:
        """Zero hash. Gas: 5"""
        return ATCHash.zero()

    # ── Signature ────────────────────────────────

    @staticmethod
    def sign(message: str, private_key: str) -> ATCSignature:
        """Sign message. Gas: 100"""
        return ATCSignature.create(message, private_key)

    # ── Transaction ──────────────────────────────

    @staticmethod
    def new_transaction(sender: str, receiver: str, amount: int,
                        gas_price: int = 1, nonce: int = 0) -> ATCTransaction:
        """Create transaction. Gas: 50"""
        return ATCTransaction(sender, receiver, amount, gas_price=gas_price, nonce=nonce)

    # ── Block Header ─────────────────────────────

    @staticmethod
    def new_block_header(number: int, prev_hash: str,
                         merkle_root: str) -> ATCBlockHeader:
        """Create block header. Gas: 50"""
        return ATCBlockHeader(number, prev_hash, merkle_root)
