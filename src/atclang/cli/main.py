# Copyright (c) 2026 Michael-Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""atc-CLI: Kompilieren, Pruefen, IR-Dump, Artifacts schreiben.

    atc compile <file.atc> [--profile consensus] [--out artifact.atca]
    atc check   <file.atc> [--profile consensus]     # SecurityGate + Semantik
    atc ir      <file.atc> [--hash]                  # JSON-IR + Hash
Exit-Codes: 0 = OK, 1 = Fehler (CI-tauglich; Gate G0-Anbindung).
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys

from atclang.compiler.compiler import compile_source
from atclang.security import SecurityGate
from atclang.ir import to_json_ir, ir_hash
from atclang.artifact import CompiledArtifact


def _load(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def cmd_compile(args) -> int:
    source = _load(args.file)
    profile = args.profile
    if not SecurityGate().check(source, profile):
        print(f"SECURITY-GATE FAIL (Profil {profile}) — siehe 'atc check'", file=sys.stderr)
        return 1
    result = compile_source(source)
    module = getattr(result, "module", result)
    artifact = CompiledArtifact(
        name=module.name, entry=args.file,
        compiler_version=getattr(module, "version", b"\x01\x00\x00").hex() or "1.0.0",
        language_standard="ATC-92 v1.0.0", profile=profile,
        source_sha256="0x" + hashlib.sha256(source.encode()).hexdigest(),
        bytecode={"functions": sorted(module.functions.keys()),
                  "exports": list(getattr(module, "exports", []))},
        abi=[], contract_standards=[],
    )
    if args.out:
        with open(args.out, "wb") as fh:
            fh.write(artifact.to_bytes())
        print(f"OK: {args.file} -> {args.out} ({artifact.artifact_id[:18]}…)")
    else:
        print(json.dumps({"artifact_id": artifact.artifact_id,
                          "functions": sorted(module.functions.keys())}, indent=2))
    return 0


def cmd_check(args) -> int:
    source = _load(args.file)
    gate = SecurityGate()
    findings = gate.analyse(source, args.profile)
    for f in findings:
        print(f"[{f.severity.value.upper()}] {f.rule} Zeile {f.line}: {f.message}", file=sys.stderr)
    passed = gate.check(source, args.profile)
    try:
        compile_source(source)
    except Exception as exc:                                  # Semantik-Gate
        print(f"SEMANTIK FEHLER: {exc}", file=sys.stderr)
        return 1
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


def cmd_ir(args) -> int:
    source = _load(args.file)
    result = compile_source(source)
    ast = getattr(result, "ast", None) or getattr(result, "program", None)
    if ast is None:
        print("Kein AST verfuegbar", file=sys.stderr)
        return 1
    ir = to_json_ir(ast)
    if args.hash:
        print(ir_hash(ir))
    else:
        print(json.dumps(ir, sort_keys=True, indent=2))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="atc", description="ATCLang Toolchain (ATC-92)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_compile = sub.add_parser("compile", help="Quellcode -> .atca-Artefakt")
    p_compile.add_argument("file")
    p_compile.add_argument("--profile", default="consensus", choices=["consensus", "off_chain", "debug"])
    p_compile.add_argument("--out")
    p_compile.set_defaults(func=cmd_compile)

    p_check = sub.add_parser("check", help="Security- + Semantik-Gate")
    p_check.add_argument("file")
    p_check.add_argument("--profile", default="consensus", choices=["consensus", "off_chain", "debug"])
    p_check.set_defaults(func=cmd_check)

    p_ir = sub.add_parser("ir", help="JSON-IR-Dump")
    p_ir.add_argument("file")
    p_ir.add_argument("--hash", action="store_true")
    p_ir.set_defaults(func=cmd_ir)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
