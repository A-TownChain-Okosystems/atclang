---
document_id: ATC-DOC-LANG-003
title: ATCLang Roadmap
version: 1.1.0
status: active
owner: A-TownChain-Okosystems
created: 2026-09-07
updated: 2026-09-16
standard: ATC-STD-MD-001
---

# ATCLang Roadmap

> Kanonische Entwicklungs-Roadmap für die ATCLang-Sprache, den Compiler und die Produktionsgrenze.

## Phase 1 — Rebuild & Semantik (Abgeschlossen)
- [x] Baseline v1.0 Rebuild (AD-019 / AD-022)
- [x] Gate G1 Language Specification
- [x] Gate G2 Semantics / TypeChecker

## Phase 2 — Compiler Backend & Subsystems
- [ ] Gate G3 Bytecode Emission & Optimization
- [ ] Gate G4 ATVM Execution Engine Integration
- [ ] Gate G5 Stdlib & Host API Completion

## Phase 2.1 — Security Boundary Remediation (Release Blocker)
- [ ] F-001 real ECDSA or explicit fail-closed reference boundary + negative tests
- [ ] F-002 real JWT validation or explicit fail-closed reference boundary + negative tests
- [ ] F-003 real transport adapter or fail-closed network reference operation
- [ ] F-004 real RPC adapter or fail-closed RPC reference operation
- [ ] F-005 protocol-conformant wallet/BIP39/address implementation + vectors
- [ ] F-006 deterministic capability profile and verifier rejection of consensus-incompatible host operations
- [ ] F-007 production integration test proving Rust canonical execution boundary
- [ ] Differential tests for every shared semantic/bytecode primitive
- [ ] Security audit evidence regenerated after each P1 closure

## Phase 2.2 — Governance / Documentation Synchronization
- [ ] Regenerate FILE_REGISTER.md from Git tree
- [ ] Synchronize STATUS.md and audit evidence after verified CI runs
- [ ] Validate AGENT_MANIFEST against current standards registry
- [ ] Add/maintain machine-readable sprint records and closure evidence
- [ ] Keep wiki/knowledge-base content synchronized with normative specs

## Phase 3 — Verification & Release
- [ ] Gate G18 Security Audit
- [ ] Gate G19 Mainnet Release
- [ ] Production readiness evidence package
- [ ] Release gates GATE-001…GATE-010 satisfied

## Release rule

No Phase 3 release gate may be marked complete while any P1 security/correctness finding remains open or current CI/evidence is unavailable.
