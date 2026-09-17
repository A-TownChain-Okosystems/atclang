"""Determinism and capability static analysis for ATCLang source.

This gate is intentionally conservative for the consensus profile: host clock,
OS/process access, filesystem, unrestricted network and randomness are rejected
unless they are expressed through explicitly host-provided deterministic APIs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    BLOCKER = "blocker"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: Severity
    line: int
    message: str


class SecurityGate:
    """Static source gate with fail-closed consensus semantics."""

    FORBIDDEN_HOST = re.compile(
        r"(?:\btime\.(?:time|monotonic)\s*\(|\bdatetime\.(?:now|utcnow)\s*\(|"
        r"\bos\.(?:system|popen|remove|unlink|mkdir|makedirs|rename)\s*\(|"
        r"\bsubprocess\.(?:run|Popen|call|check_call|check_output)\s*\(|"
        r"\bopen\s*\(|\bsocket\.(?:socket|create_connection)\s*\()"
    )
    FORBIDDEN_IMPORT = re.compile(
        r"^\s*(?:import\s+(?:time|datetime|os|subprocess|socket|random)\b|"
        r"from\s+(?:time|datetime|os|subprocess|socket|random)\s+import\b)"
    )
    RANDOM_CALL = re.compile(r"\b(?:random|secrets)\.[A-Za-z_][A-Za-z0-9_]*\s*\(")
    FORBIDDEN_NAMESPACE = re.compile(
        r"\b(?:FS_(?:WRITE|READ|MKDIR)|NET_(?:SEND|RECV|CONNECT|BROADCAST)|"
        r"SPAWN|ASYNC_CALL|AWAIT)\b"
    )
    UNSAFE_FN = re.compile(r"\bfn\s+(unsafe_[A-Za-z0-9_]*)\s*\(")
    REQUIRE = re.compile(r"\brequire\s*\(")

    def analyse(self, source: str, profile: str = "consensus") -> list[Finding]:
        findings: list[Finding] = []
        lines = source.splitlines()
        for lineno, line in enumerate(lines, start=1):
            if profile == "consensus":
                if self.FORBIDDEN_IMPORT.search(line) or self.FORBIDDEN_HOST.search(line):
                    findings.append(
                        Finding(
                            "SEC-001",
                            Severity.BLOCKER,
                            lineno,
                            "Host/OS capability is forbidden in consensus code",
                        )
                    )
                if self.RANDOM_CALL.search(line):
                    findings.append(
                        Finding(
                            "SEC-002",
                            Severity.BLOCKER,
                            lineno,
                            "Randomness is forbidden in consensus code",
                        )
                    )
                if self.FORBIDDEN_NAMESPACE.search(line):
                    findings.append(
                        Finding(
                            "SEC-003",
                            Severity.BLOCKER,
                            lineno,
                            "Non-deterministic host capability is forbidden in consensus code",
                        )
                    )
            match = self.UNSAFE_FN.search(line)
            if match and not self._function_has_require(source, match.group(1)):
                findings.append(
                    Finding(
                        "SEC-004",
                        Severity.MEDIUM,
                        lineno,
                        f"{match.group(1)} lacks an explicit require guard",
                    )
                )
        return findings

    def check(self, source: str, profile: str = "consensus") -> bool:
        return not any(
            f.severity == Severity.BLOCKER
            or (f.severity == Severity.HIGH and profile == "consensus")
            for f in self.analyse(source, profile)
        )

    def _function_has_require(self, source: str, fn: str) -> bool:
        match = re.search(r"fn\s+" + re.escape(fn) + r"\s*\([^)]*\)[^{]*\{", source)
        if not match:
            return False
        body = source[match.end() :]
        depth = 1
        for index, char in enumerate(body):
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return bool(self.REQUIRE.search(body[:index]))
        return False
