# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""ATCLang Stdlib — deterministic ATC primitive types.

Consensus-visible timestamps are explicit inputs. No primitive reads the host clock.
"""

import hashlib
from typing import Any


class ATCAddress:
    """ATC Address — 35 chars (ATC + 32 hex)."""

    def __init__(self, value: str):
        if not value.startswith("ATC") or len(value) != 35:
            raise ValueError(f"Invalid ATC address: {value}")
        self._value = value

    @staticmethod
    def from_pubkey(pubkey: str) -> "ATCAddress":
        """Derive address deterministically from public key material."""
        h = hashlib.sha256(pubkey.encode()).hexdigest()
        return ATCAddress("ATC" + h[:32])

    @staticmethod
    def zero() -> "ATCAddress":
        return ATCAddress("ATC" + "0" * 32)

    def as_string(self) -> str:
        return self._value

    def as_bytes(self) -> bytes:
        return bytes.fromhex(self._value[3:])

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ATCAddress) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"ATCAddress({self._value})"


class ATCHash:
    """ATC Hash256 — 64 char hex string (SHA-256)."""

    def __init__(self, value: str):
        if len(value) != 64:
            raise ValueError(f"Invalid hash length: {len(value)}")
        self._value = value

    @staticmethod
    def compute(data: bytes | str) -> "ATCHash":
        if isinstance(data, str):
            data = data.encode("utf-8")
        return ATCHash(hashlib.sha256(data).hexdigest())

    @staticmethod
    def zero() -> "ATCHash":
        return ATCHash("0" * 64)

    def as_string(self) -> str:
        return self._value

    def as_bytes(self) -> bytes:
        return bytes.fromhex(self._value)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ATCHash) and self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return f"ATCHash({self._value[:16]}...)"


class ATCSignature:
    """ATC signature container.

    The Python reference layer must not be mistaken for the canonical signature
    implementation; production verification belongs to the Rust cryptographic
    boundary. This container therefore performs no fake verification.
    """

    def __init__(self, value: str):
        self._value = value

    @staticmethod
    def create(message: str, private_key: str) -> "ATCSignature":
        # Reference-only deterministic placeholder; canonical signing is Rust.
        msg_hash = hashlib.sha256(message.encode()).hexdigest()
        return ATCSignature(hashlib.sha256((private_key + msg_hash).encode()).hexdigest())

    def as_string(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"ATCSignature({self._value[:16]}...)"


class ATCTransaction:
    """ATC Transaction — timestamp must be supplied by the caller/context."""

    def __init__(
        self,
        sender: str,
        receiver: str,
        amount: int,
        gas_price: int = 1,
        gas_limit: int = 30000000,
        data: str = "",
        nonce: int = 0,
        timestamp: int = 0,
    ):
        if timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.gas_price = gas_price
        self.gas_limit = gas_limit
        self.data = data
        self.nonce = nonce
        self.timestamp = timestamp
        self.signature: str | None = None
        self.hash: str | None = None

    def compute_hash(self) -> str:
        content = f"{self.sender}{self.receiver}{self.amount}{self.nonce}{self.timestamp}"
        self.hash = hashlib.sha256(content.encode()).hexdigest()
        return self.hash

    def sign(self, private_key: str) -> str:
        if not self.hash:
            self.compute_hash()
        self.signature = ATCSignature.create(self.hash, private_key).as_string()
        return self.signature

    def to_dict(self) -> dict[str, Any]:
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "gas_price": self.gas_price,
            "gas_limit": self.gas_limit,
            "data": self.data,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "signature": self.signature,
            "hash": self.hash,
        }


class ATCBlockHeader:
    """ATC Block Header with an explicit deterministic timestamp."""

    def __init__(
        self,
        number: int,
        prev_hash: str,
        merkle_root: str,
        timestamp: int = 0,
        nonce: int = 0,
        difficulty: int = 1,
    ):
        if timestamp < 0:
            raise ValueError("timestamp must be non-negative")
        self.number = number
        self.prev_hash = prev_hash
        self.merkle_root = merkle_root
        self.timestamp = timestamp
        self.nonce = nonce
        self.difficulty = difficulty
        self.hash: str | None = None

    def compute_hash(self) -> str:
        content = f"{self.number}{self.prev_hash}{self.merkle_root}{self.timestamp}{self.nonce}"
        self.hash = hashlib.sha256(content.encode()).hexdigest()
        return self.hash

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "nonce": self.nonce,
            "difficulty": self.difficulty,
            "hash": self.hash,
        }


class ATCPrimitives:
    """ATC::Primitives — factory functions for blockchain types."""

    @staticmethod
    def new_address(pubkey: str) -> ATCAddress:
        return ATCAddress.from_pubkey(pubkey)

    @staticmethod
    def zero_address() -> ATCAddress:
        return ATCAddress.zero()

    @staticmethod
    def is_valid_address(addr: str) -> bool:
        try:
            ATCAddress(addr)
            return True
        except ValueError:
            return False

    @staticmethod
    def compute_hash(data: bytes) -> ATCHash:
        return ATCHash.compute(data)

    @staticmethod
    def zero_hash() -> ATCHash:
        return ATCHash.zero()

    @staticmethod
    def sign(message: str, private_key: str) -> ATCSignature:
        return ATCSignature.create(message, private_key)

    @staticmethod
    def new_transaction(
        sender: str,
        receiver: str,
        amount: int,
        gas_price: int = 1,
        nonce: int = 0,
        timestamp: int = 0,
    ) -> ATCTransaction:
        return ATCTransaction(
            sender,
            receiver,
            amount,
            gas_price=gas_price,
            nonce=nonce,
            timestamp=timestamp,
        )

    @staticmethod
    def new_block_header(
        number: int,
        prev_hash: str,
        merkle_root: str,
        timestamp: int = 0,
    ) -> ATCBlockHeader:
        return ATCBlockHeader(number, prev_hash, merkle_root, timestamp=timestamp)
