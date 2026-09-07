# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
"""ATCLang Semantics (Subsystem) — unabhaengige semantische Analyse (Gate G2).

Normativ: specs/semantics/SPEC.md. Vertrauensgrenze: Der TypeChecker
validiert nur — er erzeugt keinen Code und mutiert nichts (AD-022).
"""
from atclang.semantics.type_checker import (
    BUILTIN_SIGNATURES,
    SemanticDiagnostic,
    TypeChecker,
    analyze_source,
)

__all__ = ["BUILTIN_SIGNATURES", "SemanticDiagnostic", "TypeChecker", "analyze_source"]
