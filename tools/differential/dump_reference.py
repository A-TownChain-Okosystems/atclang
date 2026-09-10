# Copyright (c) 2026 Michael Wroblewski — Apache-2.0
"""
SCR-0084 — Differential-Harness: Python-Referenz -> kanonisches AST-JSON.
Generiert crates/atc-core/differential/expected/*.json aus dem Reference-
Parser (frontend). Das Rust-Canonical-Core-Testsuite vergleicht bytgleich.
"""
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from atclang.frontend.lexer.lexer import ATCLexer
from atclang.frontend.parser.parser import ATCParser

CORPUS = os.path.join(ROOT, "crates", "atc-core", "differential", "corpus")
EXPECTED = os.path.join(ROOT, "crates", "atc-core", "differential", "expected")


def node_to_obj(n):
    cn = type(n).__name__
    if cn == "IntLiteral":
        return {"kind": "IntLiteral", "value": n.value}
    if cn == "Identifier":
        return {"kind": "Identifier", "name": n.name}
    if cn == "UnaryOp":
        return {"kind": "UnaryOp", "op": n.op, "operand": node_to_obj(n.operand)}
    if cn == "BinaryOp":
        return {"kind": "BinaryOp", "op": n.op, "left": node_to_obj(n.left), "right": node_to_obj(n.right)}
    if cn == "FunctionCall":
        return {"kind": "FunctionCall", "args": [node_to_obj(a) for a in n.args], "target": node_to_obj(n.target)}
    if cn == "TypeAnnotation":
        return {"kind": "TypeAnnotation", "name": n.name, "params": []}
    if cn == "LetStatement":
        return {
            "kind": "LetStatement",
            "is_const": bool(n.is_const),
            "name": n.name,
            "type_hint": None if n.type_hint is None else node_to_obj(n.type_hint),
            "value": None if n.value is None else node_to_obj(n.value),
        }
    if cn == "Program":
        return {"kind": "Program", "statements": [node_to_obj(s) for s in n.statements]}
    raise SystemExit(f"unerwarteter AST-Knoten im Subset: {cn} — Subset erweitern")


def dump(corpus_dir, expected_dir):
    os.makedirs(expected_dir, exist_ok=True)
    ok = 0
    for f in sorted(os.listdir(corpus_dir)):
        if not f.endswith(".atc"):
            continue
        src = open(os.path.join(corpus_dir, f), encoding="utf-8").read()
        tokens = ATCLexer(src).tokenize()
        prog = ATCParser(tokens).parse_program()
        out = json.dumps(node_to_obj(prog), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        stem = f[:-4]
        open(os.path.join(expected_dir, stem + ".json"), "w", encoding="utf-8").write(out + "\n")
        print(f"{f}: OK ({len(out)} Zeichen)")
        ok += 1
    return ok


if __name__ == "__main__":
    n = dump(CORPUS, EXPECTED)
    print(f"Erwartungsdateien: {n}")
