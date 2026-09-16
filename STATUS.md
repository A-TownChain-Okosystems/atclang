---
document_id: ATC-DOC-LANG-001
title: ATCLang Repository Status
version: 1.1.1
status: active
owner: A-TownChain-Okosystems
created: 2026-09-07
updated: 2026-09-16
standard: ATC-STD-MD-001
---

# Status — ATCLang

> Aktueller Projektstatus und Qualitätsmetriken des Repositories `atclang`.

## Property-Value Übersicht

| Property | Value |
|---|---|
| Repository | atclang |
| Version | 1.0.0 |
| Status | development |
| Build | not independently re-established in this audit |
| Tests | deterministic-boundary regression tests added; current GitHub Actions evidence pending |
| Security | S4 / release-blocked by open P1 findings |
| Documentation | governance metadata present; audit remediation in progress |
| Architecture | Rust-first production / Python reference boundary enforced by policy and CI checks |
| Last Audit | 2026-09-16 |
| Production Readiness | NOT ESTABLISHED |

## Current Audit State

The 2026-09-16 CI audit uses a fail-closed repository gate. It intentionally detects known insecure Python reference-VM primitives instead of allowing a false PASS.

Open release-blocking findings:

- F-20260916-ATCLANG-001 — ECDSA simulation / permissive verification
- F-20260916-ATCLANG-002 — non-validating JWT helper
- F-20260916-ATCLANG-003 — network false-success simulation
- F-20260916-ATCLANG-004 — RPC false-success simulation
- F-20260916-ATCLANG-005 — non-conformant wallet/address helpers
- F-20260916-ATCLANG-006 — nondeterministic host capabilities in reference VM
- F-20260916-ATCLANG-007 — Rust production boundary requires executable integration proof
- F-20260916-ATCLANG-008 — remaining wall-clock access in VM/runtime after deterministic context remediation

Implemented in the current audit branch but awaiting current CI evidence:

- `HostContext` no longer has a host wall-clock capability.
- `ATCChain` requires explicit block timestamp state.
- Transaction and block-header timestamps are explicit deterministic inputs.
- Regression tests prove deterministic timestamp/hash behavior and reject missing chain timestamp state.

F-008 remains open because the VM/runtime still contains a direct clock path and an executable VM stub. It is not acceptable to close this finding from documentation alone.

A finding can only be closed after implementation, source re-read, positive/negative tests, integration evidence where applicable, current CI evidence, and documentation synchronization.

## Assurance Statement

This status does not claim immunity from malware, supply-chain compromise, zero-days, or all possible attacks. Assurance is limited to the implemented and executed controls with evidence recorded by the repository audit system.
