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
  - `src/atclang/vm/atcvm.py` — remaining formatting work is still pending because the GitHub contents write interface requires complete file replacement and the current connector response is truncated for this large file.
- Implemented formatting commits:
  - `331251bea7282e834765b15615fc85503af13bbc`
  - `0b4727937fcf000da45d41f527c9fd4672a6147a`

## Finding F-008 — Dependency Review cannot establish dependency graph

- Class: P1
- Category: CI / supply-chain governance
- Family: GitHub dependency graph / dependency review
- Observed state: the dependency-review workflow previously failed because the repository dependency graph is not enabled.
- Status: OPEN / EXTERNAL CONFIGURATION REQUIRED
- Required action: enable GitHub Dependency Graph for `A-TownChain-Okosystems/atclang`, then rerun the dependency-review gate.
- No workflow weakening or fail-open bypass is introduced by this audit.

## Verification state

The corrections above are **IMPLEMENTED**, not yet **VERIFIED**. Verification requires a fresh CI run on the updated branch and successful completion of the required quality, Rust, differential, audit, determinism, CodeQL, static-security and dependency-review gates.

## Governance rule

No merge or production-readiness claim is made from these edits alone. The repository remains bounded by the evidence lifecycle `SPECIFIED -> IMPLEMENTED -> TESTED -> VERIFIED -> AUDITED -> RELEASED`.
