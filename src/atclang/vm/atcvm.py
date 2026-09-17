# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""Deterministic ATCLang reference VM.

Python is a reference/test implementation only. Rust is the canonical
production execution boundary. Host-sensitive security, wallet, network,
RPC, persistence and concurrency operations fail closed instead of simulating
success.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum, auto
from typing import Any

from atclang.legacy.security.reference_boundary import (
    ecdsa_sign,
    ecdsa_verify,
    fail_closed,
    net_send,
    rpc_call,
    verify_jwt,
    wallet_operation,
)
from atclang.stdlib.collections import ATCCollections
from atclang.stdlib.crypto import ATCCrypto
from atclang.stdlib.encoding import ATCEncoding
from atclang.stdlib.math import ATCMath


class OP(IntEnum):
    PUSH = auto()
    POP = auto()
    DUP = auto()
    SWAP = auto()
    ROT = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    POW = auto()
    NEG = auto()
    BITAND = auto()
    BITOR = auto()
    BITXOR = auto()
    BITNOT = auto()
    SHL = auto()
    SHR = auto()
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    LOAD = auto()
    STORE = auto()
    LOAD_IDX = auto()
    STORE_IDX = auto()
    LOAD_GLOBAL = auto()
    STORE_GLOBAL = auto()
    DEL_VAR = auto()
    JUMP = auto()
    JUMP_IF = auto()
    JUMP_NOT = auto()
    CALL = auto()
    RETURN = auto()
    CALL_EXT = auto()
    CALL_METHOD = auto()
    MAKE_FN = auto()
    NEW_MAP = auto()
    NEW_LIST = auto()
    NEW_OBJ = auto()
    GET_FIELD = auto()
    SET_FIELD = auto()
    HAS_KEY = auto()
    DEL_KEY = auto()
    LIST_PUSH = auto()
    LIST_POP = auto()
    LIST_LEN = auto()
    MAP_KEYS = auto()
    MAP_VALUES = auto()
    MAP_ITEMS = auto()
    CONTAINS = auto()
    CAST = auto()
    STR_LEN = auto()
    STR_SLICE = auto()
    STR_UPPER = auto()
    STR_LOWER = auto()
    STR_SPLIT = auto()
    STR_JOIN = auto()
    STR_FORMAT = auto()
    EMIT = auto()
    REQUIRE = auto()
    TRANSFER = auto()
    MINT = auto()
    BURN = auto()
    STAKE = auto()
    UNSTAKE = auto()
    VOTE = auto()
    HASH_SHA256 = auto()
    HASH_SHA3 = auto()
    HASH_SHA3_ATC = auto()
    CRYPTO_SIGN = auto()
    CRYPTO_VERIFY = auto()
    RAND_BYTES = auto()
    RAND_INT = auto()
    LEADING_ZEROS = auto()
    NET_SEND = auto()
    NET_RECV = auto()
    NET_BROADCAST = auto()
    NET_CONNECT = auto()
    NET_PEERS = auto()
    STORE_PERSIST = auto()
    LOAD_PERSIST = auto()
    FS_WRITE = auto()
    FS_READ = auto()
    FS_MKDIR = auto()
    ASYNC_CALL = auto()
    AWAIT = auto()
    SPAWN = auto()
    CHANNEL_SEND = auto()
    CHANNEL_RECV = auto()
    HALT = auto()
    NOP = auto()
    PRINT = auto()
    ASSERT = auto()
    DEBUG = auto()
    GAS_CHECK = auto()
    TIMESTAMP = auto()
    BLOCK_NUM = auto()
    CALLER = auto()
    LOG = auto()


@dataclass
class Instruction:
    op: OP
    args: list[Any] = field(default_factory=list)

    def __repr__(self) -> str:
        args = " ".join(str(value)[:30] for value in self.args)
        return f"{self.op.name:<16} {args}".rstrip()


@dataclass
class ATCFunction:
    name: str
    params: list[str]
    instructions: list[Instruction]


@dataclass
class CallFrame:
    func_name: str
    ip: int = 0
    locals: dict[str, Any] = field(default_factory=dict)


@dataclass
class ATCObject:
    type_name: str
    fields: dict[str, Any] = field(default_factory=dict)


class ATCVMError(Exception):
    """Base exception for deterministic reference VM execution."""


class RequireError(ATCVMError):
    """Raised when an ATCLang REQUIRE condition is false."""


class GasError(ATCVMError):
    """Raised when execution exceeds the configured gas limit."""


class ATCStdlib:
    """Pure reference primitives plus explicit fail-closed boundaries."""

    @staticmethod
    def hash_sha256(data: Any) -> str:
        raw = data if isinstance(data, bytes) else str(data).encode()
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def hash_sha3(data: Any) -> str:
        raw = data if isinstance(data, bytes) else str(data).encode()
        return hashlib.sha3_256(raw).hexdigest()

    @staticmethod
    def hash_sha3_atc(data: Any) -> str:
        raw = b"ATC_CHAIN_2026:" + (data if isinstance(data, bytes) else str(data).encode())
        return "atc1" + hashlib.sha3_256(raw).hexdigest()

    @staticmethod
    def leading_zeros(hash_str: str) -> int:
        value = hash_str.removeprefix("atc1").removeprefix("0x")
        count = 0
        for char in value:
            if char == "0":
                count += 4
            else:
                count += 4 - int(char, 16).bit_length()
                break
        return count

    @staticmethod
    def random_bytes(n: int = 32, vm_seed: Any = None) -> bytes:
        return ATCCrypto.random_bytes(n, vm_seed)

    @staticmethod
    def random_int(max_val: int, vm_seed: Any = None) -> int:
        return ATCCrypto.random_int(0, max_val - 1, vm_seed) if max_val > 0 else 0

    @staticmethod
    def rand_nonce(vm_seed: Any = None) -> int:
        return ATCCrypto.random_int(0, 2**64 - 1, vm_seed)

    @staticmethod
    def ecdsa_sign(data: Any, priv_key: Any) -> Any:
        return ecdsa_sign(data, priv_key)

    @staticmethod
    def ecdsa_verify(data: Any, sig: str, pub_key: Any) -> Any:
        return ecdsa_verify(data, sig, pub_key)

    @staticmethod
    def bip39_mnemonic(seed: bytes, word_count: int = 24) -> Any:
        return wallet_operation("bip39_mnemonic", seed, word_count)

    @staticmethod
    def generate_atc_address(pub_key_data: Any = None) -> Any:
        return wallet_operation("address_from_pubkey", pub_key_data)

    @staticmethod
    def verify_jwt(token: str) -> Any:
        return verify_jwt(token)

    @staticmethod
    def net_send(addr: str, port: int, data: Any) -> Any:
        return net_send(addr, port, data)

    @staticmethod
    def rpc_call(handler: str, request: Any) -> Any:
        return rpc_call(handler, request)

    @staticmethod
    def kademlia_find_node(*_args: Any) -> None:
        fail_closed("ATC::Net::Kademlia::find_node")

    @classmethod
    def storage_store(cls, _key: str, _value: Any) -> None:
        fail_closed("ATC::Storage::store")

    @classmethod
    def storage_load(cls, _key: str) -> None:
        fail_closed("ATC::Storage::load")

    @staticmethod
    def mem_alloc(size: int) -> bytes:
        if size < 0:
            raise ValueError("size must be non-negative")
        return bytes(size)


def _build_stdlib_dispatch() -> dict[str, Callable[..., Any]]:
    s = ATCStdlib
    return {
        "ATC::Hash::sha256": lambda a: s.hash_sha256(a[0] if a else ""),
        "ATC::Hash::sha3": lambda a: s.hash_sha3(a[0] if a else ""),
        "ATC::Hash::sha3_atc": lambda a: s.hash_sha3_atc(a[0] if a else ""),
        "ATC::Hash::leading_zeros": lambda a: s.leading_zeros(str(a[0]) if a else ""),
        "ATC::Crypto::verify_jwt": lambda a: s.verify_jwt(str(a[0]) if a else ""),
        "ATC::Crypto::ECDSA::sign": lambda a: s.ecdsa_sign(a[0] if a else "", a[1] if len(a) > 1 else ""),
        "ATC::Crypto::ECDSA::verify": lambda a: s.ecdsa_verify(a[0] if a else "", a[1] if len(a) > 1 else "", a[2] if len(a) > 2 else ""),
        "ATC::Crypto::BIP39::to_mnemonic": lambda a: s.bip39_mnemonic(a[0] if a else b"", int(a[1]) if len(a) > 1 else 24),
        "ATC::Net::UDP::send": lambda a: s.net_send(str(a[0]) if a else "", int(a[1]) if len(a) > 1 else 0, a[2] if len(a) > 2 else b""),
        "ATC::RPC::call": lambda a: s.rpc_call(str(a[0]) if a else "", a[1] if len(a) > 1 else {}),
        "ATC::Wallet::new": lambda a: wallet_operation("new", *(a or ())),
        "ATC::Crypto::sha256": lambda a: ATCCrypto.sha256(a[0]) if a else "",
        "ATC::Crypto::sha256_bytes": lambda a: ATCCrypto.sha256_bytes(a[0]) if a else b"",
        "ATC::Crypto::double_sha256": lambda a: ATCCrypto.double_sha256(a[0]) if a else "",
        "ATC::Crypto::hmac_sha256": lambda a: ATCCrypto.hmac_sha256(a[0], a[1]) if len(a) > 1 else "",
        "ATC::Crypto::base58_encode": lambda a: ATCCrypto.base58_encode(a[0]) if a else "",
        "ATC::Crypto::base58_decode": lambda a: ATCCrypto.base58_decode(a[0]) if a else b"",
        "ATC::Crypto::base64_encode": lambda a: ATCCrypto.base64_encode(a[0]) if a else "",
        "ATC::Crypto::base64_decode": lambda a: ATCCrypto.base64_decode(a[0]) if a else b"",
        "ATC::Crypto::hex_encode": lambda a: ATCCrypto.hex_encode(a[0]) if a else "",
        "ATC::Crypto::hex_decode": lambda a: ATCCrypto.hex_decode(a[0]) if a else b"",
        "ATC::Crypto::generate_keypair": lambda a: ATCCrypto.generate_keypair(a[0] if a else None),
        "ATC::Crypto::sign": lambda a: ATCCrypto.sign(a[0], a[1]) if len(a) > 1 else fail_closed("ATC::Crypto::sign"),
        "ATC::Crypto::verify": lambda a: ATCCrypto.verify(a[0], a[1], a[2]) if len(a) > 2 else fail_closed("ATC::Crypto::verify"),
        "ATC::Crypto::random_bytes": lambda a: ATCCrypto.random_bytes(int(a[0]), a[1]) if len(a) > 1 else fail_closed("ATC::Crypto::random_bytes"),
        "ATC::Crypto::random_int": lambda a: ATCCrypto.random_int(int(a[0]), int(a[1]), a[2]) if len(a) > 2 else fail_closed("ATC::Crypto::random_int"),
        "ATC::Crypto::address_from_pubkey": lambda a: ATCCrypto.address_from_pubkey(a[0]) if a else fail_closed("ATC::Crypto::address_from_pubkey"),
        "ATC::Crypto::is_valid_address": lambda a: ATCCrypto.is_valid_address(a[0]) if a else False,
        "ATC::Collections::map_new": lambda a: ATCCollections.map_new(),
        "ATC::Collections::map_get": lambda a: ATCCollections.map_get(a[0], a[1]) if len(a) > 1 else None,
        "ATC::Collections::map_set": lambda a: ATCCollections.map_set(a[0], a[1], a[2]) if len(a) > 2 else {},
        "ATC::Collections::map_contains": lambda a: ATCCollections.map_contains(a[0], a[1]) if len(a) > 1 else False,
        "ATC::Collections::map_keys": lambda a: ATCCollections.map_keys(a[0]) if a else [],
        "ATC::Collections::map_values": lambda a: ATCCollections.map_values(a[0]) if a else [],
        "ATC::Collections::map_size": lambda a: ATCCollections.map_size(a[0]) if a else 0,
        "ATC::Encoding::json_encode": lambda a: ATCEncoding.json_encode(a[0]) if a else "",
        "ATC::Encoding::json_decode": lambda a: ATCEncoding.json_decode(a[0]) if a else None,
        "ATC::Math::add": lambda a: ATCMath.add(a[0], a[1]) if len(a) > 1 else 0,
        "ATC::Math::sub": lambda a: ATCMath.sub(a[0], a[1]) if len(a) > 1 else 0,
        "ATC::Math::mul": lambda a: ATCMath.mul(a[0], a[1]) if len(a) > 1 else 0,
        "ATC::Math::div": lambda a: ATCMath.div(a[0], a[1]) if len(a) > 1 else 0,
    }


STDLIB_DISPATCH = _build_stdlib_dispatch()


class ATCVM:
    """Deterministic reference interpreter with fail-closed host boundaries."""

    def __init__(self, gas_limit: int = 10_000_000, block_timestamp: int = 0, caller: str = "", vm_seed: Any = None):
        if block_timestamp < 0:
            raise ValueError("block_timestamp must be non-negative")
        self.stack: list[Any] = []
        self.globals: dict[str, Any] = {
            "caller": caller,
            "block": {"timestamp": block_timestamp, "number": 0, "hash": self._hash("genesis")},
            "tx": {"hash": self._hash("tx0"), "origin": caller},
            "now": block_timestamp,
            "true": True,
            "false": False,
            "null": None,
        }
        self.vm_seed = vm_seed
        self.functions: dict[str, ATCFunction] = {}
        self.call_stack: list[CallFrame] = []
        self.events: list[dict[str, Any]] = []
        self.logs: list[str] = []
        self.gas_used = 0
        self.gas_limit = gas_limit

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha3_256(value.encode()).hexdigest()

    def push(self, value: Any) -> None:
        self.stack.append(value)

    def pop(self) -> Any:
        if not self.stack:
            raise ATCVMError("Stack underflow")
        return self.stack.pop()

    def peek(self) -> Any:
        if not self.stack:
            raise ATCVMError("Stack leer")
        return self.stack[-1]

    def gas(self, cost: int = 1) -> None:
        if cost < 0:
            raise ValueError("gas cost must be non-negative")
        self.gas_used += cost
        if self.gas_used > self.gas_limit:
            raise GasError(f"Gas-Limit {self.gas_limit} überschritten")

    def get_var(self, name: str, frame: CallFrame | None) -> Any:
        if frame and name in frame.locals:
            return frame.locals[name]
        return self.globals.get(name)

    def set_var(self, name: str, value: Any, frame: CallFrame | None) -> None:
        if frame:
            frame.locals[name] = value
        else:
            self.globals[name] = value
