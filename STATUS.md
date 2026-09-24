---
document_id: ATC-DOC-LANG-001
title: ATCLang Repository Status
version: 1.2.0
status: active
owner: A-TownChain-Okosystems
updated: 2026-09-24
standard: ATC-STD-MD-001
---

# Status — ATCLang

| Property | Value |
|---|---|
| Repository | atclang |
| Version | 1.0.0 development |
| Production implementation | Rust canonical core — incomplete |
| Reference implementation | None — Python reference implementation removed; Rust-only canonical implementation |
| Tests | Rust tests present; current GitHub Actions runtime evidence unavailable for the current audit head |
| Security | S4 / audit in progress |
| Conformance | Not verified for production |
| Release | development / NOT PRODUCTION_READY |
| Last audit | 2026-09-24 |

## Current verified facts

- The ATC standards profile is bound to the canonical atc-standards profile.
- The repository is Rust-only for the canonical compiler/VM implementation; the former Python reference implementation and its runtime path were removed.
- The Rust core contains the canonical lexer, parser, AST, lowering path, deterministic bytecode/VM path, and structural bytecode verification for the implemented subset.
- Control-flow support and the corresponding verifier checks are implemented for the current subset.
- Consensus-sensitive deterministic execution must not depend on wall-clock time, ambient randomness, network access, or other implicit host state.
- Evidence claims are not treated as PASS without current commit-bound CI evidence.


## Open blockers

1. Complete the canonical Rust frontend/parser and language conformance surface.
2. Define and independently verify canonical ATC-IR, bytecode, artifact, ABI, capability, resource/gas, and state-transition boundaries.
3. Complete ATVM integration and ecosystem/state-transition conformance.
4. Complete negative, malformed-input, fuzzing, and cross-component conformance coverage.
5. Restore current GitHub Actions runtime evidence and complete reproducible-build/provenance and independent security gates.
6. Regenerate and validate FILE_REGISTER against the Git tree.

No production gate is considered complete from documentation alone; implementation, tests and current evidence must converge before closure.