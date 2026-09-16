# ATCLang Sprint Register

## Sprint 2.1 — Security Boundary Remediation

**Status:** ACTIVE / RELEASE-BLOCKING  
**Date:** 2026-09-16  
**Owner:** A-TownChain-Okosystems

### Objectives

- remove or fail-closed all security-sensitive Python VM simulations;
- prove Rust is the canonical production execution path;
- establish deterministic capability enforcement;
- close findings F-001..F-008 with reproducible evidence;
- synchronize documentation, file inventory and standards metadata.

### Work items

- [x] Python ECDSA simulation removed; reference boundary fails closed
- [x] Python JWT permissive validation removed; reference boundary fails closed
- [x] Python network false-success removed; reference VM fails closed
- [x] Python RPC false-success removed; reference VM fails closed
- [x] Python wallet/BIP39/address simulation removed; reference boundary fails closed
- [x] HostContext wall-clock capability removed
- [x] ATCChain explicit block timestamp requirement
- [x] Transaction/block-header timestamp fallback removed
- [x] Deterministic boundary regression tests added
- [ ] Remove remaining wall-clock access from runtime/kernel-runtime
- [x] Remove/fail-closed executable VM STUB and simulated security primitives
- [ ] Determinism capability profile
- [ ] Rust production-entrypoint integration proof
- [x] Positive and negative security-boundary tests
- [ ] Full differential tests with canonical Rust implementation
- [x] Security/static analysis gate updated and passing on the pre-latest remediation snapshot
- [ ] Current GitHub Actions evidence for the latest commit
- [ ] FILE_REGISTER regeneration
- [x] STATUS/TODO/audit evidence synchronization
- [ ] ROADMAP/Wiki final synchronization after CI closure

### Exit criteria

Sprint closes only when every P1 item is implemented, tested, re-read, statically audited, and backed by current CI/evidence. Documentation-only closure is insufficient.

Agent-ID: ATC-AI-AUDIT-001
Task-ID: ATC-TASK-20260916-SPRINT
AI-Role: software-development
Validation: PENDING CURRENT-CI
