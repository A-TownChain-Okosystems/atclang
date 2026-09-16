# ATCLang Knowledge Base

This repository-local knowledge base mirrors the normative architecture and current implementation state. Normative specifications remain authoritative over this page.

## Architecture

`ATCLang source → frontend → semantics → IR/compiler → bytecode → verifier → Rust canonical ATVM/runtime → A-TownChain`

Python is reference/test/fuzzing infrastructure. Security, wallet, network, RPC, filesystem and host-sensitive reference operations fail closed unless a verified backend is explicitly bound.

## Components

| Component | Location | Role |
|---|---|---|
| Frontend | `src/atclang/frontend/` | Lexer/parser/AST |
| Semantics | `src/atclang/semantics/` | Type/scope/semantic validation |
| Compiler | `src/atclang/compiler/` | IR/bytecode/ABI |
| VM/Runtime | `src/atclang/vm/`, `src/atclang/runtime/` | Deterministic reference/integration layer |
| Stdlib | `src/atclang/stdlib/` | Pure deterministic primitives and explicit trust boundaries |
| Security boundary | `src/atclang/security/reference_boundary.py` | Fail-closed reference security/transport/wallet boundary |
| Rust production | repository Rust components | Canonical production/security boundary |
| Audit | `tools/audit/` | Fail-closed governance/security checks |
| Determinism gate | `tools/determinism_check.py` | Host clock/entropy scan + reproducibility evidence |

## Current state

- Language and semantic baseline: implemented.
- Python VM security simulations/stub: removed; reference security operations fail closed.
- Deterministic VM boundary: implemented; current repository-wide CI evidence still required.
- Backend/Rust ATVM integration: in progress.
- Security remediation: still release-blocking until canonical Rust implementations/integration proofs are complete.
- Production readiness: **NOT ESTABLISHED**.

## Evidence model

A component is considered actually present only when the chain is demonstrated:

`Vision → Concept → Component → Code → Test → CI Evidence → Finding/Fix → Re-test → Actual software state`

Documentation alone cannot close a release blocker.

See `STATUS.md`, `ROADMAP.md`, `SPRINTS.md`, `TODO.md` and `docs/audits/` for the current evidence state.
