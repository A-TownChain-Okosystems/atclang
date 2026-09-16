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

- [ ] ECDSA implementation / fail-closed boundary
- [ ] JWT validation / fail-closed boundary
- [ ] Network transport boundary
- [ ] RPC transport boundary
- [ ] Wallet/BIP39/address conformance
- [x] HostContext wall-clock capability removed
- [x] ATCChain explicit block timestamp requirement
- [x] Transaction/block-header timestamp fallback removed
- [x] Deterministic boundary regression tests added
- [ ] Remove remaining wall-clock access from VM/runtime
- [ ] Remove/fail-closed executable VM STUB
- [ ] Determinism capability profile
- [ ] Rust production-entrypoint integration proof
- [ ] Positive and negative tests
- [ ] Differential tests
- [ ] Security/static analysis
- [ ] Current GitHub Actions evidence
- [ ] FILE_REGISTER regeneration
- [ ] STATUS/ROADMAP/audit evidence synchronization

### Exit criteria

Sprint closes only when every P1 item is implemented, tested, re-read, statically audited, and backed by current CI/evidence. Documentation-only closure is insufficient.

Agent-ID: ATC-AI-AUDIT-001
Task-ID: ATC-TASK-20260916-SPRINT
AI-Role: software-development
Validation: PENDING
