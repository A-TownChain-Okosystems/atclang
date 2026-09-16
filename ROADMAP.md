---
document_id: ATC-DOC-LANG-003
title: ATCLang Roadmap
version: 1.1.0
status: active
owner: A-TownChain-Okosystems
updated: 2026-09-16
standard: ATC-STD-MD-001
---

# ATCLang Roadmap

> Kanonische Entwicklungs-Roadmap für Sprache, Compiler, Rust-Canonical-Core und Conformance.

## Phase 1 — Foundation
- [x] Baseline v1.0 architecture
- [x] G1 Language Specification
- [x] G2 Semantics gate
- [x] Python reference implementation consolidated under `src/atclang/`
- [x] Rust canonical core started in `crates/atc-core/`

## Phase 2 — Canonical Rust compiler/VM
- [ ] G3 complete Rust frontend and parser conformance
- [ ] G4 ATC-IR + independent IR verifier
- [ ] G5 bytecode format + independent bytecode verifier
- [ ] G6 artifact format + validator
- [ ] G7 ABI canonicalization
- [ ] G8 capability/security policy enforcement
- [ ] G9 deterministic ATC-VM
- [ ] G10 runtime/state-transition integration

## Phase 3 — Ecosystem integration
- [ ] G11 contracts engine
- [ ] G12 host boundary
- [ ] G13 package/lockfile/registry
- [ ] G14 CLI and SDK
- [ ] G15 Rust/Python differential conformance expansion
- [ ] G16 fuzzing and negative-test corpus

## Phase 4 — Security and release
- [ ] G17 independent security audit
- [ ] G18 reproducible-build and provenance gate
- [ ] G19 release/mainnet gate

## Current blockers

- Python reference VM contains deliberately non-production cryptographic/auth/network/RPC helpers; these must fail closed or remain inaccessible to production paths.
- Canonical Rust implementation is incomplete.
- Current GitHub Actions runtime evidence is unavailable/incomplete.
- File inventory must be regenerated and validated against the Git tree.

No milestone is considered complete from documentation alone; implementation, tests and evidence must converge before a gate is closed.
