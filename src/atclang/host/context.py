# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""HostContext — die einzige Quelle fuer Umgebungszustaende in der Contract-Ausfuehrung.

Determinismus-Regel (ATC-99 / ATC-STD-100 L4): Contracts duerfen NIE direkt
auf Wanduhr, Zufall oder OS zugreifen. Alle Umgebungswerte kommen aus dem
HostContext, der vom Knoten (Node) deterministisch aus Block-Headern gebaut
wird — zwei ehrliche Nodes MUSSSEN denselben Context fuer denselben Block
liefern (Konsens-Voraussetzung).
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HostPolicy:
    """Ausfuehrungs-Politik: was der Host erlaubt."""
    allow_wall_clock: bool = False        # Konsens: False — nur block_timestamp
    allow_os_access: bool = False
    allow_random: bool = False           # Zufall nur via vm-seed, nie host
    max_gas: int = 30_000_000
    max_call_depth: int = 64


@dataclass
class HostContext:
    """Deterministischer Ausfuehrungskontext eines Blocks."""
    chain_id: int = 658467
    block_number: int = 0
    block_timestamp: int = 0              # vom Block-Header, nicht time.time()
    block_hash: str = "0x" + "00" * 32
    prev_block_hash: str = "0x" + "00" * 32
    vm_seed: int = 0                       # deterministische Seed-Quelle
    gas_limit: int = 30_000_000
    policy: HostPolicy = field(default_factory=HostPolicy)
    _events: List[Dict[str, Any]] = field(default_factory=list)
    _logs: List[str] = field(default_factory=list)

    @classmethod
    def for_block(cls, chain_id: int, block_number: int, block_timestamp: int,
                  block_hash: str, policy: Optional[HostPolicy] = None) -> "HostContext":
        """Kanonischer Konstruktor: Node baut Context aus Block-Header."""
        return cls(chain_id=chain_id, block_number=block_number,
                   block_timestamp=block_timestamp, block_hash=block_hash,
                   policy=policy or HostPolicy())

    def now(self) -> int:
        """Zeitquelle fuer Contracts — Konsens-Pflicht: block_timestamp."""
        if self.policy.allow_wall_clock:
            return int(time.time())
        return self.block_timestamp

    def emit(self, name: str, **fields: Any) -> None:
        """Event-Log (Evidence-Spur, geordnet, replizierbar)."""
        self._events.append({"name": name, "block": self.block_number, **fields})

    def log(self, message: str) -> None:
        if self.policy.allow_os_access:
            self._logs.append(message)

    @property
    def events(self) -> List[Dict[str, Any]]:
        return list(self._events)

    def gas_consume(self, amount: int, used: int) -> int:
        used += amount
        if used > self.gas_limit:
            raise RuntimeError(f"Gas-Limit ueberschritten: {used} > {self.gas_limit}")
        return used
