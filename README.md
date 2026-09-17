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
verifizierbar und auf die ATC-VM als Konsens-Ziel kompiliert. Diese Referenz-
Implementierung definiert Semantik, Bytecode-Encoding und Sicherheits-Gates
(verifizierte Konsens-Tauglichkeit statt Vertrauen in Audits).

## Features

- ATCLang-Frontend mit deterministischer Semantik (Konsens-Pflicht)
- Rust-Consensus-Core (`crates/atc-core`): Bytecode-Verifizierer mit
  fail-closed Bounds-Checking (Stack, Locals, Functions)
- Python-Referenz-VM (`src/atclang/vm`) für Tests und Simulation
- Security-Gate (Static Analysis, fail-closed): Verbots-Import- und
  Hostcall-Detektion auf Contract-Quellen
- Determinism-Gate (SCR-0126 Checker v2, allowlist-geprüft)

## Architecture boundary

**Rust is canonical**: `crates/atc-core` ist der produktive Konsens-Kern
(Bytecode-Verifizierer, Differential-Test-Ziel). Die Python-Referenz-Pipeline
(Former: `src/atclang`) ist seit 2026-09-17 vollstaendig dokumentiert unter
`docs/reference/python/` und aus dem Repository entfernt — Rust-only.

ATCLang is the language and contract-development layer of A-TownChain. The repository deliberately uses a dual-stack model:

```text
ATCLang source
    │
    ├── Python reference implementation / SDK / differential tests
    │
    └── Rust canonical production implementation
              │
              ▼
           ATC-VM
              │
              ▼
        A-TownChain L1
```

Rust is the production/canonical language for consensus-critical compiler, verifier, VM, runtime, ABI/artifact validation and security components. Python is reference/test tooling and must never silently become the production consensus implementation.

## Status

`development` means the repository is under active development. The current repository is **not production-ready**. Passing a local test suite, a language gate, or a static audit does not imply `APPROVED`, `AUDITED`, or `PRODUCTION_READY` status.

The current release state is determined by the applicable standards, conformance, security, reproducibility and release gates. Current CI runtime evidence is explicitly treated as unavailable until a current GitHub Actions run is available.

## Components

- `src/atclang/frontend/` — Python reference lexer, tokenizer, parser and AST.
- `src/atclang/semantics/` — reference semantic/type checking.
- `src/atclang/compiler/` — reference compiler and bytecode generation.
- `src/atclang/vm/` — reference VM only; not a production trust anchor.
- `src/atclang/runtime/` — reference runtime integration.
- `src/atclang/stdlib/` — reference standard library.
- `crates/atc-core/` — Rust canonical core currently under incremental implementation and differential conformance testing.
- `specs/` — normative language, ABI, bytecode, IR, semantics, VM and standard-library specifications.
- `tools/` — deterministic/differential and CI-independent audit tooling.

## Requirements

- Python >= 3.10
- setuptools >= 68
- Git >= 2.30
- Rust stable for the canonical core

## Installation

```bash
git clone https://github.com/A-TownChain-Okosystems/atclang.git
cd atclang
cargo build --release --manifest-path crates/atc-core/Cargo.toml
cargo install --path crates/atc-core   # installs the `atc` CLI
```

CLI (Frontend-Gate: lex -> parse -> kanonische AST-JSON):

```bash
atc compile differential/corpus/calls.atc   # kanonisches JSON auf stdout
atc check differential/corpus/calls.atc     # stille Validierung (Exit-Code)
```

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

The Python VM contains reference-only boundaries and must not be used as a production cryptographic, authentication, network or RPC trust anchor. Consensus execution must use the canonical Rust path and reject non-deterministic host capabilities.

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
  reference_language: Python
governance:
  security_class: S4
  criticality: CRITICAL
-->
