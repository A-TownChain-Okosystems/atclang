#!/usr/bin/env python3
"""Fail-closed repository audit for ATCLang.

The audit checks enforceable repository invariants. It deliberately does not claim
absolute immunity from zero-days or malware; it proves only the controls encoded
here and fails when known unsafe implementation patterns are present.
"""
from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]

REQUIRED = {
    "README.md", "AGENTS.md", "AGENT_MANIFEST.md", "ARCHITECTURE.md",
    "CHANGELOG.md", "CODEOWNERS", "CONTRIBUTING.md", "GOVERNANCE.md",
    "LICENSE", "ROADMAP.md", "SECURITY.md", "STATUS.md", "TODO.md", "SPRINTS.md",
    ".atc/repository.yaml", ".atc/standards.yaml", ".atc/evidence/evidence.yaml",
    "specs/VERSION.toml", "specs/language/SPEC.md", "specs/semantics/SPEC.md",
    "docs/wiki/README.md",
}
WORKFLOWS = {
    ".github/workflows/code-quality.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/dependency-review.yml",
    ".github/workflows/determinism-gate.yml",
    ".github/workflows/governance-ci.yml",
    ".github/workflows/test-suite.yml",
    ".github/workflows/atclang-ci-audit.yml",
}
FAIL: list[str] = []
WARN: list[str] = []


def read(path: str) -> str:
    p = ROOT / path
    if not p.is_file():
        FAIL.append(f"missing required file: {path}")
        return ""
    return p.read_text(encoding="utf-8", errors="strict")


def main() -> int:
    for path in sorted(REQUIRED | WORKFLOWS):
        read(path)

    repo = read(".atc/repository.yaml")
    if repo and not re.search(r"^language:\s*\n\s+primary:\s+rust\s*$", repo, re.M):
        FAIL.append(".atc/repository.yaml: primary language must remain Rust")

    agents = read("AGENTS.md")
    for required in ("ATC-STD-README-001", "ATC-STD-MD-001", "ATC-STD-201", "ATC-STD-AI-DEV-007"):
        if required not in agents:
            FAIL.append(f"AGENTS.md: missing normative reference {required}")

    governance = read(".github/workflows/governance-ci.yml")
    if "atc_repo_audit.py" not in governance or "atc-standards" not in governance:
        FAIL.append("governance-ci.yml: central standards audit is not executed")
    quality = read(".github/workflows/code-quality.yml")
    if "ruff check" not in quality or "ruff format --check" not in quality:
        FAIL.append("code-quality.yml: lint/format gates incomplete")
    tests = read(".github/workflows/test-suite.yml")
    for marker in ("pytest", "cargo test", "differential", "evidence"):
        if marker not in tests.lower():
            FAIL.append(f"test-suite.yml: required gate missing: {marker}")
    audit_workflow = read(".github/workflows/atclang-ci-audit.yml")
    for marker in ("atclang_ci_audit.py", "compileall", "security-static"):
        if marker not in audit_workflow:
            FAIL.append(f"atclang-ci-audit.yml: required gate missing: {marker}")

    vm = read("src/atclang/vm/atcvm.py")
    if vm:
        dangerous = {
            "ecdsa_sign": r"ECDSA Simulation|return\s+[\"']sig_[\"']\s*\+",
            "ecdsa_verify": r"sig\.startswith\([\"']sig_[\"']\)",
            "verify_jwt": r"len\(token\)\s*>\s*10",
            "net_send": r"def\s+net_send[\s\S]{0,300}?return\s+True\s*#\s*Simulation",
            "rpc_call": r"return\s*\{\s*[\"']status[\"']\s*:\s*200",
            "address": r"def\s+generate_atc_address[\s\S]{0,250}?secrets\.token_bytes",
            "fake_bip39": r"def\s+bip39_mnemonic[\s\S]{0,1200}?words\s*=\s*\[",
        }
        for name, pattern in dangerous.items():
            if re.search(pattern, vm, re.I):
                FAIL.append(f"src/atclang/vm/atcvm.py: unsafe reference primitive remains: {name}")
        if "# STUB:" in vm:
            FAIL.append("src/atclang/vm/atcvm.py: executable STUB marker remains")

    arch_candidates = ["ARCHITECTURE.md", "docs/ATCLANG_1.0_ARCHITECTURE.md"]
    arch = "\n".join(read(p) for p in arch_candidates if (ROOT / p).is_file())
    for phrase in ("Rust-first", "Bytecode-Verifier", "Python", "differential"):
        if phrase.lower() not in arch.lower():
            FAIL.append(f"architecture baseline: missing enforcement statement: {phrase}")

    status = read("STATUS.md")
    audit = read("docs/audits/REPOSITORY-AUDIT-2026-09-16-CI.md")
    if "NOT ESTABLISHED" not in status and "NOT ESTABLISHED" not in audit:
        FAIL.append("release status: production readiness is not explicitly bounded")
    for finding in ("F-20260916-ATCLANG-001", "F-20260916-ATCLANG-002", "F-20260916-ATCLANG-003", "F-20260916-ATCLANG-004", "F-20260916-ATCLANG-005"):
        if finding not in audit:
            FAIL.append(f"audit documentation: missing release-blocking finding {finding}")

    source_files = list((ROOT / "src").rglob("*.py")) + list((ROOT / "crates").rglob("*.rs"))
    suspicious = re.compile(r"\b(eval|exec)\s*\(|pickle\.loads?\s*\(|os\.system\s*\(|subprocess\.(Popen|run|call)\s*\(|curl\s+https?://|wget\s+https?://", re.I)
    for p in source_files:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if suspicious.search(text):
            WARN.append(f"security review trigger in executable source: {p.relative_to(ROOT)}")
        if re.search(r"\bTODO\b|\bFIXME\b|\bXXX\b", text):
            WARN.append(f"placeholder marker in executable source: {p.relative_to(ROOT)}")

    for path in sorted(WORKFLOWS):
        text = read(path)
        for match in re.finditer(r"uses:\s*([^\s#]+)", text):
            ref = match.group(1).rsplit("@", 1)[-1]
            if not re.fullmatch(r"[0-9a-f]{40}", ref):
                FAIL.append(f"{path}: action is not pinned to immutable SHA: {match.group(1)}")

    register = read("FILE_REGISTER.md")
    for path in sorted(WORKFLOWS | {"tools/audit/atclang_ci_audit.py"}):
        if path not in register:
            WARN.append(f"FILE_REGISTER.md stale: missing {path}; regenerate from Git tree")

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
