# ATCLang TODO / Closure Register

This file contains only actionable work. Completed items belong in CHANGELOG/audit evidence rather than remaining here.

## P1 — Release blockers

- [ ] F-20260916-ATCLANG-001: replace ECDSA simulation with canonical implementation or fail closed.
- [ ] F-20260916-ATCLANG-002: replace permissive JWT check with real validation or fail closed.
- [ ] F-20260916-ATCLANG-003: remove network false-success behavior.
- [ ] F-20260916-ATCLANG-004: remove RPC false-success behavior.
- [ ] F-20260916-ATCLANG-005: implement protocol-conformant wallet/BIP39/address handling.
- [ ] F-20260916-ATCLANG-008: remove all remaining host-clock access from the reference VM/runtime or make it unreachable and fail-closed for consensus execution.

## P2 — Architecture / assurance

- [ ] F-20260916-ATCLANG-006: enforce deterministic capability profile for consensus execution.
- [ ] F-20260916-ATCLANG-007: prove Rust canonical production dispatch with an integration test.
- [ ] Remove executable `STUB` markers from consensus-reachable VM code; reference-only stubs must fail closed and be isolated.
- [ ] Regenerate file register from the Git tree.
- [ ] Verify current GitHub Actions runs and attach evidence.
- [ ] Synchronize knowledge-base/wiki content with normative specifications.

## Recently implemented — pending CI closure

- [x] Removed host wall-clock capability from `HostContext`.
- [x] Required explicit block timestamp in `ATCChain`.
- [x] Made transaction/block-header timestamps explicit deterministic inputs.
- [x] Added deterministic execution-boundary regression tests.
- [ ] Re-run GitHub Determinism Gate on the new commits and close F-008 only if the complete repository scan is clean.

## Rule

No TODO is considered complete from a comment, documentation statement or manual assertion alone. Closure requires implementation + tests + source re-read + audit evidence.
