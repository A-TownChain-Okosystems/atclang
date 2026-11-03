# ATC ATCLang

> System- und Smart-Contract-Sprache des A-TownChain-Ökosystems mit Compiler, ATC-VM-Bytecode und Standardbibliothek.

**Project:** `atclang`  
**Organization:** `A-TownChain-Okosystems`  
**Status:** `development`  
**Version:** `1.0.0`  
**License:** `Apache-2.0` (see `LICENSE`)

![ATC COMPLIANCE](https://img.shields.io/badge/ATC%20COMPLIANCE-R4%20%C2%B7%20ATC--STD--201%2F202%2F203-brightgreen)

## Purpose

ATCLang ist die Vertragssprache des A-TownChain-Ökosystems: deterministisch,
verifizierbar und auf die ATC-VM als Konsens-Ziel ausgerichtet. Der kanonische
Implementierungspfad ist Rust unter `crates/atc-core/`; der aktuell umgesetzte
Teilumfang befindet sich weiterhin in Entwicklung. Normative Semantik und
Bytecode-/ABI-Verträge werden durch versionierte Spezifikationen definiert.
Weder vorhandener Quellcode noch bestandene Tests begründen allein eine
Konsens- oder Produktionsfreigabe.

## Features

- ATCLang-Frontend mit deterministischer Semantik (Konsens-Pflicht)
- Rust-Canonical-Core (`crates/atc-core`): Bytecode-Verifizierer mit
  fail-closed Bounds-Checking (Stack, Locals, Functions)
- Rust-only implementation path; Python reference VM removed from the active repository on 2026-09-17
- Security-Gate (Static Analysis, fail-closed): Verbots-Import- und
  Hostcall-Detektion auf Contract-Quellen
- Determinism-Gate (SCR-0126 Checker v2, allowlist-geprüft)

## Architecture boundary

**Rust is canonical**: `crates/atc-core` ist der kanonische Rust-Pfad für den
aktuell implementierten Teilumfang (Bytecode-Verifizierer, Differential-Test-Ziel);
die vollständige Produktions- und Konsensfreigabe ist weiterhin offen. Die Python-Referenz-Pipeline
(Former: `src/atclang`) ist seit 2026-09-17 vollstaendig dokumentiert unter
`docs/reference/python/` und aus dem Repository entfernt — Rust-only.

ATCLang is the language and contract-development layer of A-TownChain. The repository documents a **Rust-only active implementation path**. The former Python reference pipeline was removed from the active tree on 2026-09-17; older documentation and historical tests that mention it must not be read as a current runtime component.

```text
ATCLang source
    ↓
Rust compiler / verifier / artifact validation
    ↓
ATC-VM (canonical implementation: a-townchain/components/vm)
    ↓
A-TownChain chain runtime
```

Consensus-critical language semantics and artifact validation must be defined by the current Rust source and canonical standards. Python tooling is not an active production implementation unless reintroduced through an explicit reviewed change.

## Status

`development` means the repository is under active development. The current repository is **not production-ready**. Passing a local test suite, a language gate, or a static audit does not imply `APPROVED`, `AUDITED`, or `PRODUCTION_READY` status.

The current release state is determined by the applicable standards, conformance, security, reproducibility and release gates. Current CI runtime evidence is explicitly treated as unavailable until a current GitHub Actions run is available.

## Components

- `crates/atc-core/` — kanonischer Rust-Compiler-/Verifier-Core für den derzeit implementierten Teilumfang; weiterhin in Entwicklung.
- `docs/reference/python/` — archivierte, aus dem früheren Python-Quellbestand erzeugte Referenzdokumentation; kein aktiver Runtime-Code.
- `tools/` — Python-basierte Audit-, Conformance- und CI-Werkzeuge; keine Konsens-Ausführungsinstanz.
- `specs/` — normative language, ABI, bytecode, IR, semantics, VM and standard-library specifications.

## Requirements

- Rust stable — Build und Tests des kanonischen Rust-Cores.
- Python >= 3.10 und setuptools >= 68 — ausschließlich für Audit-/CI-Werkzeuge unter `tools/`.
- Git >= 2.30.

## Installation

```bash
git clone https://github.com/A-TownChain-Okosystems/atclang.git
cd atclang
cargo build --release --manifest-path crates/atc-core/Cargo.toml
cargo install --path crates/atc-core   # installs the `atc` CLI
```

CLI (Frontend + Lowering + Ausfuehrung):

```bash
atc compile differential/corpus/calls.atc   # kanonisches AST-JSON auf stdout
atc run programm.atc                       # kompiliert, verifiziert, fuehrt aus (Ergebnis auf stdout)
atc check differential/corpus/calls.atc     # stille Validierung (Exit-Code)
```

Ablaufmodell: top-level Statements bilden die implizite Entry-Funktion; eine
nutzerdefinierte `fn main` ist der Entry, wenn keine top-level Statements
existieren. Ausfuehrung ist eine deterministische i64-Stack-Maschine ueber
verifiziertem Bytecode: checked-Arithmetik (Overflow = Fehler, kein Wrap),
Division/0 statisch vom Verifizierer bzw. dynamisch als Laufzeitfehler
abgelehnt, feste maximale Aufruftiefe (1024, fail-closed statt Stack-Overflow).

## Testing

```bash
cargo test --manifest-path crates/atc-core/Cargo.toml
python3 tools/ci_independent_audit.py
```

A passing local test suite is evidence for that execution only. It does not establish release or production readiness.

## Governance and standards

Development follows `ATC-STD-000` and the repository's applicable standards. The canonical standards profile is `.atc/standards.yaml`; the central `atc-standards` registry remains the source of truth.

The standards taxonomy uses family-scoped canonical IDs. Standard IDs are not invented or autonomously allocated in this repository.

## Security

Die frühere Python-Referenzimplementierung wurde aus dem aktiven Quellbaum entfernt; unter `docs/reference/python/` verbleibt ausschließlich archivierte Dokumentation. Python-Skripte unter `tools/` dienen Audit-, Conformance- und CI-Zwecken und besitzen keine Runtime- oder Konsensautorität. Konsensrelevante Compiler- und Ausführungspfade müssen über den kanonischen Rust-Pfad laufen und nichtdeterministische Host-Capabilities fail-closed ablehnen.

Security issues must not be disclosed through public GitHub Issues. Follow `SECURITY.md` and the organization's approved security-disclosure process.

## Documentation

- `docs/` — architecture, conformance, release-gate and audit documentation.
- `specs/` — normative specifications.
- `ARCHITECTURE.md` — repository architecture summary.
- `STATUS.md` — current repository status.
- `ROADMAP.md` — development roadmap.
- `FILE_REGISTER.md` — generated file inventory.

## License

Apache License 2.0. See `LICENSE` for the complete license text.

## Repository Metadata

<!-- atc metadata block (ATC-STD-README-001 §14) -->
<!--
atc:
  standard: ATC-STD-README-001
  version: 1.0.0
repository:
  id: ATC-REPO-LANG-001
  name: atclang
  type: software
  status: development
ownership:
  organization: A-TownChain-Okosystems
technology:
  primary_language: Rust
  secondary_language: Python
  secondary_scope: audit, conformance, CI tooling
governance:
  security_class: S4
  criticality: CRITICAL
-->
