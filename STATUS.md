---
document_id: ATC-DOC-LANG-001
title: ATCLang Repository Status
version: 1.3.0
status: active
owner: A-TownChain-Okosystems
updated: 2026-11-12
standard: ATC-STD-MD-001
---

## Status — ATCLang

| Property | Value |
|---|---|
| Repository | atclang |
| Version | 1.0.0 development |
| Production implementation | Rust canonical core — incomplete |
| Reference implementation | None — Python reference implementation removed; Rust-only canonical implementation |
| Tests | 105 Rust tests green locally (`cargo test --locked`, 2026-11-12); GitHub Actions runtime evidence for the audit head still pending |
| Security | S4 / audit in progress |
| Conformance | Not verified for production |
| Release | development / NOT PRODUCTION_READY |
| Last audit | 2026-11-12 (Owner audit, findings F1 to F5) |

## Current verified facts

- The ATC standards profile is bound to the canonical atc-standards profile.
- The repository is Rust-only for the canonical compiler/VM implementation; the former Python reference implementation and its runtime path were removed.
- The Rust core contains the canonical lexer, parser, AST, lowering path, deterministic bytecode/VM path, and structural bytecode verification for the implemented subset.
- Control-flow support and the corresponding verifier checks are implemented for the current subset.
- Consensus-sensitive deterministic execution must not depend on wall-clock time, ambient randomness, network access, or other implicit host state.
- Evidence claims are not treated as PASS without current commit-bound CI evidence.

## E1 — Contract executability (2026-11-12)

- `Stmt::Contract` is no longer skipped. `lower::executable_subset_gate` rejects any source that declares a contract before a compile is built, and names what would have been lost (functions, state fields, events, `require` guards).
- `atc run` exits 1 for a contract instead of printing `0` with exit 0. `atc check` refuses the same source. No replacement program (`ConstI64(0); Return`) is generated.
- The rule "Compiler Success is not an Executable Contract" and the states `PARSED`, `TYPE_CHECKED`, `SEMANTICALLY_VALIDATED`, `BYTECODE_GENERATED`, `BYTECODE_VERIFIED`, `DEPLOYABLE`, `EXECUTABLE` are documented in `docs/EXECUTION_STATE_MODEL.md`.
- Honest limit: contract support is still zero. Rejection is a safety measure, not a fix. Contracts stay unusable until the opcode source of truth (E2), the VM decoder (E3) and end-to-end coverage (E4) exist.

## Open blockers

1. Complete the canonical Rust frontend/parser and language conformance surface. Contract bodies are held as a token stream only; contract lowering does not exist, and E1 rejects them fail-closed.
2. Establish one normative opcode table (ATC-BC-001) and align the VM decoder with it; compiler and VM must not interpret opcode values differently (F2).
3. Strengthen `atc check` to the full lowering pipeline instead of the current E1 gate plus parse (F3). Decide on a canonical contract IR only after the existing compiler architecture is established.
4. Define and independently verify canonical ATC-IR, bytecode, artifact, ABI, capability, resource/gas, and state-transition boundaries.
5. Complete ATVM integration and ecosystem/state-transition conformance.
6. Complete negative, malformed-input, fuzzing, and cross-component conformance coverage.
7. Restore current GitHub Actions runtime evidence and complete reproducible-build/provenance and independent security gates.
8. Regenerate and validate FILE_REGISTER against the Git tree.

No production gate is considered complete from documentation alone; implementation, tests and current evidence must converge before closure.
