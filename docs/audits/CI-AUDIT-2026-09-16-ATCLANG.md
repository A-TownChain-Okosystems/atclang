# ATCLang CI Audit — 2026-09-16

Status: **FAIL-CLOSED / NOT PRODUCTION READY**

This audit records the executable evidence available from GitHub Actions and the repository's own compliance gate. A passing individual gate is evidence only for the control it executes; it is not evidence that unrelated requirements are satisfied.

## Evidence snapshot

Audited branch: `audit/2026-09-16-ci-enforcement`

Latest verified commit: `039ba93f68120a2d77d15d5adf5f64f7a568c65a`

The PR merge ref was `f649fcb070fa4d9cca3ac344d92a1edadc0e7682` and executed the same audit branch changes.

| Gate | Result | Meaning |
|---|---|---|
| Repository Governance (ATC-STD-201/202/203) | PASS | Governance controls currently execute successfully. |
| ATC Test Suite | PASS | Existing test suite completed successfully. |
| CodeQL | PASS | CodeQL completed successfully for this revision. |
| ATCLang CI Audit / repository audit | FAIL | Known unsafe reference primitives remain. |
| ATCLang CI Audit / static security boundary | FAIL | Executable security stubs remain. |
| Determinism Gate | FAIL | Determinism violations remain outside the already-fixed scanner self-match. |
| ATC Code Quality (STD-081/082) | FAIL | Formatting/quality closure is not established. |
| Dependency Review | FAIL | GitHub Dependency Graph is not available to the workflow. |

## Release-blocking findings

### F-001 — Reference ECDSA primitive
- Class: P1
- Category: Security / cryptographic correctness
- Family: Crypto / Signature
- Tags: `ecdsa`, `signature`, `authentication`, `fail-closed`
- Evidence: `src/atclang/vm/atcvm.py` contains a simulated signing path and permissive signature verification.
- Risk: a production path reaching this implementation could accept forged authentication material.
- Required state: the Python reference path must either delegate to a canonical, policy-constrained implementation or fail closed. Production/consensus execution must be proven unable to reach it.
- Verification: CI currently fails on this exact primitive, so the finding remains open.

### F-002 — JWT validation is not cryptographic validation
- Class: P1
- Category: Security / authentication
- Family: Token / Identity
- Tags: `jwt`, `authentication`, `token-validation`
- Evidence: the reference VM currently uses a permissive token-length predicate.
- Risk: authentication bypass if exposed as an authority-bearing verifier.
- Required state: algorithm allow-list, signature verification, key handling, issuer/audience policy and temporal claims must be enforced, or the reference path must fail closed.
- Verification: CI currently fails on this primitive.

### F-003 — Network send reports simulated success
- Class: P1
- Category: Security / network correctness
- Family: P2P / Transport
- Tags: `network`, `false-success`, `p2p`
- Evidence: the reference VM contains a simulated-success network send.
- Risk: consensus or orchestration code could treat an operation as delivered when no transport occurred.
- Required state: injected real transport or explicit fail-closed reference behavior.
- Verification: CI currently fails on this primitive.

### F-004 — RPC call fabricates HTTP success
- Class: P1
- Category: Security / external interface correctness
- Family: RPC / Transport
- Tags: `rpc`, `false-success`, `transport`
- Evidence: the reference VM fabricates a successful response.
- Risk: false state transitions and authentication/authorization confusion.
- Required state: injected transport with authenticated response handling, or explicit failure in reference-only mode.
- Verification: CI currently fails on this primitive.

### F-005 — Wallet/BIP39/address implementation is non-conformant
- Class: P1
- Category: Security / key and address correctness
- Family: Wallet / Key Derivation
- Tags: `bip39`, `wallet`, `address`, `key-derivation`
- Evidence: the reference VM uses a truncated embedded word set and derives addresses independently of the supplied public key.
- Risk: incompatible wallets and key/address mismatches.
- Required state: canonical BIP39/conformance vectors and key-bound address derivation, or fail-closed reference behavior.
- Verification: CI audit remains red.

### F-006 — Host capabilities remain reachable from deterministic execution
- Class: P2
- Category: Determinism / consensus safety
- Family: Execution Context / Host Capability
- Tags: `determinism`, `consensus`, `host-capability`
- Evidence: current repository search still finds host-clock access in runtime/stdlib surfaces. The VM also contains host-clock access.
- Required state: deterministic execution context supplies block time; consensus code has no host-clock fallback.
- Verification: Determinism Gate remains red.

### F-007 — Rust production-boundary proof is incomplete
- Class: P2
- Category: Architecture / language policy
- Family: Runtime / Production Boundary
- Tags: `rust-first`, `production-boundary`, `python-reference`, `traceability`
- Required state: an executable test must prove the production entrypoint resolves to the Rust canonical implementation and cannot silently dispatch to Python reference primitives.
- Verification: no green executable proof has yet been recorded.

### F-008 — LoadLocal verifier bounds check
- Class: P1
- Category: Security / verifier correctness
- Family: Bytecode / Local Variables
- Tags: `verifier`, `bytecode`, `invalid-local`, `fail-closed`
- Status: **IMPLEMENTED; CI CLOSURE PENDING**.
- Evidence: Rust `Instruction::LoadLocal` now rejects indexes greater than or equal to the declared local count, with a regression test.
- Required verification: current PR CI must execute the regression test successfully.

### F-009 — Determinism scanner self-file false positive
- Class: P2
- Category: CI logic / scanner correctness
- Family: Determinism / Static Analysis
- Tags: `determinism`, `scanner`, `false-positive`, `ci`
- Status: **IMPLEMENTED; CI CLOSURE PENDING**.
- Evidence: the scanner now excludes its own normalized file path rather than comparing a directory basename with a file path.
- Required verification: a fresh Determinism Gate must pass the scanner stage while still finding genuine violations.

### F-010 — File Register drift
- Class: P2
- Category: Governance / repository inventory consistency
- Family: File Inventory
- Tags: `file-register`, `inventory`, `governance`, `consistency`
- Evidence: `FILE_REGISTER.md` was missing current workflow/audit paths.
- Required state: register generated from the actual Git tree, not manually curated.
- Status: documented; current register still needs full regeneration.

### F-011 — Dependency Review cannot execute its intended graph analysis
- Class: P1
- Category: Supply-chain security / CI infrastructure
- Family: Dependency Graph / Dependency Review
- Tags: `dependency-review`, `dependency-graph`, `supply-chain`
- Evidence: GitHub Dependency Review reports that the repository Dependency Graph is unavailable.
- Required state: enable Dependency Graph at repository level and rerun the workflow. The immutable-SHA gate must not be weakened to hide this failure.
- Status: external GitHub setting required.

## Standards enforcement assessment

The repository declares the following required standards in `.atc/standards.yaml`: ATC-STD-000, 003, 012, 016, 017, 018, 019, 201 and 202.

Current CI directly checks a subset of these controls. Therefore **presence of a standard in the registry is not treated as proof of complete enforcement**. The release gate remains fail-closed until each required standard has either an executable enforcement rule or an explicitly documented, reviewed human/governance control.

## Security assurance

The current controls provide evidence against defined classes of failure: immutable GitHub Action references, CodeQL, static security scanning, deterministic-execution scanning, verifier tests, governance checks and fail-closed release status.

They do **not** prove immunity against zero-days, compromised dependencies, malicious maintainers, arbitrary malware, hardware compromise, or future attack techniques. A claim of absolute "hack" or "virus" immunity would not be technically supportable.

For each threat class, acceptance requires the chain:

`threat -> control -> negative test -> positive test -> CI evidence -> documented residual risk`.

## Traceability model

```text
Vision
  -> Concept
  -> Components
  -> Code
  -> Tests
  -> Evidence
  -> Finding
  -> Fix
  -> Re-test
  -> Actual software state
```

A component is considered present only when its implementation and its executable evidence agree. Documentation alone cannot close a release-blocking finding.

## Next closure order

1. Remove/fail-close the unsafe Python VM security primitives.
2. Remove/fail-close remaining host-clock access from deterministic execution paths.
3. Add executable Rust production-boundary proof.
4. Regenerate the complete File Register from the Git tree.
5. Fix remaining formatting/quality failures.
6. Enable GitHub Dependency Graph and rerun Dependency Review.
7. Rerun all affected gates and close findings only after fresh evidence is green.
