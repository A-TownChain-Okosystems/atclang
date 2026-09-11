# Copyright (c) 2026 Michael-Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""atcpkg-Manifest — deterministisches Paketformat fuer ATCLang-Module.

Felder (SemVer, SPDX-License-Identifier, Entry, Deps als Constraint-Range):
  name / version / license / entry / profile / dependencies / artifacts
Zwei Manifeste mit gleichem Namen MUSSSEN verschiedene Versionen haben;
Version-Bereiche folgen SemVer-Pruefung (kein Loose-Pinning: ^1.2.3 erlaubt,
* verboten — Reproduzierbarkeit, ATC-STD-041).
"""
from __future__ import annotations
import re
import semver
from dataclasses import dataclass, field
from typing import Dict, Optional

_ENTRY_RE = re.compile(r"^[\w/]+\.atc$")
_RANGE_RE = re.compile(r"^(\^|~)?\d+\.\d+\.\d+$")


class PackageError(Exception):
    pass


@dataclass
class PackageManifest:
    name: str
    version: str
    license: str
    entry: str
    profile: str = "consensus"
    dependencies: Dict[str, str] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)   # version -> artifact_id

    def validate(self) -> None:
        if not re.match(r"^[a-z][a-z0-9-_]*$", self.name):
            raise PackageError(f"Paketname ungueltig: {self.name!r}")
        if not semver.Version.is_valid(self.version):
            raise PackageError(f"SemVer ungueltig: {self.version!r}")
        if not self.license.startswith("SPDX-License-Identifier:"):
            raise PackageError("License muss SPDX-License-Identifier:… sein")
        if not _ENTRY_RE.match(self.entry):
            raise PackageError(f"Entry ungueltig: {self.entry!r}")
        if self.profile not in ("consensus", "off_chain", "debug"):
            raise PackageError(f"Profil ungueltig: {self.profile!r}")
        for dep, rng in self.dependencies.items():
            if rng == "*" or not _RANGE_RE.match(rng):
                raise PackageError(f"Dependency-Range ungueltig: {dep} {rng!r} — * verboten")

    def add_artifact(self, artifact_id: str) -> str:
        if artifact_id in self.artifacts.values():
            raise PackageError("Artefakt bereits registriert")
        self.artifacts[self.version] = artifact_id
        return artifact_id
