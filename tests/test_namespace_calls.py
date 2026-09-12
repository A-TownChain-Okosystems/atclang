# -*- coding: utf-8 -*-
"""Regression: Namespace-Calls mit Keyword-Member (Issue: silent wrong semantics).

Vor dem Fix (12.09.2026) zerfiel `ATCoin::transfer(a, b, c)` in Statement-
und let-Position in ZWEI Statements: `Identifier('ATCoin')` + ein folgender
`FunctionCall('transfer')` — der Namespace-Qualifier ging verloren und die
Semantik aenderte sich schweigend. Ursache: der Parser akzeptierte nach `::`
nur die Modifier-Keywords new/delete/deploy/call; transfer/mint/burn/...
sind aber reservierte Woerter und wurden abgewiesen.

ATC-Ref: ATC-92 (Language Spec) — Namespace-Zugriff `X::member`.
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from atclang.frontend.parser.parser import parse


def _first_stmt(src):
    ast = parse(src)
    return ast.statements[0].functions[0].body[0]


def test_namespace_call_in_statement_position():
    st = _first_stmt(
        "contract C {\n"
        "    fn f(a: Address, b: Address, c: u256) {\n"
        "        ATCoin::transfer(a, b, c)\n"
        "    }\n"
        "}\n"
    )
    assert type(st).__name__ == "ExprStatement"
    call = st.expr
    assert type(call).__name__ == "FunctionCall"
    ns = call.target
    assert type(ns).__name__ == "NamespaceAccess"
    assert ns.parts == ["ATCoin", "transfer"], ns.parts
    assert len(call.args) == 3


def test_namespace_call_in_let_initializer():
    st = _first_stmt(
        "contract C {\n"
        "    fn f(a: Address) -> bool {\n"
        "        let ok = ATCoin::transfer(a, a, 1)\n"
        "        return ok\n"
        "    }\n"
        "}\n"
    )
    assert type(st).__name__ == "LetStatement"
    call = st.value
    assert type(call).__name__ == "FunctionCall"
    assert type(call.target).__name__ == "NamespaceAccess"
    assert call.target.parts == ["ATCoin", "transfer"], call.target.parts


def test_atc_std_namespace_still_intact():
    st = _first_stmt(
        "contract C {\n"
        "    fn f() {\n"
        "        let h = ATC::Hash::sha256(\"x\")\n"
        "    }\n"
        "}\n"
    )
    assert type(st).__name__ == "LetStatement"
    call = st.value
    assert type(call).__name__ == "FunctionCall"
    assert call.target.parts == ["ATC", "Hash", "sha256"], call.target.parts


def test_chained_member_after_keyword_method():
    """ATC::Net::P2P::connect — Member nach Keyword-Kette (connect ist Keyword)."""
    st = _first_stmt(
        "contract C {\n"
        "    fn f() -> bool {\n"
        "        return ATC::Net::P2P::connect(1)\n"
        "    }\n"
        "}\n"
    )
    ret = st
    assert type(ret).__name__ == "ReturnStatement"
    call = ret.value
    assert type(call).__name__ == "FunctionCall"
    assert call.target.parts == ["ATC", "Net", "P2P", "connect"], call.target.parts
