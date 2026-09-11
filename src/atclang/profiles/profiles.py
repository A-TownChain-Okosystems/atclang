# Copyright (c) 2026 Michael-Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""Execution Profiles: gleiche Sprache, unterschiedliche Vertrauenskontexte.

- consensus:   Determinismus-Pflicht (SecurityGate BLOCKER), Gas-Limit, kein OS
- off_chain:   erweiterte Host-Freigaben (Wanduhr erlaubt), lockeres Gate
- debug:       Vollzugriff fuer lokale Entwicklung, nie fuer Deployment
Profil ist Teil des Artefakts (ATCA) — ein consensus-Artefakt ist nur mit
consensus-Profil kompilierbar und validierbar (Fail-Closed).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ExecutionProfile:
    name: str
    deterministic: bool
    gas_limit: int
    security_gate_blockers_fail: bool
    allow_wall_clock: bool
    allow_os: bool


PROFILES: Dict[str, ExecutionProfile] = {
    "consensus": ExecutionProfile("consensus", True, 30_000_000, True, False, False),
    "off_chain": ExecutionProfile("off_chain", False, 30_000_000, False, True, False),
    "debug":     ExecutionProfile("debug", False, 100_000_000, False, True, True),
}


def get_profile(name: str) -> ExecutionProfile:
    if name not in PROFILES:
        raise KeyError(f"Unbekanntes Profil: {name!r} — verfuegbar: {sorted(PROFILES)}")
    return PROFILES[name]
