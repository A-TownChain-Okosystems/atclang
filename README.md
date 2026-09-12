# ATC ATCLang

> Apache-2.0e System- und Smart-Contract-Sprache des A-TownChain-Ökosystems mit Compiler, ATVM-Runtime und Standardbibliothek.

**Project:** atclang
**Organization:** A-TownChain-Okosystems
**Status:** `development`
**Version:** `1.0.0`
**License:** `Apache-2.0 — A-TownChain-Okosystems`

| ATC COMPLIANCE | ![Status](https://img.shields.io/badge/ATC--201%2F202%2F203-R4_COMPLIANT-00c853) R4 · Repository Governance (ATC-STD-201/202/203) · Audit: atc-repo-audit (CI-gated) |
|---|---|

## Overview

ATCLang ist die Apache-2.0e System- und Smart-Contract-Sprache der A-TownChain. Sie umfasst Lexer, Parser (100% Parse-Rate), Type-Checker (Semantik-Gate G2), Compiler, ATVM Bytecode-Interpreter, Runtime-Framework, ABI-Definitionen und eine 9-teilige Standardbibliothek (Chain, Crypto, Math, Primitives, Wallet, IO, Encoding, Collections, String).

ATCLang basiert auf dem Rust-Canonical-Core mit Python-Referenz-Tooling (AD-022) und stellt eine eigenständige Layer-L0-Sprachinfrastruktur ohne POSIX-Abhängigkeiten dar.

## Purpose

ATC ATCLang provides the canonical implementation of the ATCLang programming language and compiler within the A-TownChain ecosystem. It is responsible for:

- Lexikalische Analyse (63 Tokens, 76 Keywords) und AST-Parsierung (28 Produktionen, 50 AST-Knoten, 100% Parse-Rate).
- Semantische Validierung (Gate G2, TypeChecker, Regeln SEM-001 bis SEM-012).
- Intermediate Representation (ATC-IR) und Bytecode-Kompilierung für die ATVM execution engine.
- Bereitstellung der System-Standardbibliothek für Smart Contracts und Kernel-Treiber.

Davon hängen ab: `atc-vm`, `atc-contracts`, `a-townchain-os` sowie alle Smart-Contract- und Runtime-Komponenten im ATC-Ökosystem.

## Status

**Status:** `development` — Rebuild-Status v1.0 (AD-019/AD-022): Phase-1-Konsolidierung abgeschlossen (22.617 LOC). Gate G1 (Language Specification) und Gate G2 (Semantics) wurden erfolgreich bestanden. Die Entwicklung folgt den Stufen G0–G19 bis zum Security-Audit (G18) und Mainnet-Release (G19).

## Architecture

### Components

- `src/atclang/frontend/`: Lexer (Tokenizer) und Parser (AST-Erzeugung).
- `src/atclang/semantics/`: TypeChecker und semantische Regel-Engine (SEM-001..SEM-012).
- `src/atclang/compiler/`: IR-Generierung, Codegen, Bytecode und ABI-Generator.
- `src/atclang/vm/` & `src/atclang/runtime/`: ATVM Interpreter Engine und Kernel Driver Framework.
- `src/atclang/stdlib/`: Stdlib-Module (`chain`, `crypto`, `math`, `primitives`, `wallet`, `io`, `encoding`, `collections`, `string`).

### Data Flow

```text
ATCLang Quellcode (.atc)
      │
      ▼
  Lexer / Tokenizer (63 Tokens)
      │
      ▼
  Parser (AST, 28 Produktionen, 100% Parse-Rate)
      │
      ▼
  Semantik / TypeChecker (Gate G2, SEM-001..012)
      │
      ▼
  Compiler / Codegen (ATC-IR -> Bytecode & ABI)
      │
      ▼
  ATVM Runtime Interpreter
```

### Dependencies

| Component | Purpose | Required |
|---|---|---|
| Python >= 3.10 | Referenz-Tooling & Test-Suite | Yes |
| Rust toolchain | Canonical High-Performance Core | Optional (Phase 2) |
| setuptools >= 68 | Python-Paketierung | Yes |

## Features

- **Eigenständige Sprache:** Eigenes Grammatik-Design ohne externen Parser-Generator.
- **100% Parse-Rate:** Robuster Parser für komplexe Contract- und Systemkonstrukte.
- **Semantik-Gate G2:** Type-Checker mit Gültigkeits- und Typ-Promotion-Regeln (`int` -> `float`, Shadowing, Scope-Hierarchie).
- **Modulare Stdlib:** Vorinstallierte Module für Kryptographie, Chain-State, Mathedominanz und Speicherverwaltung.
- **Differential Testing:** Test-Vergleich zwischen Python-Referenz und Rust-Core (AD-021/AD-022).

## Repository Structure

```text
/
├── docs/                # Projektdokumentation und Baseline-Spezifikationen
├── examples/            # ATCLang Referenzprogramme (.atc)
├── specs/               # Normative Sprach- und Semantik-Spezifikationen
├── src/                 # ATCLang Quellcode (Frontend, Compiler, VM, Runtime, Stdlib)
├── tests/               # Testsuite (Semantik, Bytecode, ABI)
├── tools/               # Hilfswerkzeuge
├── AGENTS.md            # AI Agent Instructions
├── AGENT_MANIFEST.md    # Agenten-Identität & Compliance-Mandat
├── ARCHITECTURE.md      # Technische Architektur
├── CHANGELOG.md         # Änderungshistorie
├── CODEOWNERS           # Repository-Eigentümer
├── CODE_OF_CONDUCT.md   # Verhaltenskodex
├── CONTRIBUTING.md      # Beitragsrichtlinien
├── GOVERNANCE.md        # Repository-Governance
├── LICENSE              # Lizenzbestimmungen
├── README.md            # Einstiegsdokumentation
├── ROADMAP.md           # Entwicklungs-Roadmap
├── SECURITY.md          # Sicherheitsrichtlinien
└── STATUS.md            # Maschinenlesbarer Status
```

## Requirements

- Python >= 3.10
- setuptools >= 68
- Git >= 2.30

## Installation

### Pipeline-Setup

```bash
git clone https://github.com/A-TownChain-Okosystems/atclang.git
cd atclang
pip install -e .
```

## Configuration

Keine zusätzliche Laufzeit-Konfiguration erforderlich. Der Compiler kann direkt über das CLI oder als Python-Bibliothek aufgerufen werden.

## Usage

Kompilierung eines Beispiels:

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
print("Bytecode erzeugt:", compiled)
```

## Development

Entwicklungsarbeiten folgen den Vorgaben von ATC-STD-000 und ATC-STD-201.

- Code-Style: PEP 8 für Python, Rust Standard Style für Rust.
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`).
- Governance: Architekturentscheidungen werden über AD-Records und SCR-Anträge geregelt.

## Testing

Ausführen der gesamten Testsuite:

```bash
python3 -m unittest discover tests
# Erwartetes Ergebnis: PASS (Semantik- und Bytecode-Tests)
```

## Security

Security issues must not be disclosed publicly through GitHub Issues.

Sicherheitsrelevante Schwachstellen sind umgehend über den offiziellen Sicherheitsmeldeprozess (ATC-STD-203, `SECURITY.md`) zu melden. Klassifikation: S4.

## Documentation

Vertiefende Dokumentation befindet sich in folgenden Verzeichnissen:

- `docs/ATCLANG_1.0_ARCHITECTURE.md` — Zielarchitektur v1.0
- `docs/ATCLANG_BASELINE_V1.md` — Baseline-Spezifikation (AD-022)
- `specs/language/SPEC.md` — Normative Sprachspezifikation
- `specs/semantics/SPEC.md` — Normative Semantikspezifikation (Gate G2)
- `ARCHITECTURE.md` — Systemarchitektur
- `STATUS.md` — Aktueller Projektstatus

## Governance

Dieses Repository unterliegt den Governance-Regeln der A-TownChain-Organisation (ATC-STD-000 v1.3.0, ATC-ENT-001..015). Architektur- und Sicherheitsänderungen erfordern eine Formal-Freigabe des Owners.

## Standards & Compliance

Dieses Repository erfüllt die folgenden A-TownChain-Standards:

| Standard | Version | Compliance |
|---|---:|---|
| ATC-STD-000 | 1.3.0 | ✅ |
| ATC-STD-201 | 1.0.1 | ✅ |
| ATC-STD-202 | 1.2.0 | ✅ |
| ATC-STD-203 | 1.0.1 | ✅ |
| ATC-STD-204 | 1.0.0 | ✅ |
| ATC-STD-README-001 | 1.0.0 | ✅ |
| ATC-STD-MD-001 | 1.0.0 | ✅ |

## Roadmap

Siehe kanonische Quellen:

- `ROADMAP.md` (Repository-Wurzel)
- A-TownChain Master Roadmap (`a-townchain-os-docs`)
- GitHub Issues & Projects

## Contributing

Beiträge sind willkommen. Bitte lesen Sie vorab `CONTRIBUTING.md` und beachten Sie den Verhaltenskodex in `CODE_OF_CONDUCT.md`.

## License

Apache-2.0 — Copyright Michael Wroblewski (Org-Einheitslizenz per AD-F-046)..

## Maintainers

**Organization:** A-TownChain-Okosystems  
**Owner:** Michael Wroblewski  
**Maintainer:** ATC-AI-ARCH-001 (Aurora #1)

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
