# ATCLang TODO / Closure Register

This file contains only actionable work. Completed items belong in CHANGELOG/audit evidence rather than remaining here.

## P1 — Release blockers

- [ ] F-20260916-ATCLANG-001: replace ECDSA simulation with canonical implementation or fail closed.
- [ ] F-20260916-ATCLANG-002: replace permissive JWT check with real validation or fail closed.
- [ ] F-20260916-ATCLANG-003: remove network false-success behavior.
- [ ] F-20260916-ATCLANG-004: remove RPC false-success behavior.
- [ ] F-20260916-ATCLANG-005: implement protocol-conformant wallet/BIP39/address handling.
- [ ] F-20260916-ATCLANG-008: remove all remaining host-clock access from the reference VM/runtime or make it unreachable and fail-closed for consensus execution.
- [x] F-20260916-ATCLANG-011: enforce `LoadLocal` local-index bounds in the Rust bytecode verifier; closure still requires current CI evidence.
- [ ] F-20260916-ATCLANG-014: eliminate all executable Python VM security simulations/stubs or make every reference-only primitive explicitly fail closed.
- [ ] F-20260916-ATCLANG-015: enable GitHub Dependency Graph and obtain a successful Dependency Review run.

## P2 — Architecture / assurance

- [ ] F-20260916-ATCLANG-006: enforce deterministic capability profile for consensus execution.
- [ ] F-20260916-ATCLANG-007: prove Rust canonical production dispatch with an integration test.
- [ ] F-20260916-ATCLANG-012: make Ruff format check green for all audited Python tooling.
- [x] F-20260916-ATCLANG-013: prevent the determinism scanner from scanning its own pattern table; closure still requires current CI evidence.
- [ ] Remove executable `STUB` markers from consensus-reachable VM code; reference-only stubs must fail closed and be isolated.
- [ ] Regenerate file register from the Git tree.
- [ ] Verify current GitHub Actions runs and attach evidence.
- [ ] Synchronize knowledge-base/wiki content with normative specifications.

## Recently implemented — pending CI closure

- [x] Removed host wall-clock capability from `HostContext`.
- [x] Required explicit block timestamp in `ATCChain`.
- [x] Made transaction/block-header timestamps explicit deterministic inputs.
- [x] Added deterministic execution-boundary regression tests.
- [x] Enforced `LoadLocal` bounds in the Rust verifier.
- [x] Removed host-OS randomness from `ATC::Crypto`; seeded pseudo-random APIs now require an explicit deterministic seed, while reference signing/key generation fail closed.
- [x] Excluded the determinism scanner itself from product-code scanning.
- [ ] Re-run GitHub Determinism Gate on the latest commits and close findings only if the complete repository scan is clean.

## Rule

No TODO is considered complete from a comment, documentation statement or manual assertion alone. Closure requires implementation + tests + source re-read + audit evidence.
