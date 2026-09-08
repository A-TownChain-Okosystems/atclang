# Changelog — ATCLang

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-09-07

### Added
- **Gate G2 (Semantics):** `src/atclang/semantics/` TypeChecker-Subsystem mit Regeln SEM-001..SEM-012.
- **Spezifikation:** Normative Spezifikationen `specs/semantics/SPEC.md` und maschinenlesbare `registry.json`.
- **Governance & Standards:** Dokumentations-Konformität mit `ATC-STD-README-001` und `ATC-STD-MD-001`.
- **Pflichtdokumente:** `STATUS.md`, `CONTRIBUTING.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `AGENTS.md`, `CODE_OF_CONDUCT.md`, `GOVERNANCE.md`.

### Fixed
- **Parser:** `parse_type` Korrektur für typ-annotierte Let-Bindings und Rückgabewerte.
- **Compliance:** Behebung aller MD-01..MD-10 Quality Gate Verstöße.

### Changed
- **Compiler:** `compile_source` führt standardmäßig semantischen Gate-Check aus.
