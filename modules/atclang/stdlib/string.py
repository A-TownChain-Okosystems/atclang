# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Standard Library — String Module v1.0
Erweiterte String-Operationen für ATCLang.
Standard: ATC-94
"""

class ATCString:
    """Erweiterte String-Operationen."""

    @staticmethod
    def len(s: str) -> int:
        return len(s)

    @staticmethod
    def upper(s: str) -> str:
        return s.upper()

    @staticmethod
    def lower(s: str) -> str:
        return s.lower()

    @staticmethod
    def split(s: str, delim: str = " ") -> list:
        return s.split(delim)

    @staticmethod
    def join(parts: list, delim: str = " ") -> str:
        return delim.join(str(p) for p in parts)

    @staticmethod
    def format(template: str, **kwargs) -> str:
        return template.format(**kwargs)

    @staticmethod
    def trim(s: str) -> str:
        return s.strip()

    @staticmethod
    def trim_left(s: str) -> str:
        return s.lstrip()

    @staticmethod
    def trim_right(s: str) -> str:
        return s.rstrip()

    @staticmethod
    def starts_with(s: str, prefix: str) -> bool:
        return s.startswith(prefix)

    @staticmethod
    def ends_with(s: str, suffix: str) -> bool:
        return s.endswith(suffix)

    @staticmethod
    def contains(s: str, substr: str) -> bool:
        return substr in s

    @staticmethod
    def replace(s: str, old: str, new: str) -> str:
        return s.replace(old, new)

    @staticmethod
    def repeat(s: str, n: int) -> str:
        return s * n

    @staticmethod
    def reverse(s: str) -> str:
        return s[::-1]

    @staticmethod
    def slice(s: str, start: int, end: int = None) -> str:
        if end is None:
            return s[start:]
        return s[start:end]

    @staticmethod
    def to_bytes(s: str) -> bytes:
        return s.encode("utf-8")

    @staticmethod
    def from_bytes(b: bytes) -> str:
        return b.decode("utf-8")

    @staticmethod
    def pad_left(s: str, width: int, pad: str = " ") -> str:
        return s.rjust(width, pad)

    @staticmethod
    def pad_right(s: str, width: int, pad: str = " ") -> str:
        return s.ljust(width, pad)

    @staticmethod
    def to_hex(s: str) -> str:
        return s.encode("utf-8").hex()

    @staticmethod
    def from_hex(h: str) -> str:
        return bytes.fromhex(h).decode("utf-8")
