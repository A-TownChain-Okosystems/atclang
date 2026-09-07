# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.
"""Gate G2 — Semantik-Tests (specs/semantics/SPEC.md, Regeln SEM-001…SEM-012)."""
import glob
import os

import pytest

from atclang.frontend.parser.parser import parse
from atclang.semantics import TypeChecker, analyze_source
from atclang.compiler.errors import (
    BreakOutsideLoopError,
    TypeMismatchError,
)


def wrap(body: str) -> str:
    """Gueltiges Programm-Geruest: Contract mit einer Funktion drumherum."""
    return "contract T {\n    fn f() {\n" + body + "\n    }\n}\n"


def diags(src: str):
    return TypeChecker().analyze_source(src)


def rules(ds):
    return sorted({d.rule for d in ds})


# ── Referenz-Korpus ─────────────────────────────────────────────────────

def test_examples_clean():
    """Alle parsbaren Beispiel-Programme muessen semantisch CLEAN sein."""
    base = os.path.join(os.path.dirname(__file__), "..", "examples")
    checked = 0
    for p in sorted(glob.glob(os.path.join(base, "*.atc"))):
        src = open(p, encoding="utf-8").read()
        try:
            ds = analyze_source(src)
        except SyntaxError:
            continue  # Parser-Luecke (trait) — kein Semantik-Gegenstand
        assert ds == [], "%s: %s" % (os.path.basename(p), [str(d) for d in ds])
        checked += 1
    assert checked >= 4


# ── Valide Programme ─────────────────────────────────────────────────────

def test_valid_program_clean():
    src = """contract TC {
    state v: u64 = 0
    fn compute(a: int, b: int) -> int {
        let sum: int = a + b
        return sum
    }
    fn run() -> u64 {
        for i in range(10) {
            if i == 2 {
                break
            }
        }
        while false {
            continue
        }
        let r: float = 1
        print(self.compute(2, 3))
        return self.v
    }
}
"""
    assert diags(src) == []


def test_shadowing_allowed():
    assert diags(wrap("let x: int = 1\n if true { let x: int = 2 }")) == []


def test_int_float_promotion_ok():
    assert diags(wrap("let x: float = 1")) == []


# ── SEM-001 Doppelte Definition ────────────────────────────────────────

def test_sem001_duplicate_let():
    ds = diags(wrap("let x: int = 1\n let x: int = 2"))
    assert rules(ds) == ["SEM-001"]


def test_sem001_duplicate_contract_fn():
    src = "contract C {\n    fn get() -> u64 { return 0 }\n    fn get() -> u64 { return 1 }\n}"
    assert "SEM-001" in rules(diags(src))


# ── SEM-002 Unbekanntes Symbol ──────────────────────────────────────────

def test_sem002_undefined_symbol():
    ds = diags(wrap("print(x)"))
    assert rules(ds) == ["SEM-002"]


# ── SEM-003/004 break/continue ausserhalb ─────────────────────────────

def test_sem003_break_outside_loop():
    assert "SEM-003" in rules(diags(wrap("break")))


def test_sem004_continue_outside_loop():
    assert "SEM-004" in rules(diags(wrap("continue")))


# ── SEM-005 return ausserhalb ──────────────────────────────────────────

def test_sem005_return_outside_function():
    assert "SEM-005" in rules(diags("return 1"))


# ── SEM-006/007 Typ-Mismatch ───────────────────────────────────────────

def test_sem006_let_type_mismatch():
    ds = diags(wrap("let x: int = \"s\""))
    assert "SEM-006" in rules(ds)


def test_sem006_int_not_assignable_to_int_from_float():
    assert "SEM-006" in rules(diags(wrap("let x: int = 1.5")))


def test_sem007_return_type_mismatch():
    src = "contract C {\n    fn f() -> int { return \"s\" }\n}"
    assert "SEM-007" in rules(diags(src))


# ── SEM-008/009 Built-ins ──────────────────────────────────────────────

def test_sem008_builtin_arity():
    assert "SEM-008" in rules(diags(wrap("len(1, 2)")))


def test_sem009_builtin_param_type():
    assert "SEM-009" in rules(diags(wrap("range(\"x\")")))


# ── SEM-010 Doppelter Parameter ────────────────────────────────────────

def test_sem010_duplicate_parameter():
    src = "contract C {\n    fn f(a: int, a: int) { }\n}"
    assert "SEM-010" in rules(diags(src))


# ── SEM-011/012 Ausdruecke und Bedingungen ─────────────────────────────

def test_sem011_string_plus_int():
    assert "SEM-011" in rules(diags(wrap("let x = \"s\" + 1")))


def test_sem012_condition_must_be_boolable():
    assert "SEM-012" in rules(diags(wrap("if \"hello\" { }")))


# ── Strict-Modus ────────────────────────────────────────────────────────

def test_strict_mode_raises():
    with pytest.raises(BreakOutsideLoopError):
        TypeChecker().check(parse(wrap("break")))


def test_strict_type_mismatch_raises():
    with pytest.raises(TypeMismatchError):
        TypeChecker().check(parse(wrap("let x: int = \"s\"")))
