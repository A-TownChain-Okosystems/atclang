# ATCLang Knowledge Base

This repository-local knowledge base mirrors the normative architecture and current implementation state. Normative specifications remain authoritative over this page.

## Architecture

`ATCLang source → frontend → semantics → IR/compiler → bytecode → verifier → Rust canonical ATVM/runtime → A-TownChain`

Python is reference/test/fuzzing infrastructure and must not provide false-success security or transport semantics.

## Components

| Component | Location | Role |
|---|---|---|
| Frontend | `src/atclang/frontend/` | Lexer/parser/AST |
| Semantics | `src/atclang/semantics/` | Type/scope/semantic validation |
| Compiler | `src/atclang/compiler/` | IR/bytecode/ABI |
| VM/Runtime | `src/atclang/vm/`, `src/atclang/runtime/` | Reference/integration layer |
| Stdlib | `src/atclang/stdlib/` | Language primitives |
| Rust production | repository Rust components | Canonical production/security boundary |
| Audit | `tools/audit/` | Fail-closed governance/security checks |

## Current state

- Language and semantic baseline: implemented.
- Backend/ATVM integration: in progress.
- Security remediation: release-blocking.
- Production readiness: not established.

See `STATUS.md`, `ROADMAP.md`, `SPRINTS.md`, `TODO.md` and `docs/audits/` for current evidence.
