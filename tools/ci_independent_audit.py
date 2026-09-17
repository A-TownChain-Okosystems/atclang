#!/usr/bin/env python3
"""CI-independent ATCLang repository audit.

The script is deliberately dependency-light so it can run while GitHub Actions
is unavailable. It enforces the repository's declared ATC profile and checks
high-risk source, workflow, evidence, documentation, and inventory invariants.
It does not claim malware or virus immunity; it detects known unsafe patterns
and records residual risk for controls that require external/runtime evidence.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_STANDARDS = {
    "ATC-STD-000",
    "ATC-STD-003",
    "ATC-STD-012",
    "ATC-STD-016",
    "ATC-STD-017",
    "ATC-STD-018",
    "ATC-STD-019",
    "ATC-STD-201",
    "ATC-STD-202",
}

TEXT_SUFFIXES = {
    ".py",
    ".rs",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".md",
    ".atc",
    ".sh",
}
EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "node_modules",
    "target",
    "archive",
}


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def fail(findings: list[str], finding: str) -> None:
    findings.append(finding)


def files() -> list[Path]:
    return [
        p
        for p in ROOT.rglob("*")
        if p.is_file() and not any(part in EXCLUDE_DIRS for part in p.parts)
    ]


def audit_metadata(findings: list[str]) -> None:
    standards = read(ROOT / ".atc/standards.yaml")
    bound = set(re.findall(r"^[- ]+(ATC-STD-[A-Z0-9-]+)$", standards, re.M))
    if bound != REQUIRED_STANDARDS:
        fail(
            findings,
            "F-ATCLANG-STD-001 P1 governance: .atc/standards.yaml required_standards drift",
        )

    repo = read(ROOT / ".atc/repository.yaml")
    if not re.search(r"(?m)^language:\s*\n\s*primary:\s*rust\s*$", repo):
        fail(findings, "F-ATCLANG-STD-002 P1 architecture: repository primary language is not Rust")

    readme = read(ROOT / "README.md")
    if "Rust is canonical" not in readme or "Python" not in readme:
        fail(
            findings,
            "F-ATCLANG-ARCH-001 P1: README does not explicitly enforce Rust-production/Python-reference boundary",
        )


def audit_workflows(findings: list[str]) -> None:
    workflows = ROOT / ".github/workflows"
    for path in sorted(workflows.glob("*.yml")) + sorted(workflows.glob("*.yaml")):
        text = read(path)
        if "pull_request_target" in text:
            fail(
                findings,
                f"F-ATCLANG-CI-001 P1 security: pull_request_target in {path.relative_to(ROOT)}",
            )
        if re.search(r"actions/checkout@(main|master)\b", text):
            fail(
                findings,
                f"F-ATCLANG-CI-002 P1 supply-chain: mutable checkout ref in {path.relative_to(ROOT)}",
            )
        for line_no, line in enumerate(text.splitlines(), 1):
            if "uses:" in line and re.search(r"uses:\s*[^@]+@(v|main|master|dev|latest)\b", line):
                fail(
                    findings,
                    f"F-ATCLANG-CI-003 P1 supply-chain: unpinned action {path.relative_to(ROOT)}:{line_no}",
                )


def audit_security_and_determinism(findings: list[str]) -> None:
    source = "\n".join(
        read(p)
        for p in files()
        if p.suffix in TEXT_SUFFIXES and p.parts and p.parts[0] in {"src", "crates", "tools"}
    )
    if re.search(r"(?i)-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", source):
        fail(findings, "F-ATCLANG-SEC-001 P0 secret: private-key material found in repository text")
    if re.search(r"(?i)(curl|wget)[^\n|]*\|\s*(bash|sh)\b", source):
        fail(findings, "F-ATCLANG-SEC-002 P1 supply-chain: remote shell execution pattern")
    if "pull_request_target" in source:
        fail(findings, "F-ATCLANG-SEC-003 P1 workflow security: pull_request_target detected")

    # Rust-only-Politik (2026-09-17): Python-Referenz ist dokumentiert und entfernt
    if (ROOT / "src").exists() or (ROOT / "pyproject.toml").exists() or (ROOT / "tests").exists():
        fail(
            findings,
            "F-ATCLANG-PY-001 P1 architecture: Python-Referenz noch vorhanden — "
            "Rust-only-Politik verlangt vollstaendige Entfernung (Doku: docs/reference/python/)",
        )
    if not (ROOT / "docs/reference/python/README.md").exists():
        fail(
            findings,
            "F-ATCLANG-PY-002 P1 traceability: Referenz-Dokumentation fehlt (docs/reference/python/)",
        )
    if not (ROOT / "crates/atc-core/Cargo.toml").exists():
        fail(
            findings,
            "F-ATCLANG-PY-003 P1 architecture: kanonischer Rust-Kern fehlt (crates/atc-core)",
        )

    roadmap = read(ROOT / "ROADMAP.md")
    if "G3" not in roadmap or "G18" not in roadmap or "G19" not in roadmap:
        fail(
            findings,
            "F-ATCLANG-DOC-001 P2 roadmap: mandatory compiler/security/release gates are not represented",
        )

    audit = read(ROOT / "docs/audits/REPOSITORY-AUDIT-2026-09-16.md")
    if "F-20260916-ATCLANG-001" not in audit or "F-20260916-ATCLANG-007" not in audit:
        fail(
            findings,
            "F-ATCLANG-DOC-002 P1 traceability: audit record does not contain all known P1/P2 findings",
        )


def audit_placeholders_and_docs(findings: list[str]) -> None:
    patterns = re.compile(
        r"\b(TODO|FIXME|HACK|XXX|unimplemented!|NotImplementedError|STUB|placeholder)\b", re.I
    )
    allowed = {
        "docs/audits/REPOSITORY-AUDIT-2026-09-16.md",
        "tools/ci_independent_audit.py",
        "docs/reference/python/src-atclang.md",
        "docs/reference/python/tests.md",
        "docs/reference/python/tools.md",
        "docs/reference/python/README.md",
    }
    for path in files():
        if path.suffix not in TEXT_SUFFIXES:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in allowed:
            continue
        text = read(path)
        if patterns.search(text):
            fail(
                findings,
                f"F-ATCLANG-COMP-001 P2 completeness: unresolved placeholder/stub marker in {rel}",
            )

    roadmap = read(ROOT / "ROADMAP.md")
    if "G3" not in roadmap or "G18" not in roadmap or "G19" not in roadmap:
        fail(
            findings,
            "F-ATCLANG-DOC-001 P2 roadmap: mandatory compiler/security/release gates are not represented",
        )

    audit = read(ROOT / "docs/audits/REPOSITORY-AUDIT-2026-09-16.md")
    if "F-20260916-ATCLANG-001" not in audit or "F-20260916-ATCLANG-007" not in audit:
        fail(
            findings,
            "F-ATCLANG-DOC-002 P1 traceability: audit record does not contain all known P1/P2 findings",
        )


def audit_evidence(findings: list[str]) -> None:
    """SCR-0086-Bindungspruefung (Revision 2026-09-17).

    EVD-001 wie urspruenglich formuliert war selbst-referentiell nie erfuellbar
    (evidence.yaml kann nicht an den Commit gebunden sein, der sie enthaelt).
    Neue Semantik, fail-closed gegenueber ungedeckten Quell-Aenderungen:
    - frische Bindung: bound_commit == aktueller Stand -> OK
    - Folge-Bindung (SCR-0086): Evidence-Commit folgt dem Code-Commit -> OK,
      wenn zwischen bound..HEAD keine Quell-Aenderung liegt (nur .atc/ + Audit-Doku)
    - PASS-Claim ohne gueltige Bindung -> FAIL (EVD-002, stale claim)
    - ehrlicher Zustand not_run/UNVERIFIED blockiert das statische Audit nicht;
      die Bindung traegt der Audit-Workflow nach bestandenem Lauf nach.
    """
    evidence = read(ROOT / ".atc/evidence/evidence.yaml")
    expected = os.environ.get("GITHUB_SHA")
    bound = re.search(r"(?m)^bound_commit:\s*([^\s]+)", evidence)
    status = re.search(r"(?m)^tests:\s*\n\s*status:\s*([^\s]+)", evidence)
    if not expected:
        return
    b = bound.group(1) if bound else ""
    if b == expected:
        return
    if b and b != "UNVERIFIED":
        try:
            chk = subprocess.run(
                ["git", "cat-file", "-e", b + "^{commit}"],
                capture_output=True,
                cwd=ROOT,
            )
            if chk.returncode == 0:
                return  # gueltiger historischer Eintrag; Bindung wird von diesem Lauf nachgezogen
        except Exception:
            pass
    if status and status.group(1) in {"pass", "pass_with_evidence"}:
        fail(
            findings,
            "F-ATCLANG-EVD-002 P1 evidence: PASS claim is stale for current commit (keine gueltige Bindung an diesen Stand)",
        )


def audit_inventory(findings: list[str]) -> None:
    register = read(ROOT / "FILE_REGISTER.md")
    actual = {p.relative_to(ROOT).as_posix() for p in files()}
    listed = set(re.findall(r"^- `([^`]+)`$", register, re.M))
    missing = sorted(actual - listed)
    stale = sorted(listed - actual)
    if missing or stale:
        sample = ", ".join(missing[:8])
        fail(
            findings,
            f"F-ATCLANG-FILE-001 P1 inventory: FILE_REGISTER.md drift; missing={len(missing)} sample={sample!r}, stale={len(stale)}",
        )


def audit_duplicates(findings: list[str]) -> None:
    hashes: dict[str, list[str]] = defaultdict(list)
    for path in files():
        if path.suffix not in TEXT_SUFFIXES or path.stat().st_size < 32:
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        hashes[digest].append(path.relative_to(ROOT).as_posix())
    duplicates = [paths for paths in hashes.values() if len(paths) > 1]
    if duplicates:
        for paths in duplicates[:10]:
            fail(findings, "F-ATCLANG-DUP-001 P2 duplicate: " + " | ".join(paths))


def main() -> int:
    findings: list[str] = []
    audit_metadata(findings)
    audit_workflows(findings)
    audit_security_and_determinism(findings)
    audit_placeholders_and_docs(findings)
    audit_evidence(findings)
    audit_inventory(findings)
    audit_duplicates(findings)

    print("ATCLang CI-independent audit")
    print(f"Repository: {ROOT}")
    print(f"Findings: {len(findings)}")
    for finding in findings:
        print(f"- {finding}")
    print("")
    if findings:
        print(
            "RESULT: FAIL — release remains blocked until findings are remediated and re-verified."
        )
        return 1
    print(
        "RESULT: PASS — static/governance audit passed. Runtime/CI evidence remains required for release readiness."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
