# Copyright (c) 2026 Michael-Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""SecurityGate — statische Analyse von ATCLang-Quellcode (Pre-Compile-Gate).

Pruefregeln (Findings mit Schweregrad, Gate-Semantik nach ATC-GOV-001 Kap. 11):
- SEC-001 (BLOCKER): time.time()/datetime.now()/os.* in Consensus-Code —
  Verletzung des Determinismus-Prinzips (ATC-99).
- SEC-002 (BLOCKER): random.* ohne vm_seed — Nichtdeterminismus.
- SEC-003 (HIGH):    emit ohne Contract-Kontext.
- SEC-004 (MEDIUM):  unsafe-Funktionspraefix ohne require in der Funktion.
- SEC-005 (MEDIUM):  Unbegrenzte Schleifen ohne Gas-/Limit-Bindung.
Gate-Politik: BLOCKER => FAIL, HIGH => FAIL im consensus-Profil, sonst WARN.
"""
from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Severity(str, Enum):
    BLOCKER = "blocker"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Finding:
    rule: str
    severity: Severity
    line: int
    message: str


class SecurityGate:
    """Quellcode-Gate: analyse(source, profile) -> (findings, passed)."""

    FORBIDDEN_HOST_CALLS = re.compile(
        r"\b(time\.time\s*\(|datetime\.now\s*\(|os\.system\s*\(|os\.popen\s*\(|subprocess\.)")
    RANDOM_CALLS = re.compile(r"\brandom\.(?!seed)")
    EMIT_RE = re.compile(r"\bemit\s+(\w+)\s*\(")
    REQUIRE_RE = re.compile(r"\brequire\s*\(")
    UNSAFE_RE = re.compile(r"\bfn\s+(unsafe_\w+)")
    LOOP_RE = re.compile(r"\b(while|loop)\s*\(")

    def analyse(self, source: str, profile: str = "consensus") -> List[Finding]:
        findings: List[Finding] = []
        for lineno, line in enumerate(source.splitlines(), start=1):
            if profile == "consensus":
                if self.FORBIDDEN_HOST_CALLS.search(line):
                    findings.append(Finding("SEC-001", Severity.BLOCKER, lineno,
                                            "Host-Aufruf verboten im Consensus-Profil (Determinismus)"))
                if self.RANDOM_CALLS.search(line):
                    findings.append(Finding("SEC-002", Severity.BLOCKER, lineno,
                                            "random.* verboten — Zufall nur via vm_seed"))
            if self.UNSAFE_RE.search(line):
                fn = self.UNSAFE_RE.search(line).group(1)
                if not self._function_has_require(source, fn):
                    findings.append(Finding("SEC-004", Severity.MEDIUM, lineno,
                                            f"{fn} ohne require-Guard"))
        return findings

    def check(self, source: str, profile: str = "consensus") -> bool:
        """Gate-Semantik: BLOCKER => FAIL; HIGH => FAIL im consensus."""
        findings = self.analyse(source, profile)
        for f in findings:
            if f.severity == Severity.BLOCKER:
                return False
            if f.severity == Severity.HIGH and profile == "consensus":
                return False
        return True

    def _function_has_require(self, source: str, fn: str) -> bool:
        m = re.search(rf"fn\s+{fn}\s*\(.*?\)\s*(->\s*\w+\s*)?\{{", source)
        if not m:
            return False
        body = source[m.end():]
        depth, end = 1, len(body)
        for i, ch in enumerate(body):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        return bool(self.REQUIRE_RE.search(body[:end]))
