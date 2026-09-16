# ATC ATCLang

> System- und Smart-Contract-Sprache des A-TownChain-Ökosystems mit Compiler, ATC-VM-Bytecode und Standardbibliothek.

[![ATC COMPLIANCE](https://img.shields.io/badge/ATC%20COMPLIANCE-R4%20Governance-blue)](./SECURITY.md)

**Project:** `atclang`  
**Organization:** `A-TownChain-Okosystems`  
**Status:** `development`  
**Version:** `1.0.0`  
**License:** `Apache-2.0` (see `LICENSE`)

## Purpose

ATCLang provides the language and contract-development layer for the A-TownChain ecosystem. Its purpose is to define source syntax, semantics, compilation and contract-facing tooling while keeping chain-bearing infrastructure outside the language implementation.

## Scope

The repository covers lexical analysis, parsing, semantic and type validation, intermediate representation, bytecode generation, ABI definitions, standard-library components, reference testing and integration with the ATC-VM boundary. It does not define the blockchain itself.

## Overview

ATCLang is the language and contract-development layer of A-TownChain. It covers lexical analysis, parsing, semantic validation, compilation, bytecode generation, ABI definitions, and language standard-library components.

The architectural boundary is explicit:

```text
ATCLang
  │ language, contracts, compilation
  ▼
ATC-VM
  │ deterministic bytecode execution boundary
  ▼
A-TownChain
  │ sovereign deterministic L1 / chain infrastructure
  ▼
Rust infrastructure
```

ATCLang does **not** define the chain itself and does not replace the ATC-VM or the Rust chain infrastructure. Chain-bearing infrastructure remains outside the language layer.

## Features

- `.atc` lexical analysis, parsing and AST construction.
- Semantic and type validation.
- Intermediate representation and bytecode compilation.
- ABI and contract-facing tooling.
- Standard-library components.
- Rust-first production architecture with Python limited to reference, test and fuzzing roles.
- Differential testing and fail-closed security-boundary validation.

## Status

`development` means the repository is under active development. Language or semantic gates passing does not imply `APPROVED`, `AUDITED`, or `PRODUCTION_READY` status for the complete ecosystem.

There is no current Mainnet/Production claim in this README. Release readiness is determined by the applicable governance, validation, security, and release gates.

## Architecture

### Core responsibilities

- Lexer and parser for `.atc` source files.
- AST and semantic/type validation.
- Intermediate representation and bytecode compilation.
- ABI generation and contract-facing tooling.
- ATCLang standard-library modules.
- Differential/reference testing where supported by the repository implementation.

### Repository components

- `src/atclang/frontend/` — lexer, tokenizer and parser.
- `src/atclang/semantics/` — semantic and type-checking logic.
- `src/atclang/compiler/` — IR generation, code generation, bytecode and ABI tooling.
- `src/atclang/vm/` — VM-related language tooling where present.
- `src/atclang/runtime/` — runtime integration.
- `src/atclang/stdlib/` — language standard library.

## Requirements

- Python >= 3.10
- setuptools >= 68
- Git >= 2.30
- Rust tooling is required for repository components implemented in Rust and for the canonical production execution path.

## Installation

```bash
git clone https://github.com/A-TownChain-Okosystems/atclang.git
cd atclang
python3 -m pip install -e .
```

## Usage

Example compiler invocation from the Python API:

```python
from atclang.compiler.compiler import compile_source

source_code = """
contract Token {
    state balance: u64 = 100
    fn get_balance() -> u64 {
        return self.balance
    }
}
"""

compiled = compile_source(source_code, semantic_check=True)
print(compiled)
```

The exact supported language surface is defined by the repository's normative specifications and implementation, not by this README.

## Testing

```bash
python3 -m unittest discover tests
```

A passing local test suite is evidence for that test execution only. It does not by itself establish audit, release, or production readiness.

## Development & Governance

Development follows the organization governance defined by `ATC-STD-000` and the repository's applicable standards and agent instructions.

The standards taxonomy uses family-scoped canonical IDs:

```text
ATC-STD-F{family}-{sequence}
```

For example, `ATC-STD-F03-001` identifies sequence `001` within Family `F03`. Legacy numeric or domain-specific IDs remain historical identifiers during migration and are not silently renumbered or reused.

Canonical standard allocation is controlled by the standards registry and governance process. A README must not invent or autonomously allocate standard IDs.

## Compliance status terminology

These states are intentionally distinct:

- **APPROVED** — formally approved by the applicable governance process.
- **IMPLEMENTED** — the relevant implementation exists.
- **AUDITED** — the relevant audit has been performed and recorded.
- **PRODUCTION_READY** — all required release gates have passed.

One state must never be inferred from another.

## Security

Security issues must not be disclosed through public GitHub Issues. Follow the repository `SECURITY.md` and the organization's approved security-disclosure process. The CI audit is fail-closed for known insecure reference primitives and release-blocking findings.

## Roadmap

The authoritative development roadmap is `ROADMAP.md`. Current release-blocking work includes removal or fail-closed isolation of insecure Python reference primitives, proof of the Rust canonical production boundary, deterministic capability enforcement, differential tests and security evidence.

## Documentation

- `docs/` — project documentation and specifications.
- `specs/` — language and semantic specifications where present.
- `ARCHITECTURE.md` — repository architecture.
- `STATUS.md` — current repository status.
- `ROADMAP.md` — development roadmap.
- `TODO.md` — evidence-backed outstanding work.
- `SPRINTS.md` — active implementation sprints.
- `docs/wiki/README.md` — repository knowledge base.
- `docs/audits/` — audit findings and closure evidence.

## Repository Structure

```text
/
├── docs/
├── examples/
├── specs/
├── src/
├── tests/
├── tools/
├── AGENTS.md
├── AGENT_MANIFEST.md
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CODEOWNERS
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── GOVERNANCE.md
├── LICENSE
├── README.md
├── ROADMAP.md
├── SECURITY.md
└── STATUS.md
```

## Contributing

Please read `CONTRIBUTING.md`, `AGENTS.md`, and the applicable governance documentation before making changes.

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
  primary_language: Python/Rust
governance:
  security_class: S4
  criticality: CRITICAL
-->
