# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""Deterministic execution context for ATCLang.

Consensus execution receives all environmental state from the block context.
There is deliberately no host wall-clock fallback and no host RNG capability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HostPolicy:
    """Capabilities available to an execution context."""

    allow_os_access: bool = False
    allow_random: bool = False
    max_gas: int = 30_000_000
    max_call_depth: int = 64


@dataclass
class HostContext:
    """Deterministic execution context derived from a block header."""

    chain_id: int = 658467
    block_number: int = 0
    block_timestamp: int = 0
    block_hash: str = "0x" + "00" * 32
    prev_block_hash: str = "0x" + "00" * 32
    vm_seed: int = 0
    gas_limit: int = 30_000_000
    policy: HostPolicy = field(default_factory=HostPolicy)
    _events: list[dict[str, Any]] = field(default_factory=list)
    _logs: list[str] = field(default_factory=list)

    @classmethod
    def for_block(
        cls,
        chain_id: int,
        block_number: int,
        block_timestamp: int,
        block_hash: str,
        prev_block_hash: str = "0x" + "00" * 32,
        vm_seed: int = 0,
        policy: HostPolicy | None = None,
    ) -> "HostContext":
        """Build the canonical context from authenticated block data."""
        if block_number < 0 or block_timestamp < 0:
            raise ValueError("block number/timestamp must be non-negative")
        if not block_hash:
            raise ValueError("block_hash is required")
        return cls(
            chain_id=chain_id,
            block_number=block_number,
            block_timestamp=block_timestamp,
            block_hash=block_hash,
            prev_block_hash=prev_block_hash,
            vm_seed=vm_seed,
            gas_limit=(policy or HostPolicy()).max_gas,
            policy=policy or HostPolicy(),
        )

    def now(self) -> int:
        """Return the block timestamp; host wall-clock access is impossible."""
        return self.block_timestamp

    def emit(self, name: str, **fields: Any) -> None:
        """Record a deterministic, replayable event."""
        self._events.append({"name": name, "block": self.block_number, **fields})

    def log(self, message: str) -> None:
        if self.policy.allow_os_access:
            self._logs.append(message)

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)

    def gas_consume(self, amount: int, used: int) -> int:
        if amount < 0:
            raise ValueError("gas amount must be non-negative")
        used += amount
        if used > self.gas_limit:
            raise RuntimeError(f"Gas-Limit ueberschritten: {used} > {self.gas_limit}")
        return used
