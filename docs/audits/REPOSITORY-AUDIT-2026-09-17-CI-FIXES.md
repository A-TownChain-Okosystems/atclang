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
- Observed state: the dependency-review workflow failed because the repository dependency graph is not enabled.
- Status: OPEN / EXTERNAL CONFIGURATION REQUIRED
- Required action: enable GitHub Dependency Graph for `A-TownChain-Okosystems/atclang`, then rerun the dependency-review gate.
- No workflow weakening or fail-open bypass is introduced by this audit.

## Finding F-009 — Python security reference separated into Legacy namespace

- Class: P1
- Category: Architecture / canonical implementation boundary
- Family: Rust-first production security boundary
- Trigger: canonical Rust cryptographic implementation exists in `crates/atc-core/src/crypto.rs`.
- Correction: the Python `reference_boundary.py` implementation lives under `src/atclang/legacy/security/` and is explicitly fail-closed.
- Canonical implementation: `crates/atc-core/src/crypto.rs`.
- Reference-only implementation: `src/atclang/legacy/security/reference_boundary.py`.
- `tests/test_reference_security_boundary.py` now imports the explicit legacy namespace.
- `src/atclang/security/reference_boundary.py` is now only a compatibility shim that re-exports the Legacy implementation; it contains no security implementation of its own.
- This shim exists temporarily so the deterministic reference VM can migrate without breaking imports atomically.
- The VM must continue to migrate from the compatibility namespace to `atclang.legacy.security` once the large VM file can be safely edited as a complete blob.
- Implementation commits: `a51c22972e9a5b86cc3c107ccddbcfbaa5c01ace`, `331ccc669d06e2575ece23e239f60dff305d4da0`.
- Important: moving the reference does not by itself establish production readiness; Rust integration/conformance tests and current CI remain required.

## Current CI evidence

The first CI cycle for commit `a69674b0acab19b11a27be7d8c40782e3e9343b7` was started before the latest test/shim corrections. Its failures therefore remain historical evidence and must not be treated as evidence against the latest branch head.

Observed historical failures:

- Rust core: 16/17 tests; ECDSA negative test failed at the obsolete assertion.
- Differential: Rust canonical test failed at the same obsolete ECDSA assertion.
- Determinism: fail-closed because the test command returned non-zero.
- Quality: Ruff import ordering failed for `src/atclang/vm/atcvm.py` and `tests/test_reference_security_boundary.py` in that earlier merge snapshot.
- Dependency Review: GitHub reported Dependency Graph unavailable.

Successful historical gates included Repository Governance, ATCLang CI Audit, Python syntax, static security boundary, and CodeQL. These are historical observations only.

## Verification state

The corrections above are **IMPLEMENTED**, not yet **VERIFIED**. Verification requires a fresh CI run on the latest branch head and successful completion of the required quality, Rust, differential, audit, determinism, CodeQL, static-security and dependency-review gates.

## Governance rule

No merge or production-readiness claim is made from these edits alone. The repository remains bounded by the evidence lifecycle `SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> AUDITED -> RELEASED`.
