# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""ATCLang Standard Library — Pure Python implementations."""
import hashlib
import json
import math
from typing import Any, List, Dict, Optional


class ATCCollections:
    """ATC collection utilities."""

    @staticmethod
    def map(fn, lst: List) -> List:
        return [fn(x) for x in lst]

    @staticmethod
    def filter(pred, lst: List) -> List:
        return [x for x in lst if pred(x)]

    @staticmethod
    def reduce(fn, lst: List, init: Any = 0) -> Any:
        result = init
        for x in lst:
            result = fn(result, x)
        return result

    @staticmethod
    def sort(lst: List, key=None, reverse: bool = False) -> List:
        return sorted(lst, key=key, reverse=reverse)

    @staticmethod
    def unique(lst: List) -> List:
        seen = set()
        result = []
        for x in lst:
            if x not in seen:
                seen.add(x)
                result.append(x)
        return result


class ATCMath:
    """ATC math functions."""

    @staticmethod
    def factorial(n: int) -> int:
        return math.factorial(n) if n >= 0 else 0

    @staticmethod
    def fibonacci(n: int) -> int:
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a

    @staticmethod
    def is_prime(n: int) -> bool:
        if n < 2: return False
        for i in range(2, int(n**0.5) + 1):
            if n % i == 0: return False
        return True

    @staticmethod
    def gcd(a: int, b: int) -> int:
        while b: a, b = b, a % b
        return abs(a)

    @staticmethod
    def power(base: int, exp: int) -> int:
        return base ** exp


class ATCCrypto:
    """ATC crypto utilities."""

    @staticmethod
    def hash(data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def hash_file(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def merkle_root(hashes: List[str]) -> str:
        if not hashes: return ""
        if len(hashes) == 1: return hashes[0]
        if len(hashes) % 2 == 1: hashes.append(hashes[-1])
        next_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            next_level.append(hashlib.sha256(combined.encode()).hexdigest())
        return ATCCrypto.merkle_root(next_level)


class ATCIO:
    """ATC I/O utilities."""

    @staticmethod
    def read_json(path: str) -> Any:
        with open(path, 'r') as f:
            return json.load(f)

    @staticmethod
    def write_json(path: str, data: Any) -> None:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def serialize(obj: Any) -> str:
        return json.dumps(obj, sort_keys=True)

    @staticmethod
    def deserialize(data: str) -> Any:
        return json.loads(data)


class ATCNet:
    """ATC networking utilities."""

    @staticmethod
    def format_message(msg_type: str, payload: Any) -> bytes:
        return json.dumps({"type": msg_type, "payload": payload}).encode()

    @staticmethod
    def parse_message(data: bytes) -> Dict:
        return json.loads(data.decode())
