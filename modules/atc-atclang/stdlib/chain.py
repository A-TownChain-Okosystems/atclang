# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Stdlib — ATC::Chain
Blockchain state access for ATCLang contracts.
"""
import time
import hashlib
from typing import Optional, Dict, Any


class ATCChain:
    """ATC::Chain — access current chain state from contracts."""

    def __init__(self, state: Dict[str, Any] = None):
        self._state = state or {}

    @property
    def block_number(self) -> int:
        return self._state.get("block_number", 0)

    @property
    def block_hash(self) -> str:
        return self._state.get("block_hash", "0x" + "0" * 64)

    @property
    def block_timestamp(self) -> int:
        return self._state.get("block_timestamp", int(time.time()))

    @property
    def chain_id(self) -> int:
        return self._state.get("chain_id", 658467)

    def require(self, condition: bool, message: str = "Condition failed"):
        if not condition:
            raise AssertionError(f"require: {message}")

    def emit(self, event_name: str, **kwargs):
        print(f"[Event:{event_name}] {kwargs}")

    def revert(self, message: str = "Transaction reverted"):
        raise RuntimeError(f"revert: {message}")
