#!/usr/bin/env python3
"""Fail-closed CI audit for ATCLang repository governance and security boundaries.

This is intentionally deterministic and stdlib-only. It validates repository-local
invariants that can be checked without trusting GitHub Actions history.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

REQUIRED = {
    "README.md", "AGENTS.md", "AGENT_MANIFEST.md", "ARCHITECTURE.md",
    "CHANGELOG.md", "CODEOWNERS", "CONTRIBUTING.md", "GOVERNANCE.md",
    "LICENSE", "ROADMAP.md", "SECURITY.md", "STATUS.md",
    ".atc/repository.yaml", ".atc/standards.yaml", ".atc/evidence/evidence.yaml",
    "specs/VERSION.toml", "specs/language/SPEC.md", "specs/semantics/SPEC.md",
}
WORKFLOWS = {
    ".github/workflows/code-quality.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/dependency-review.yml",
    ".github/workflows/determinism-gate.yml",
    ".github/workflows/governance-ci.yml",
    ".github/workflows/test-suite.yml",
}

FAIL = []
WARN = []


def read(path: str) -> str:
    p = ROOT / path
    if not p.is_file():
        FAIL.append(f"missing required file: {path}")
        return ""
    return p.read_text(encoding="utf-8")


def require_text(path: str, patterns: list[str]) -> None:
    text = read(path)
    for pattern in patterns:
        if not re.search(pattern, text, re.I | re.M):
            FAIL.append(f"{path}: required pattern missing: {pattern}")


def main() -> int:
    for path in sorted(REQUIRED):
        read(path)
    for path in sorted(WORKFLOWS):
        read(path)

    repo = read(".atc/repository.yaml")
    if repo and not re.search(r"^language:\s*\n\s+primary:\s+rust\s*$", repo, re.M):
        FAIL.append(".atc/repository.yaml: primary language must remain Rust")

    agents = read("AGENTS.md")
    for required in ("ATC-STD-README-001", "ATC-STD-MD-001", "ATC-STD-201", "ATC-STD-AI-DEV-007"):
        if required not in agents:
            FAIL.append(f"AGENTS.md: missing normative reference {required}")

    # Required CI enforcement. A workflow that merely exists is not sufficient.
    governance = read(".github/workflows/governance-ci.yml")
    if "atc_repo_audit.py" not in governance:
        FAIL.append("governance-ci.yml: ATC repository audit not executed")
    quality = read(".github/workflows/code-quality.yml")
    if "ruff check" not in quality or "ruff format --check" not in quality:
        FAIL.append("code-quality.yml: lint/format gates incomplete")
    tests = read(".github/workflows/test-suite.yml")
    for marker in ("pytest", "cargo test", "differential", "evidence"):
        if marker not in tests:
            FAIL.append(f"test-suite.yml: required gate missing: {marker}")

    # Production security boundary: the Python VM contains reference-only primitives.
    vm = read("src/atclang/vm/atcvm.py")
    if vm:
        dangerous = {
            "ecdsa_sign": r'return\s+["\']sig_["\']\s*\+|ECDSA Simulation',
            "ecdsa_verify": r'sig\.startswith\(["\']sig_["\']\)',
            "verify_jwt": r'len\(token\)\s*>\s*10',
            "net_send": r'def\s+net_send[\s\S]{0,300}?return\s+True\s+#\s*Simulation',
            "rpc_call": r'return\s*\{\s*["\']status["\']\s*:\s*200',
            "address": r'def\s+generate_atc_address[\s\S]{0,250}?secrets\.token_bytes',
        }
        for name, pattern in dangerous.items():
            if re.search(pattern, vm, re.I):
                FAIL.append(f"src/atclang/vm/atcvm.py: insecure reference primitive still active: {name}")

        if "# STUB:" in vm:
            FAIL.append("src/atclang/vm/atcvm.py: STUB marker remains in an executable VM module")

    # Consensus-sensitive nondeterminism must not be presented as canonical execution.
    arch = read("docs/ATCLANG_1.0_ARCHITECTURE.md")
    for phrase in ("Rust-first", "Python = Referenz", "Bytecode-Verifier = harte Trust-Boundary", "DUAL-STACK-DIFFERENTIAL-MODELL"):
        if phrase not in arch:
            FAIL.append(f"architecture baseline: missing enforcement statement: {phrase}")

    # Repository file register must not silently omit current CI/audit infrastructure.
    register = read("FILE_REGISTER.md")
    for path in sorted(WORKFLOWS | {"tools/audit/atclang_ci_audit.py"}):
        if path not in register:
            WARN.append(f"FILE_REGISTER.md stale: missing {path}; regenerate from Git tree")

    # Obvious placeholders in executable source. Explicit reference stubs are blocked above.
    source_files = list((ROOT / "src").rglob("*.py")) + list((ROOT / "crates").rglob("*.rs"))
    for p in source_files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\bTODO\b|\bFIXME\b|\bXXX\b", text):
            WARN.append(f"placeholder marker in executable source: {p.relative_to(ROOT)}")

    if WARN:
        print("WARNINGS:")
        for item in WARN:
            print(f"- {item}")

    if FAIL:
        print("FAIL: ATCLang CI audit is fail-closed")
        for item in FAIL:
            print(f"- {item}")
        return 1

    print("PASS: ATCLang CI audit invariants satisfied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
