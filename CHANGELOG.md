# Changelog — atclang

## [Unreleased] — 2026-09-07 — Gate G2 (Semantics) PASSED
- **feat(G2):** `src/atclang/semantics/` — unabhaengiges TypeChecker-Subsystem
  (AD-022-Philosophie: validiert nur, erzeugt nichts): Scope-Kette,
  Shadowing, SEM-001…012 (Duplicates, undefinierte Symbole,
  break/continue/return-Platzierung, Typ-Regeln mit int→float-Promotion,
  Built-in-Signaturen der 13 Funktionen), non-werfende
  `check_and_report` + strict `check` (CompileError-Subklassen) +
  `analyze_source`.
- **fix(parser):** `parse_type` gab nicht-generische Typ-Annotationen als
  None zurueck (return fehlte) — alle `let x: T`-/`-> T`-Annotationen
  fielen bisher aus dem AST.
- **feat(compiler):** `compile_source(..., semantic_check=True)` fuehrt
  das semantische Gate vor dem Codegen aus.
- **specs:** `specs/semantics/SPEC.md` (normativ) + `registry.json`
  (maschinenlesbar, 12 Regeln, Builtins, API-Vertrag).
- **tests:** `tests/test_semantics.py` — 20 Tests, 20 PASS; Referenz-Korpus
  (4 parsbare Beispiele) semantisch CLEAN; Voll-Suite ohne Regressionen
  (32 pre-existing Bytecode-API-Fails unveraendert).

# Changelog — atclang

## [Unreleased] — 2026-09-07
- Governance-Ueberarbeitung nach ATC-STD-201/202/203: .atc-Metadaten
  (repository/ownership/lifecycle/compliance.yaml), SECURITY.md, CODEOWNERS,
  docs/REPOSITORY_STANDARD.md, Governance-CI (governance-ci.yml),
  ATC-COMPLIANCE-Anhang im README. R-Level: R4.
