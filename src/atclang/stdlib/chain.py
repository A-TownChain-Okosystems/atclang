# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""ATCLang Stdlib — ATC::Chain.

Blockchain state access is strictly supplied by the execution context.
No host-clock fallback is permitted.
"""

from typing import Any


class ATCChain:
    """ATC::Chain — deterministic access to current chain state."""

    def __init__(self, state: dict[str, Any] | None = None):
        self._state = dict(state or {})

    @property
    def block_number(self) -> int:
        return int(self._state.get("block_number", 0))

    @property
    def block_hash(self) -> str:
        return str(self._state.get("block_hash", "0x" + "0" * 64))

    @property
    def block_timestamp(self) -> int:
        if "block_timestamp" not in self._state:
            raise RuntimeError("deterministic block_timestamp is required")
        return int(self._state["block_timestamp"])

    @property
    def chain_id(self) -> int:
        return int(self._state.get("chain_id", 658467))

    def require(self, condition: bool, message: str = "Condition failed") -> None:
        if not condition:
            raise AssertionError(f"require: {message}")

    def emit(self, event_name: str, **kwargs: Any) -> None:
        events = self._state.setdefault("events", [])
        events.append({"name": event_name, "block": self.block_number, **kwargs})

    def revert(self, message: str = "Transaction reverted") -> None:
        raise RuntimeError(f"revert: {message}")
