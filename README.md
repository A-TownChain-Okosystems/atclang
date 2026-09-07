# ATCLang — A-TownChain Systemsprache (1.0 REBUILD)

ATCLang ist die proprietäre System- und Contract-Sprache der A-TownChain: Lexer, Parser, Type-Checker, Compiler, Bytecode, ATVM, Runtime, ABI, Stdlib — von Grund auf eigenständig, kein POSIX-Klon.

**Baseline v1.0 (AD-022):** Rust Canonical Core + Python Reference/Tooling — [docs/ATCLANG_BASELINE_V1.md](docs/ATCLANG_BASELINE_V1.md) · Gates G0-G19, kein Freeze vor G18 (Security Audit).

**Rebuild-Status (06.09.2026, AD-019):** Phase-1-Konsolidierung abgeschlossen — eine Implementierung je Verantwortlichkeit unter src/atclang/ (Frontend, Compiler, VM, Runtime, Stdlib verifiziert; 22.617 LOC). Zielarchitektur 1.0: docs/ATCLANG_1.0_ARCHITECTURE.md (ARCHITECTURE FREEZE: GO). Subsystem-Implementierungen und Conformance: Phase 2.

    pip install -e . && python -m pytest    # Pipeline-Check
    python -c "from atclang.compiler.compiler import compile_source; compile_source('let x = 1;')"

Architekturzentren: src/ (Implementierung) · specs/ (normativ) · docs/ (erklärend) · tests/ (mit Fixtures) · examples/ · tools/. Keine zweite VM, keine zweite Stdlib, kein zweiter Parser.

---

## ATC Compliance & Governance (ATC-STD-201 / 202 / 203)

**ATC COMPLIANCE: R4** — auditiert am 2026-09-07 (atc-repo-audit; R-Level aus `.atc/repository.yaml`).
Architekturentscheidungen: zentral im [DECISIONS_REGISTER](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/DECISIONS_REGISTER.md) (AD-Nummern verbindlich; lokale Entscheidungen in `docs/decisions/`).

- **Purpose:** ATCLang — die proprietare Sprache des Oekosystems (Lexer, Parser, Compiler, ATVM).
- **Scope:** Layer L0, Domain language — atclang als CORE in der 23-Repo-Landschaft (AD-024/026).
- **Architecture:** Rust-First-Baseline (AD-022): Compiler→ATC-IR→Verifier→ATVM; Python als Referenz fuer Differential Testing. G1 Language Specification bestanden (07.09.), naechstes Gate G2 Semantics.
- **Features:** 63 Tokens, 76 Keywords, 28 Parser-Produktionen, 50 AST-Knoten, 9 Stdlib-Module; specs/language/SPEC.md + registry.json.
- **Installation:** Modul-Build je Sprache (rust); Integration via Monorepo-Workspace (a-townchain-os, sync_modules.py).
- **Development:** Conventional Commits; Governance-Regeln aus atc-standards; Naming gemaess ATC-STD-000 §7.
- **Testing:** pytest-Pipeline; Differential Testing Rust-vs-Python als verbindliches Conformance-Kriterium (AD-021/022).
- **Security:** SECURITY.md; S-Klasse S4; ATC-STD-203 Release-Gates; Emergency-Prozess ATC-STD-000 §32.
- **Roadmap:** Einordnung in die Lauffaehigkeits-Roadmap M1-M8 (AD-027) und Bauhierarchie L0-L7 (AD-026).
- **Version:** CHANGELOG.md; SemVer; Releases als ATC-REL-X.Y.Z.
- **License:** Proprietaer — All Rights Reserved, Michael Wroblewski / ShivaCore / A-TownChain-Okosystems (ATC-LIC/ATS-LIC).
