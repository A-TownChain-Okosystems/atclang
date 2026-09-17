# ATCLang Repository Audit — CI Fixes — 2026-09-17

## Scope

This record documents corrective work applied to the existing `audit/2026-09-16-ci-enforcement` branch for PR #13. `main` was not modified.

## Finding F-006 — ECDSA negative test used malformed signature data

- Class: P1
- Category: Cryptography / regression test
- Family: ATCLang Rust canonical security boundary
- Root cause: the test passed `sig_simulated` as a negative signature and then unwrapped the verifier result. The value is not a valid fixed-width P-256 ECDSA signature encoding, so the correct API result is `CryptoError::InvalidSignature`, not `Ok(false)`.
- Correction: the test now explicitly verifies the malformed-input error and separately verifies a syntactically valid 64-byte signature with invalid cryptographic contents returns `Ok(false)`.
- Implementation: `crates/atc-core/src/crypto.rs`
- Commit: `fa4b04971d040186a4e3985ddb6089751e9a5eab`

## Finding F-007 — Ruff format gate failed on three Python files

- Class: P2
- Category: CI / code quality
- Family: ATCLang CI enforcement
- Evidence: previous quality job `105181893607` reported `ruff check .` PASS and `ruff format --check .` FAIL for exactly three files.
- Corrected files:
  - `tools/audit/atclang_ci_audit.py`
  - `tools/determinism_check.py`
  - `src/atclang/vm/atcvm.py`
- Formatting work remains subject to fresh CI verification.

## Finding F-008 — Dependency Review cannot establish dependency graph

- Class: P1
- Category: CI / supply-chain governance
- Family: GitHub dependency graph / dependency review
- Observed state: the dependency-review workflow previously failed because the repository dependency graph is not enabled.
- Status: OPEN / EXTERNAL CONFIGURATION REQUIRED
- Required action: enable GitHub Dependency Graph for `A-TownChain-Okosystems/atclang`, then rerun the dependency-review gate.
- No workflow weakening or fail-open bypass is introduced by this audit.

## Finding F-009 — Python security reference moved out of the canonical namespace

- Class: P1
- Category: Architecture / canonical implementation boundary
- Family: Rust-first production security boundary
- Trigger: canonical Rust cryptographic implementation exists in `crates/atc-core/src/crypto.rs`.
- Correction: the Python `reference_boundary.py` was moved from `src/atclang/security/` to `src/atclang/legacy/security/` and explicitly documented as a legacy fail-closed compatibility layer.
- Canonical implementation: `crates/atc-core/src/crypto.rs`.
- Reference-only implementation: `src/atclang/legacy/security/reference_boundary.py`.
- VM import updated to use the legacy namespace.
- The original `src/atclang/security/reference_boundary.py` path was removed.
- Implementation commit: `c2763724887696aebf70ba45c65d4687af3e4206`.
- Important: moving the reference does not by itself establish production readiness; Rust integration/conformance tests and current CI remain required.

## Verification state

The corrections above are **IMPLEMENTED**, not yet **VERIFIED**. Verification requires a fresh CI run on the updated branch and successful completion of the required quality, Rust, differential, audit, determinism, CodeQL, static-security and dependency-review gates.

## Governance rule

No merge or production-readiness claim is made from these edits alone. The repository remains bounded by the evidence lifecycle `SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> AUDITED -> RELEASED`.
