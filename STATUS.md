---
document_id: ATC-DOC-LANG-001
title: ATCLang Repository Status
version: 1.1.0
status: active
owner: A-TownChain-Okosystems
updated: 2026-09-16
standard: ATC-STD-MD-001
---

# Status — ATCLang

| Property | Value |
|---|---|
| Repository | atclang |
| Version | 1.0.0 development |
| Production implementation | Rust canonical core — incomplete |
| Reference implementation | Python — substantial |
| Tests | Defined; current GitHub Actions runtime evidence unavailable |
| Security | S4 / audit in progress |
| Conformance | Not verified for production |
| Release | development / NOT PRODUCTION_READY |
| Last audit | 2026-09-16 |

## Current verified facts

- The ATC standards profile is bound to the canonical atc-standards profile.
- The repository has a Rust canonical-core track and Python reference track.
- Consensus-sensitive Chain stdlib no longer uses a local wall-clock fallback on the hardening branch.
- Independent static governance/security audit tooling is present.
- Evidence claims are not treated as PASS without current commit-bound CI evidence.

## Open blockers

1. Fail-closed reference cryptography/auth/network/RPC boundaries.
2. Production Rust compiler/IR/bytecode verifier/VM completion.
3. Full differential and negative conformance suite.
4. Complete workflow pinning and restored CI runtime evidence.
5. Regenerated and validated FILE_REGISTER.
