"""ATC::Chain reference bindings.

Consensus-safe rule: chain environment values are supplied by the host
context. This module never reads the local wall clock and never prints
side effects during contract execution.
"""

from typing import Any


class ATCChain:
    """Deterministic chain-state view supplied by the execution host."""

    DEFAULT_CHAIN_ID = 658467

    def __init__(self, state: dict[str, Any] | None = None):
        self._state = dict(state or {})
        self._events: list[dict[str, Any]] = []

    @property
    def block_number(self) -> int:
        return int(self._state.get("block_number", 0))

    @property
    def block_hash(self) -> str:
        return str(self._state.get("block_hash", "0x" + "0" * 64))

    @property
    def block_timestamp(self) -> int:
        """Return the host-supplied block timestamp; never the local clock."""
        return int(self._state.get("block_timestamp", 0))

    @property
    def chain_id(self) -> int:
        return int(self._state.get("chain_id", self.DEFAULT_CHAIN_ID))

    def require(self, condition: bool, message: str = "Condition failed") -> None:
        if not condition:
            raise AssertionError(f"require: {message}")

    def emit(self, event_name: str, **kwargs: Any) -> None:
        """Record an event for deterministic host-side collection."""
        self._events.append({"event": event_name, "block": self.block_number, "args": dict(kwargs)})

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def revert(self, message: str = "Transaction reverted") -> None:
        raise RuntimeError(f"revert: {message}")
