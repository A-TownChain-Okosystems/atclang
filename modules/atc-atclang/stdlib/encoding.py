# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Stdlib — ATC::Encoding
Serialisierung und Encoding für ATCLang.
ATC-94 | Sprint 2.5 | Non-EVM: JSON + CBOR, RLP deprecated
"""
import json
import struct
from typing import Any, Dict, List, Union


class ATCEncoding:
    """ATC::Encoding — JSON, CBOR, Hex, Base58, Base64."""

    # ── JSON ─────────────────────────────────────

    @staticmethod
    def json_encode(obj: Any) -> str:
        """Encode object to JSON string. Gas: 15"""
        return json.dumps(obj, default=str, sort_keys=True)

    @staticmethod
    def json_decode(s: str) -> Any:
        """Decode JSON string to object. Gas: 15"""
        return json.loads(s)

    # ── CBOR (Concise Binary Object Representation) ──

    @staticmethod
    def cbor_encode(obj: Any) -> bytes:
        """Encode to CBOR bytes. Gas: 20"""
        return ATCEncoding._cbor_write(obj)

    @staticmethod
    def cbor_decode(data: bytes) -> Any:
        """Decode CBOR bytes. Gas: 20"""
        value, offset = ATCEncoding._cbor_read(data, 0)
        return value

    @staticmethod
    def _cbor_write(obj: Any) -> bytes:
        """Internal CBOR encoder."""
        if obj is None:
            return b'\xf6'
        elif obj is True:
            return b'\xf5'
        elif obj is False:
            return b'\xf4'
        elif isinstance(obj, int):
            if 0 <= obj <= 23:
                return bytes([obj])
            elif 24 <= obj <= 255:
                return bytes([24, obj])
            elif 256 <= obj <= 65535:
                return bytes([25]) + struct.pack('>H', obj)
            elif 65536 <= obj <= 4294967295:
                return bytes([26]) + struct.pack('>I', obj)
            else:
                return bytes([27]) + struct.pack('>Q', obj)
        elif isinstance(obj, str):
            encoded = obj.encode('utf-8')
            length = len(encoded)
            if length <= 23:
                return bytes([0x60 + length]) + encoded
            elif length <= 255:
                return bytes([0x78, length]) + encoded
            else:
                return bytes([0x79]) + struct.pack('>H', length) + encoded
        elif isinstance(obj, bytes):
            length = len(obj)
            if length <= 23:
                return bytes([0x40 + length]) + obj
            elif length <= 255:
                return bytes([0x58, length]) + obj
            else:
                return bytes([0x59]) + struct.pack('>H', length) + obj
        elif isinstance(obj, list):
            length = len(obj)
            if length <= 23:
                header = bytes([0x80 + length])
            else:
                header = bytes([0x9f])  # indefinite
            result = header
            for item in obj:
                result += ATCEncoding._cbor_write(item)
            if length > 23:
                result += b'\xff'  # break
            return result
        elif isinstance(obj, dict):
            length = len(obj)
            if length <= 23:
                header = bytes([0xa0 + length])
            else:
                header = bytes([0xbf])  # indefinite
            result = header
            for k, v in obj.items():
                result += ATCEncoding._cbor_write(str(k))
                result += ATCEncoding._cbor_write(v)
            if length > 23:
                result += b'\xff'  # break
            return result
        return b'\xf6'  # null fallback

    @staticmethod
    def _cbor_read(data: bytes, offset: int) -> tuple:
        """Internal CBOR decoder."""
        if offset >= len(data):
            return (None, offset)
        b = data[offset]
        major = b >> 5
        minor = b & 0x1f
        offset += 1

        if major == 0:  # unsigned int
            if minor <= 23:
                return (minor, offset)
            elif minor == 24:
                return (data[offset], offset + 1)
            elif minor == 25:
                return (struct.unpack('>H', data[offset:offset+2])[0], offset + 2)
            elif minor == 26:
                return (struct.unpack('>I', data[offset:offset+4])[0], offset + 4)
            elif minor == 27:
                return (struct.unpack('>Q', data[offset:offset+8])[0], offset + 8)
        elif major == 2:  # bytes
            length = minor
            if minor > 23:
                length = struct.unpack('>H', data[offset:offset+2])[0]
                offset += 2
            return (data[offset:offset+length], offset + length)
        elif major == 3:  # string
            length = minor
            if minor > 23:
                length = struct.unpack('>H', data[offset:offset+2])[0]
                offset += 2
            return (data[offset:offset+length].decode('utf-8'), offset + length)
        elif major == 4:  # array
            items = []
            if minor == 0x1f:  # indefinite
                while offset < len(data) and data[offset] != 0xff:
                    val, offset = ATCEncoding._cbor_read(data, offset)
                    items.append(val)
                offset += 1  # skip break
            else:
                for _ in range(minor):
                    val, offset = ATCEncoding._cbor_read(data, offset)
                    items.append(val)
            return (items, offset)
        elif major == 5:  # map
            obj = {}
            if minor == 0x1f:
                while offset < len(data) and data[offset] != 0xff:
                    k, offset = ATCEncoding._cbor_read(data, offset)
                    v, offset = ATCEncoding._cbor_read(data, offset)
                    obj[str(k)] = v
                offset += 1
            else:
                for _ in range(minor):
                    k, offset = ATCEncoding._cbor_read(data, offset)
                    v, offset = ATCEncoding._cbor_read(data, offset)
                    obj[str(k)] = v
            return (obj, offset)
        elif major == 7:  # special
            if minor == 20:
                return (False, offset)
            elif minor == 21:
                return (True, offset)
            elif minor == 22:
                return (None, offset)
        return (None, offset)

    # ── Hex ──────────────────────────────────────

    @staticmethod
    def hex_encode(data: bytes) -> str:
        """Bytes to hex string. Gas: 10"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return data.hex()

    @staticmethod
    def hex_decode(s: str) -> bytes:
        """Hex string to bytes. Gas: 10"""
        return bytes.fromhex(s)

    # ── RLP (deprecated — Non-EVM) ───────────────

    @staticmethod
    def rlp_encode(obj: Any) -> bytes:
        """RLP Encode (DEPRECATED — use CBOR). Gas: 20"""
        # Non-EVM: RLP is deprecated, use CBOR instead
        return ATCEncoding.cbor_encode(obj)

    @staticmethod
    def rlp_decode(data: bytes) -> Any:
        """RLP Decode (DEPRECATED — use CBOR). Gas: 20"""
        return ATCEncoding.cbor_decode(data)

    # ── SCALE (deprecated — Non-EVM) ─────────────

    @staticmethod
    def scale_encode(obj: Any) -> bytes:
        """SCALE Encode (DEPRECATED — use CBOR). Gas: 20"""
        # Non-EVM: SCALE is deprecated
        return ATCEncoding.cbor_encode(obj)

    @staticmethod
    def scale_decode(data: bytes) -> Any:
        """SCALE Decode (DEPRECATED — use CBOR). Gas: 20"""
        return ATCEncoding.cbor_decode(data)
