<!--
HISTORISCH — nachgeholt am 2026-09-24 (war nie auf main gelandet, Quelle: Branch audit/2026-09-16-ci-enforcement).
Die Python-bezogenen P1-Findings (F-001..F-005) sind mit der Python-Loeschung (Welle 2, 17.09.) gegenstandslos geworden;
der Rust-Kern (crates/atc-core) hat diese Grenzen nicht. Determinismus-Findings laufen unter SCR-0128-Roadmap.
-->

# ATCLang TODO / Closure Register

This file contains only actionable work. Completed items belong in CHANGELOG/audit evidence rather than remaining here.

## P1 — Release blockers

- [ ] F-20260916-ATCLANG-001: canonical ECDSA backend at the Rust production boundary. Python VM/stdlib now fails closed.
- [ ] F-20260916-ATCLANG-002: canonical JWT validation at the Rust production boundary. Python VM/stdlib now fails closed.
- [ ] F-20260916-ATCLANG-003: real network transport adapter outside consensus execution. Python VM now fails closed.
- [ ] F-20260916-ATCLANG-004: real authenticated RPC adapter outside consensus execution. Python VM now fails closed.
- [ ] F-20260916-ATCLANG-005: protocol-conformant wallet/BIP39/address implementation with vectors. Python VM/stdlib now fails closed for wallet operations.
- [ ] F-20260916-ATCLANG-008: remove all remaining host-clock access from deterministic execution paths and obtain green Determinism Gate evidence.
- [x] F-20260916-ATCLANG-011: enforce `LoadLocal` local-index bounds in the Rust bytecode verifier; closure still requires current CI evidence.
- [x] F-20260916-ATCLANG-014: remove executable simulated security primitives from the Python VM. The VM has been replaced with a deterministic reference implementation whose security/network/wallet/host boundaries fail closed.
- [ ] F-20260916-ATCLANG-015: enable GitHub Dependency Graph and obtain a successful Dependency Review run.

## P2 — Architecture / assurance

- [ ] F-20260916-ATCLANG-006: enforce deterministic capability profile for consensus execution and prove all host operations are unreachable.
- [ ] F-20260916-ATCLANG-007: prove Rust canonical production dispatch with an integration test.
- [ ] F-20260916-ATCLANG-012: keep Ruff format check green for all audited Python tooling.
- [x] F-20260916-ATCLANG-013: prevent the determinism scanner from scanning its own pattern table; closure still requires current CI evidence.
- [ ] Regenerate `FILE_REGISTER.md` from the Git tree and make the generation check executable.
- [ ] Verify all current GitHub Actions runs and bind their evidence to the current commit.
- [ ] Synchronize knowledge-base/wiki content with normative specifications after the current remediation pass.

## Recently implemented — pending CI closure

- [x] Removed host wall-clock capability from `HostContext`.
- [x] Required explicit block timestamp in `ATCChain`.
- [x] Made transaction/block-header timestamps explicit deterministic inputs.
- [x] Added deterministic execution-boundary regression tests.
- [x] Enforced `LoadLocal` bounds in the Rust verifier.
- [x] Removed host-OS randomness from `ATCCrypto`; deterministic random APIs require an explicit VM seed.
- [x] Added a dedicated fail-closed reference security boundary.
- [x] Bound Python stdlib crypto/signature/wallet operations to the fail-closed boundary.
- [x] Replaced the old Python VM simulation implementation with a deterministic reference VM; security, network, RPC, filesystem and host-sensitive operations fail closed.
- [x] Added VM dispatch negative tests for ECDSA, JWT and network operations.
- [x] Formatted the previously failing Ruff files.

## Closure rule

No TODO is complete from documentation alone. Closure requires implementation + source re-read + positive/negative tests + integration evidence where applicable + static analysis + current GitHub Actions evidence + synchronized status/audit documentation.
