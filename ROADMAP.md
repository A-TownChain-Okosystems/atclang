---
document_id: ATC-DOC-LANG-003
title: ATCLang Roadmap
version: 1.2.0
status: active
owner: A-TownChain-Okosystems
updated: 2026-09-24
standard: ATC-STD-MD-001
---

# ATCLang Roadmap

> Kanonische Entwicklungs-Roadmap für Sprache, Compiler, Rust-Canonical-Core und Conformance.

## Phase 1 — Foundation
- [x] Baseline v1.0 architecture
- [x] G1 Language Specification
- [x] G2 Semantics gate
- [x] Former Python reference implementation documented and removed — Rust-only canonical implementation (2026-09-17)
- [x] Rust canonical core started in crates/atc-core/

## Phase 2 — Canonical Rust compiler/VM
- [ ] G3 complete Rust frontend and parser conformance
- [ ] G4 ATC-IR + independent IR verifier
- [ ] G5 bytecode format + independent bytecode verifier
- [ ] G6 artifact format + validator
- [ ] G7 ABI canonicalization
- [ ] G8 capability/security policy enforcement
- [ ] G9 deterministic compilation
- [ ] G10 ATVM/state-transition execution conformance

### Implemented subset
- [x] atc CLI binary and frontend build/check gate
- [x] AST → bytecode lowering for the implemented subset
- [x] Deterministic stack VM and atc run
- [x] Control-flow subset: comparisons, if/else/else-if, while
- [x] Structural bytecode verification, including control-flow/stack-height checks for the implemented subset

## Phase 3 — Ecosystem integration
- [ ] G11 contracts engine
- [ ] G12 host boundary
- [ ] G13 package/lockfile/registry
- [ ] G14 CLI and SDK integration
- [ ] G15 cross-implementation/conformance expansion
- [ ] G16 fuzzing and negative-test corpus

## Phase 4 — Security and release
- [ ] G17 independent security audit
- [ ] G18 reproducible-build and provenance gate
- [ ] G19 release/mainnet gate

## Current blockers

- Canonical Rust implementation is incomplete beyond the implemented language/VM subset.
- Canonical IR, artifact, ABI, capability, resource/gas, storage/state-transition, and host-boundary contracts still require normative specifications and independent validation.
- Current GitHub Actions runtime evidence is unavailable/incomplete for the current audit head.
- Cross-component conformance, negative/fuzz coverage, reproducible-build evidence, and independent security review remain open.
- File inventory must be regenerated and validated against the Git tree.

No milestone is considered complete from documentation alone; implementation, tests and current evidence must converge before a gate is closed.