# Copyright (c) 2026 Michael-Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""CompiledArtifact — das transportable Compile-Ergebnis (.atca).

Governance-Kopplung: Artefakt-Record nach ATC-STD-043 (Artifact Integrity,
9 Felder) und Reproducible Builds (ATC-STD-041): kanonische JSON-Serialisierung
(sortierte Keys, feste Trenner) macht Builds reproduzierbar; die Artifact-ID
ist sha3-256 des kanonischen Payloads — identischer Source + identische
Compiler-Version MUSSSEN identische ID ergeben.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

ATCA_VERSION = "1.0.0"


class ArtifactError(Exception):
    pass


@dataclass
class CompiledArtifact:
    """Deterministisch serialisierbares Compile-Artefakt."""
    name: str
    entry: str
    compiler_version: str
    language_standard: str                       # z. B. ATC-92 v1.0.0
    profile: str                                 # consensus | off_chain | debug
    source_sha256: str
    bytecode: Dict[str, Any]                     # serialisierte Sections
    abi: List[Dict[str, Any]] = field(default_factory=list)
    contract_standards: List[str] = field(default_factory=list)

    def canonical_payload(self) -> bytes:
        """Kanonische JSON-Serialisierung (Determinismus-Pflicht)."""
        payload = {
            "name": self.name, "entry": self.entry,
            "compiler_version": self.compiler_version,
            "language_standard": self.language_standard,
            "profile": self.profile, "source_sha256": self.source_sha256,
            "bytecode": self.bytecode, "abi": self.abi,
            "contract_standards": self.contract_standards,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    @property
    def artifact_id(self) -> str:
        return "0x" + hashlib.sha3_256(self.canonical_payload()).hexdigest()

    def to_bytes(self) -> bytes:
        """Wire-Format: ATCA-Header + kanonischer Payload."""
        doc = {"atca_version": ATCA_VERSION, "artifact_id": self.artifact_id,
               "payload_sha256": "0x" + hashlib.sha256(self.canonical_payload()).hexdigest()}
        return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode() + b"\x00" + self.canonical_payload()

    @classmethod
    def from_bytes(cls, raw: bytes) -> "CompiledArtifact":
        try:
            head, _, payload = raw.partition(b"\x00")
            doc = json.loads(head)
            p = json.loads(payload)
        except (ValueError, UnicodeDecodeError) as exc:
            raise ArtifactError(f"Ungueltiges ATCA-Format: {exc}")
        if doc.get("atca_version") != ATCA_VERSION:
            raise ArtifactError(f"ATCA-Version {doc.get('atca_version')} nicht unterstuetzt")
        art = cls(name=p["name"], entry=p["entry"], compiler_version=p["compiler_version"],
                  language_standard=p["language_standard"], profile=p["profile"],
                  source_sha256=p["source_sha256"], bytecode=p["bytecode"],
                  abi=p.get("abi", []), contract_standards=p.get("contract_standards", []))
        if art.artifact_id != doc["artifact_id"]:
            raise ArtifactError("Artifact-ID-Mismatch — Artefakt manipuliert oder korrupt")
        return art

    def validate(self) -> None:
        """ATC-STD-043-Feldpruefung (9 Pflichtfelder)."""
        required = ["name", "entry", "compiler_version", "language_standard",
                    "profile", "source_sha256", "bytecode", "abi", "contract_standards"]
        missing = [f for f in required if not hasattr(self, f)]
        if missing:
            raise ArtifactError(f"Fehlende Artefakt-Felder: {missing}")
        if self.profile not in ("consensus", "off_chain", "debug"):
            raise ArtifactError(f"Unbekanntes Profil: {self.profile}")
        if len(self.source_sha256) != 66:
            raise ArtifactError("source_sha256 muss 32-Byte-Hex sein")
