# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""ATCLang ABI Codec — kanonische Kodierung von Argument- und Rückgabewerten.

Wire-Format (big-endian, deterministisch, 32-Byte-Ausrichtung wie ATC-8300):
- UInt/Int (U8..U256/I256): vorzeichenbehaftete/notierte Ganzzahl, rechts-
  gepolstert in 32 Bytes (U8/U16/U32/U64 links mit 0x00, I256 two's complement)
- Bool: 32 Bytes 0/1 · Address: 20 Bytes rechtsbündig in 32 Bytes
- Bytes32/Bytes64: fixe Länge · String: dynamisch, Längen-Präfix-Head + Payload
- Vec<T>/Map: Längen-Head + Elemente (rekursiv kanonisch)
- Selektor: sha3-256(canonical_signature)[0:4] — 4 Bytes, hex-präfixiert "0x"
"""
from __future__ import annotations
import hashlib
from typing import Any, List, Sequence, Tuple

_U = {"UInt8": 1, "UInt16": 2, "UInt32": 4, "UInt64": 8, "UInt128": 16, "UInt256": 32}


class ABIError(Exception):
    """ABI-Kodierungs-/Dekodierungsfehler."""


def canonical_signature(name: str, params: Sequence[str]) -> str:
    """fn transfer(to: Address, amount: UInt256) -> 'transfer(Address,UInt256)'."""
    return f"{name}({','.join(p.strip() for p in params)})"


def method_selector(name: str, params: Sequence[str]) -> str:
    """4-Byte-Methoden-ID aus SHA3-256 der kanonischen Signatur (hex 0x…)."""
    sig = canonical_signature(name, params)
    digest = hashlib.sha3_256(sig.encode("utf-8")).digest()
    return "0x" + digest[:4].hex()


class ABICodec:
    """Kanonischer Wert-Codec für ATCLang-ABI-Typen (ATC-8300-kompatibel)."""

    # ---- encode ----
    def encode(self, value: Any, abi_type: str) -> bytes:
        if abi_type in _U:
            return self._enc_uint(int(value), _U[abi_type])
        if abi_type == "Int256":
            return self._enc_int256(int(value))
        if abi_type == "Bool":
            return self._enc_uint(1 if value else 0, 1)
        if abi_type == "Address":
            return self._enc_address(value)
        if abi_type == "Bytes32":
            return bytes(value)
        if abi_type == "Bytes64":
            return bytes(value)
        if abi_type == "String":
            data = value.encode("utf-8")
            return self._head(len(data)) + data
        if abi_type.startswith("Vec["):
            inner = abi_type[4:-1]
            items = b"".join(self.encode(v, inner) for v in value)
            return self._head(len(value)) + items
        if abi_type.startswith("Map["):
            _, vtype = self._split_map(abi_type)
            # deterministisch: sortierte Key-Reihenfolge
            pairs = sorted(value.items()) if hasattr(value, "items") else value
            body = b""
            for k, v in pairs:
                body += self.encode(k, "String") + self.encode(v, vtype)
            return self._head(len(pairs)) + body
        raise ABIError(f"Unbekannter ABI-Typ: {abi_type!r}")

    def encode_call(self, selector: str, values: Sequence[Any], abi_types: Sequence[str]) -> bytes:
        """Call-Payload = Selektor || kanonisch verkettete Argumente."""
        if len(values) != len(abi_types):
            raise ABIError("Argument-/Typenanzahl stimmt nicht ueberein")
        sel = bytes.fromhex(selector[2:] if selector.startswith("0x") else selector)
        if len(sel) != 4:
            raise ABIError("Selektor muss 4 Bytes sein")
        return sel + b"".join(self.encode(v, t) for v, t in zip(values, abi_types))

    # ---- decode ----
    def decode(self, data: bytes, abi_type: str, offset: int = 0) -> Tuple[Any, int]:
        if abi_type in _U:
            width = _U[abi_type]
            return int.from_bytes(data[offset:offset + 32][32 - width:], "big"), offset + 32
        if abi_type == "Int256":
            raw = data[offset:offset + 32]
            val = int.from_bytes(raw, "big", signed=True)
            return val, offset + 32
        if abi_type == "Bool":
            return int.from_bytes(data[offset:offset + 32], "big") == 1, offset + 32
        if abi_type == "Address":
            raw = data[offset:offset + 32]
            return "0x" + raw[12:].hex(), offset + 32
        if abi_type in ("Bytes32",):
            return bytes(data[offset:offset + 32]), offset + 32
        if abi_type in ("Bytes64",):
            return bytes(data[offset:offset + 64]), offset + 64
        if abi_type == "String":
            ln = int.from_bytes(data[offset:offset + 32], "big")
            body = data[offset + 32:offset + 32 + ln]
            return body.decode("utf-8"), offset + 32 + ln
        if abi_type.startswith("Vec["):
            inner = abi_type[4:-1]
            ln = int.from_bytes(data[offset:offset + 32], "big")
            off = offset + 32
            out: List[Any] = []
            for _ in range(ln):
                v, off = self.decode(data, inner, off)
                out.append(v)
            return out, off
        if abi_type.startswith("Map["):
            _, vtype = self._split_map(abi_type)
            ln = int.from_bytes(data[offset:offset + 32], "big")
            off = offset + 32
            out = {}
            for _ in range(ln):
                k, off = self.decode(data, "String", off)
                v, off = self.decode(data, vtype, off)
                out[k] = v
            return out, off
        raise ABIError(f"Unbekannter ABI-Typ: {abi_type!r}")

    # ---- Helfer ----
    @staticmethod
    def _head(n: int) -> bytes:
        return n.to_bytes(32, "big")

    @staticmethod
    def _split_map(t: str) -> Tuple[str, str]:
        inner = t[4:-1]
        parts = inner.split(",", 1)
        return parts[0].strip(), parts[1].strip()

    @staticmethod
    def _enc_uint(v: int, width: int) -> bytes:
        if v < 0:
            raise ABIError("Unsigned-Typ mit negativem Wert")
        raw = v.to_bytes(32, "big")
        if raw[:32 - width] != b"\x00" * (32 - width):
            raise ABIError(f"Wert {v} ueberschreitet {width}-Byte-Breite")
        return raw

    @staticmethod
    def _enc_int256(v: int) -> bytes:
        return int(v).to_bytes(32, "big", signed=True)

    @staticmethod
    def _enc_address(a: Any) -> bytes:
        if isinstance(a, str):
            a = a[2:] if a.startswith("0x") else a
            a = bytes.fromhex(a)
        a = bytes(a)
        if len(a) != 20:
            raise ABIError("Address muss 20 Bytes sein")
        return b"\x00" * 12 + a
