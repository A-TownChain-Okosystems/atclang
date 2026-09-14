"""Release-gate smoke checks for ATCLang 1.0.

These checks intentionally verify only invariants that can be established by the
repository itself. They do not claim ATVM/mainnet readiness.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_normative_spec_exists():
    spec = ROOT / "specs" / "language" / "SPEC.md"
    assert spec.exists()
    text = spec.read_text(encoding="utf-8")
    assert "ATCLang 1.0" in text
    assert "G1-Kriterien" in text


def test_release_gate_exists_and_is_no_go_until_evidence_exists():
    gate = ROOT / "docs" / "ATCLANG_1.0_RELEASE_GATE.md"
    assert gate.exists()
    text = gate.read_text(encoding="utf-8")
    assert "Status:" in text
    assert "NO-GO" in text
    assert "G3" in text and "G4" in text and "G18" in text


def test_conformance_plan_exists():
    plan = ROOT / "docs" / "ATCLANG_1.0_CONFORMANCE.md"
    assert plan.exists()
    text = plan.read_text(encoding="utf-8")
    for section in ("Lexical", "Parser", "Semantics", "IR", "Bytecode", "Determinism", "ATVM"):
        assert section in text
