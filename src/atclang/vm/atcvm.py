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

from atclang.security.reference_boundary import (
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

    def _call_method(self, obj: Any, method: str, args: list[Any]) -> Any:
        if isinstance(obj, dict):
            if method == "get":
                return obj.get(args[0], args[1] if len(args) > 1 else None)
            if method == "keys":
                return list(obj.keys())
            if method == "values":
                return list(obj.values())
            if method == "items":
                return list(obj.items())
            if method == "length":
                return len(obj)
        if isinstance(obj, list):
            if method == "push":
                obj.append(args[0])
                return obj
            if method == "pop":
                return obj.pop() if obj else None
            if method == "length":
                return len(obj)
            if method == "contains":
                return args[0] in obj
        if isinstance(obj, str):
            if method == "length":
                return len(obj)
            if method == "upper":
                return obj.upper()
            if method == "lower":
                return obj.lower()
            if method == "contains":
                return args[0] in obj
            if method == "split":
                return obj.split(args[0] if args else None)
        if isinstance(obj, (int, float)) and method == "to_string":
            return str(obj)
        if isinstance(obj, bytes) and method == "length":
            return len(obj)
        if isinstance(obj, ATCObject):
            return obj.fields.get(method)
        return None

    def execute(self, instructions: list[Instruction], frame: CallFrame | None = None) -> Any:
        ip = 0
        while ip < len(instructions):
            instr = instructions[ip]
            self.gas()
            op, args = instr.op, instr.args

            if op == OP.NOP:
                pass
            elif op == OP.HALT:
                break
            elif op == OP.PUSH:
                self.push(args[0])
            elif op == OP.POP:
                self.pop()
            elif op == OP.DUP:
                self.push(self.peek())
            elif op == OP.SWAP:
                first, second = self.pop(), self.pop()
                self.push(first)
                self.push(second)
            elif op == OP.ROT:
                first, second, third = self.pop(), self.pop(), self.pop()
                self.push(first)
                self.push(third)
                self.push(second)
            elif op == OP.ADD:
                right, left = self.pop(), self.pop()
                self.push(left + right if isinstance(left, (int, float)) else str(left) + str(right))
            elif op in {OP.SUB, OP.MUL, OP.POW, OP.BITAND, OP.BITOR, OP.BITXOR, OP.SHL, OP.SHR}:
                right, left = self.pop(), self.pop()
                operations = {
                    OP.SUB: lambda: left - right,
                    OP.MUL: lambda: left * right,
                    OP.POW: lambda: left**right,
                    OP.BITAND: lambda: int(left) & int(right),
                    OP.BITOR: lambda: int(left) | int(right),
                    OP.BITXOR: lambda: int(left) ^ int(right),
                    OP.SHL: lambda: int(left) << int(right),
                    OP.SHR: lambda: int(left) >> int(right),
                }
                self.push(operations[op]())
            elif op == OP.DIV:
                right, left = self.pop(), self.pop()
                if right == 0:
                    raise ATCVMError("Division durch Null")
                self.push(left // right)
            elif op == OP.MOD:
                right, left = self.pop(), self.pop()
                if right == 0:
                    raise ATCVMError("Modulo durch Null")
                self.push(left % right)
            elif op == OP.NEG:
                self.push(-self.pop())
            elif op == OP.BITNOT:
                self.push(~int(self.pop()))
            elif op in {OP.EQ, OP.NEQ, OP.LT, OP.GT, OP.LTE, OP.GTE}:
                right, left = self.pop(), self.pop()
                self.push({
                    OP.EQ: left == right,
                    OP.NEQ: left != right,
                    OP.LT: left < right,
                    OP.GT: left > right,
                    OP.LTE: left <= right,
                    OP.GTE: left >= right,
                }[op])
            elif op in {OP.AND, OP.OR}:
                right, left = self.pop(), self.pop()
                self.push(bool(left) and bool(right) if op == OP.AND else bool(left) or bool(right))
            elif op == OP.NOT:
                self.push(not self.pop())
            elif op == OP.LOAD:
                self.push(self.get_var(args[0], frame))
            elif op == OP.STORE:
                self.set_var(args[0], self.pop(), frame)
            elif op == OP.LOAD_GLOBAL:
                self.push(self.globals.get(args[0]))
            elif op == OP.STORE_GLOBAL:
                self.globals[args[0]] = self.pop()
            elif op == OP.LOAD_IDX:
                key, obj = self.pop(), self.pop()
                self.push(obj[key])
            elif op == OP.STORE_IDX:
                key, obj, value = self.pop(), self.pop(), self.pop()
                obj[key] = value
                self.push(obj)
            elif op == OP.DEL_VAR:
                self.globals.pop(args[0], None)
            elif op in {OP.JUMP, OP.JUMP_IF, OP.JUMP_NOT}:
                should_jump = op == OP.JUMP or (op == OP.JUMP_IF and bool(self.pop())) or (op == OP.JUMP_NOT and not bool(self.pop()))
                if should_jump:
                    ip = args[0]
                    continue
            elif op == OP.CALL:
                name = args[0]
                argc = args[1] if len(args) > 1 else 0
                call_args = [self.pop() for _ in range(argc)][::-1]
                function = self.functions.get(name)
                if function is None:
                    raise ATCVMError(f"Unknown function: {name}")
                new_frame = CallFrame(name, locals=dict(zip(function.params, call_args)))
                self.push(self.execute(function.instructions, new_frame))
            elif op == OP.CALL_EXT:
                name = args[0]
                argc = args[1] if len(args) > 1 else 0
                call_args = [self.pop() for _ in range(argc)][::-1]
                handler = STDLIB_DISPATCH.get(name)
                if handler is None:
                    raise ATCVMError(f"Unknown ATC namespace: {name}")
                self.push(handler(call_args))
            elif op == OP.CALL_METHOD:
                name = args[0]
                argc = args[1] if len(args) > 1 else 0
                call_args = [self.pop() for _ in range(argc)][::-1]
                self.push(self._call_method(self.pop(), name, call_args))
            elif op == OP.RETURN:
                return self.pop() if self.stack else None
            elif op == OP.NEW_MAP:
                self.push({})
            elif op == OP.NEW_LIST:
                self.push([])
            elif op == OP.NEW_OBJ:
                self.push(ATCObject(args[0] if args else "Object"))
            elif op == OP.GET_FIELD:
                obj = self.pop()
                key = args[0]
                self.push(obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None))
            elif op == OP.SET_FIELD:
                value, obj = self.pop(), self.pop()
                key = args[0]
                if isinstance(obj, dict):
                    obj[key] = value
                else:
                    setattr(obj, key, value)
                self.push(obj)
            elif op == OP.HAS_KEY:
                key, obj = self.pop(), self.pop()
                self.push(key in obj)
            elif op == OP.DEL_KEY:
                key, obj = self.pop(), self.pop()
                obj.pop(key, None)
                self.push(obj)
            elif op == OP.LIST_PUSH:
                value, obj = self.pop(), self.pop()
                obj.append(value)
                self.push(obj)
            elif op == OP.LIST_POP:
                self.push(self.pop().pop())
            elif op == OP.LIST_LEN:
                self.push(len(self.pop()))
            elif op == OP.MAP_KEYS:
                self.push(list(self.pop().keys()))
            elif op == OP.MAP_VALUES:
                self.push(list(self.pop().values()))
            elif op == OP.MAP_ITEMS:
                self.push(list(self.pop().items()))
            elif op == OP.CONTAINS:
                item, obj = self.pop(), self.pop()
                self.push(item in obj)
            elif op == OP.CAST:
                value = self.pop()
                target = args[0]
                if target == "String":
                    value = str(value)
                elif target in {"Int", "UInt32", "UInt64", "UInt256"}:
                    value = int(value)
                elif target == "Bool":
                    value = bool(value)
                self.push(value)
            elif op == OP.STR_LEN:
                self.push(len(str(self.pop())))
            elif op == OP.STR_UPPER:
                self.push(str(self.pop()).upper())
            elif op == OP.STR_LOWER:
                self.push(str(self.pop()).lower())
            elif op == OP.STR_SLICE:
                end, start, value = self.pop(), self.pop(), self.pop()
                self.push(str(value)[start:end])
            elif op == OP.STR_SPLIT:
                sep, value = self.pop(), self.pop()
                self.push(str(value).split(str(sep)))
            elif op == OP.STR_JOIN:
                values, sep = self.pop(), self.pop()
                self.push(str(sep).join(map(str, values)))
            elif op == OP.STR_FORMAT:
                self.push(str(self.pop()))
            elif op == OP.EMIT:
                argc = args[1] if len(args) > 1 else 0
                self.events.append({"event": args[0], "args": [self.pop() for _ in range(argc)][::-1]})
            elif op == OP.REQUIRE:
                if not self.pop():
                    raise RequireError(args[0] if args else "Require fehlgeschlagen")
            elif op in {
                OP.TRANSFER,
                OP.MINT,
                OP.BURN,
                OP.STAKE,
                OP.UNSTAKE,
                OP.VOTE,
                OP.NET_RECV,
                OP.NET_BROADCAST,
                OP.NET_CONNECT,
                OP.NET_PEERS,
                OP.FS_WRITE,
                OP.FS_READ,
                OP.FS_MKDIR,
                OP.ASYNC_CALL,
                OP.AWAIT,
                OP.SPAWN,
                OP.CHANNEL_SEND,
                OP.CHANNEL_RECV,
            }:
                fail_closed(f"ATC::VM::{op.name}")
            elif op == OP.HASH_SHA256:
                self.push(ATCStdlib.hash_sha256(self.pop()))
            elif op == OP.HASH_SHA3:
                self.push(ATCStdlib.hash_sha3(self.pop()))
            elif op == OP.HASH_SHA3_ATC:
                self.push(ATCStdlib.hash_sha3_atc(self.pop()))
            elif op == OP.CRYPTO_SIGN:
                key, data = self.pop(), self.pop()
                self.push(ecdsa_sign(data, key))
            elif op == OP.CRYPTO_VERIFY:
                pub, sig, data = self.pop(), self.pop(), self.pop()
                self.push(ecdsa_verify(data, sig, pub))
            elif op in {OP.RAND_BYTES, OP.RAND_INT}:
                fail_closed(f"ATC::VM::{op.name}")
            elif op == OP.LEADING_ZEROS:
                self.push(ATCStdlib.leading_zeros(str(self.pop())))
            elif op == OP.NET_SEND:
                fail_closed("ATC::Net::send")
            elif op == OP.STORE_PERSIST:
                fail_closed("ATC::Storage::store")
            elif op == OP.LOAD_PERSIST:
                fail_closed("ATC::Storage::load")
            elif op == OP.PRINT:
                self.pop()
            elif op == OP.LOG:
                self.logs.append(str(self.pop()))
            elif op == OP.DEBUG:
                self.logs.append(f"stack={self.stack[-5:]}")
            elif op == OP.GAS_CHECK:
                self.push(self.gas_used)
            elif op == OP.TIMESTAMP:
                self.push(self.globals["block"]["timestamp"])
            elif op == OP.BLOCK_NUM:
                self.push(self.globals["block"]["number"])
            elif op == OP.CALLER:
                self.push(self.globals["caller"])
            elif op == OP.ASSERT:
                if not self.pop():
                    raise ATCVMError(args[0] if args else "Assertion fehlgeschlagen")
            else:
                raise ATCVMError(f"Unsupported opcode: {op.name}")
            ip += 1
        return self.pop() if self.stack else None

    def run_program(self, instructions: list[Instruction]) -> Any:
        return self.execute(instructions)

    def register_function(self, function: ATCFunction) -> None:
        self.functions[function.name] = function

    def get_events(self) -> list[dict[str, Any]]:
        return list(self.events)

    def stats(self) -> dict[str, int]:
        return {
            "gas_used": self.gas_used,
            "gas_limit": self.gas_limit,
            "stack_size": len(self.stack),
            "events": len(self.events),
            "logs": len(self.logs),
            "functions": len(self.functions),
        }
