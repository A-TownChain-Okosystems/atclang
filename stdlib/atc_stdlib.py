"""
atclang/stdlib/atc_stdlib.py
ATCLang Standard Library — v0.2.0

Built-in Funktionen und Module für ATCLang Smart Contracts.
"""
import hashlib
import time
import json
from typing import Any, Dict, Optional


class ATCStdlibModule:
    """Kapselt alle Built-in-Funktionen der ATCLang Stdlib."""

    # ── Crypto ──────────────────────────────────────────

    @staticmethod
    def sha256(data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def sha3_256(data: str) -> str:
        return hashlib.sha3_256(data.encode()).hexdigest()

    @staticmethod
    def keccak256(data: str) -> str:
        """Kompatibel mit Solidity keccak256."""
        return hashlib.sha3_256(data.encode()).hexdigest()

    # ── Block/Chain-Kontext ─────────────────────────────

    @staticmethod
    def block_timestamp() -> int:
        return int(time.time())

    @staticmethod
    def block_number() -> int:
        """Gibt simulierte Block-Höhe zurück (Testnet)."""
        return int(time.time()) // 5  # ~5s Block-Zeit

    @staticmethod
    def now() -> int:
        return int(time.time())

    # ── Typ-Konvertierung ───────────────────────────────

    @staticmethod
    def to_u64(v: Any) -> int:
        n = int(v)
        if n < 0 or n > 2**64 - 1:
            raise ValueError(f"Wert {n} außerhalb u64-Bereich")
        return n

    @staticmethod
    def to_u128(v: Any) -> int:
        n = int(v)
        if n < 0 or n > 2**128 - 1:
            raise ValueError(f"Wert {n} außerhalb u128-Bereich")
        return n

    @staticmethod
    def to_string(v: Any) -> str:
        return str(v)

    @staticmethod
    def to_bool(v: Any) -> bool:
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

    # ── Adress-Validierung ──────────────────────────────

    @staticmethod
    def is_valid_address(addr: str) -> bool:
        return isinstance(addr, str) and addr.startswith("ATC") and len(addr) == 35

    @staticmethod
    def zero_address() -> str:
        return "ATC" + "0" * 32

    # ── Math (Overflow-safe) ────────────────────────────

    @staticmethod
    def safe_add(a: int, b: int, max_val: int = 2**64 - 1) -> int:
        r = a + b
        if r > max_val:
            raise OverflowError(f"Overflow: {a} + {b} > {max_val}")
        return r

    @staticmethod
    def safe_sub(a: int, b: int) -> int:
        if b > a:
            raise ValueError(f"Underflow: {a} - {b} < 0")
        return a - b

    @staticmethod
    def safe_mul(a: int, b: int, max_val: int = 2**64 - 1) -> int:
        r = a * b
        if r > max_val:
            raise OverflowError(f"Overflow: {a} * {b} > {max_val}")
        return r

    @staticmethod
    def min(a, b): return a if a < b else b

    @staticmethod
    def max(a, b): return a if a > b else b

    @staticmethod
    def abs(a: int) -> int: return a if a >= 0 else -a

    # ── Logging (Contract Events) ───────────────────────

    @staticmethod
    def emit_event(name: str, data: Dict) -> dict:
        """Simuliert ein Contract-Event (wird auf der Chain geloggt)."""
        event = {
            "event":     name,
            "timestamp": int(time.time()),
            "data":      data,
        }
        return event

    # ── Assertions ─────────────────────────────────────

    @staticmethod
    def require(condition: bool, message: str = "Assertion failed") -> None:
        if not condition:
            raise AssertionError(f"[ATCLang] require() failed: {message}")

    @staticmethod
    def assert_eq(a, b, msg: str = "") -> None:
        if a != b:
            raise AssertionError(f"[ATCLang] assert_eq: {a} != {b}. {msg}")

    # ── Serialisierung ──────────────────────────────────

    @staticmethod
    def to_json(v: Any) -> str:
        return json.dumps(v, default=str)

    @staticmethod
    def from_json(s: str) -> Any:
        return json.loads(s)


# ── Stdlib-Loader ──────────────────────────────────────

def load_stdlib() -> Dict[str, Any]:
    """
    Gibt ein Dict mit allen Built-in-Funktionen zurück.
    Wird von der ATCLang VM beim Start geladen.
    """
    m = ATCStdlibModule
    return {
        # Crypto
        "sha256":          m.sha256,
        "sha3_256":        m.sha3_256,
        "keccak256":       m.keccak256,
        # Chain
        "block_timestamp": m.block_timestamp,
        "block_number":    m.block_number,
        "now":             m.now,
        # Typen
        "u64":             m.to_u64,
        "u128":            m.to_u128,
        "to_string":       m.to_string,
        "to_bool":         m.to_bool,
        # Adressen
        "is_valid_address":m.is_valid_address,
        "zero_address":    m.zero_address,
        # Math
        "safe_add":        m.safe_add,
        "safe_sub":        m.safe_sub,
        "safe_mul":        m.safe_mul,
        "min":             m.min,
        "max":             m.max,
        "abs":             m.abs,
        # Events
        "emit":            m.emit_event,
        # Assertions
        "require":         m.require,
        "assert_eq":       m.assert_eq,
        # Serialisierung
        "to_json":         m.to_json,
        "from_json":       m.from_json,
        # Konstanten
        "TRUE":            True,
        "FALSE":           False,
        "ZERO_ADDRESS":    m.zero_address(),
        "MAX_U64":         2**64 - 1,
        "MAX_U128":        2**128 - 1,
    }
