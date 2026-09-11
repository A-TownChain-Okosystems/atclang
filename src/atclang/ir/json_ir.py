# Copyright (c) 2026 Michael-Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""JSON-IR: AST -> normalisierte, kanonisch serialisierbare Zwischendarstellung.

Zweck (Sprint 2.3, Tools-Differential): die IR ist die stabile, sprach-
versionsunabhaengige Basis fuer Differential-Tests, Formatter, Linter und
spaetere Backend-Targets (VM, native). Sie ist bewusst schlicht — ein
Lowering-Schritt zwischen AST und Bytecode, kein SSA.

Regeln: node = {kind, …felder}; Kinder unter 'body'/'args'; kanonische
Serialisierung (sortierte Keys) macht IR-Hashes vergleichbar — gleicher
AST MUSS gleiche IR-Hashes ergeben.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any, Dict


class IRValidationError(Exception):
    pass


def to_json_ir(ast: Any) -> Dict[str, Any]:
    """ASTNode-Objekt (dataclass-Baum) -> IR-Dict."""
    return _convert(ast)


def _convert(node: Any) -> Any:
    if hasattr(node, "__dict__"):
        kind = type(node).__name__
        out: Dict[str, Any] = {"kind": kind}
        for key, val in vars(node).items():
            if key.startswith("_") or callable(val):
                continue
            if isinstance(val, (list, tuple)):
                out[key] = [_convert(v) for v in val]
            elif hasattr(val, "__dict__"):
                out[key] = _convert(val)
            elif isinstance(val, (int, float, str, bool)) or val is None:
                out[key] = val
        return out
    if isinstance(node, (list, tuple)):
        return [_convert(v) for v in node]
    return node


def validate_ir(ir: Any) -> None:
    if not isinstance(ir, dict) or "kind" not in ir:
        raise IRValidationError("IR-Knoten ohne 'kind'")
    for key, val in ir.items():
        if key.startswith("_"):
            raise IRValidationError(f"Privatfeld im IR-Knoten: {key}")
        if callable(val):
            raise IRValidationError(f"Funktion im IR-Knoten: {key}")


def ir_hash(ir: Dict[str, Any]) -> str:
    """Kanonischer IR-Hash (Vergleichbarkeit, Differential-Gates)."""
    return "0x" + hashlib.sha256(
        json.dumps(ir, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
