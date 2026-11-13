# Engineering Audit

Repository: `atclang`
Status: BASELINE
Last verified: 2026-09-15

## Required audit loop

1. Implement code changes from authoritative requirements.
2. Run repository-native formatting, build and test checks.
3. Record functional errors and their evidence.
4. Record security findings and their evidence.
5. Record consistency findings across code, manifests and documentation.
6. Fix findings, then rerun the affected checks.
7. Verify module/function connectivity and fail closed on missing evidence.

## Current evidence boundary

This file establishes the organization-wide audit contract. It does **not** claim that the repository is production-ready. CI is the authoritative execution evidence.

## Security baseline

High-confidence credential patterns are rejected by `.github/workflows/repository-health.yml`. Cryptographic, parser, dependency and runtime security require repository-specific review.

## Consistency baseline

The repository name, documentation, manifests, public APIs and CI configuration must describe the same current implementation state. Target architecture must not be documented as implemented software.

## Evidence

- Automated repository-health workflow: `.github/workflows/repository-health.yml`
- Deep findings must be added here with reproducible evidence and a verification result.

## Findings — Audit 2026-11-12 (ATCLang Executability)

Source: Owner audit of 2026-11-12, priorities set by the Owner decision in the
same session. Each finding names its evidence and its verification state.

| ID | Priority | Finding | Evidence | State 2026-11-12 |
|---|---|---|---|---|
| F1 | P0 | Contract bodies are discarded while the compiler reports success | `atc run` on `examples/main.atc` printed `0` and exited 0; the Gateway contract with 10 functions, 8 state fields and 4 events had no bytecode | FIXED in E1 (see below), reproducible via `cargo test --locked` |
| F2 | P0 | Compiler and VM disagree on opcode values | separate component review (`a-townchain` `components/vm`, vendored `atc-core`) | OPEN, addressed by E2/E3 |
| F3 | P1/P2 | Weak `atc check` and no canonical IR for contracts | `check` returned 0 for a contract source without inspecting the body | PARTIAL: `check` now applies the E1 gate; full lowering parity and contract IR remain OPEN |
| F4 | P1 | i64 / u128 inconsistency between bytecode and ABI types | type surface of `atc-core` vs. economic/ABI types | OPEN, addressed by E5 |
| F5 | P1 | No CI build evidence for `atc-core` at the audited head | 197 local tests are not CI verification | OPEN, addressed by E5 |

## E1 — Contract lowering, fail-closed

Scope, as decided by the Owner on 2026-11-12: remove the dangerous simulation of
success only. No new language features, no compiler expansion, no new IR before
the existing architecture is established.

Implementation:

- `lower::executable_subset_gate` rejects every source that declares a contract
  before anything is built. The error names the contract, its bases and the
  visible surface (functions, state fields, events, `require` guards, body
  tokens).
- `lower_program` calls the gate first, so no `CompiledProgram` and no artifact
  can exist for a contract source.
- `atc check` applies the same gate, so validation cannot succeed where
  execution refuses.
- `atc run` additionally requires an entry point (`lower::require_entry_point`),
  so a declaration-only or empty source can no longer print `0` and exit `0`.
- The contrived replacement program (`ConstI64(0); Return`) is no longer
  reachable as a success path for either case.

Verification (reproducible):

- `cargo test --locked` in `crates/atc-core`: 105 tests, 0 failed, including
  `tests/contract_e1_failclosed.rs` (10 tests).
- `atc run examples/main.atc`: exit 1, stderr names `Vertrag 'Gateway'`, no
  stdout.
- `atc run` on `contract Vault { fn main() -> i64 { return 42 } }`: exit 1, no
  `0` output.
- `cargo clippy --all-targets -- -D warnings` and `cargo fmt --check`: clean.
- `python3 tools/determinism_check.py --lang rust`: PASS.

Known limits, stated rather than claimed away:

- `atc check` validates the E1 gate and the parse, not the full lowering
  pipeline. Finding F3 stays open for the full parity.
- A program containing a contract is rejected as a whole. There is no partial
  compilation of its non-contract parts, by design.
- `examples/kernel.atc` fails at the parser (import path with a brace), which is
  a separate parser finding and not part of E1.
- Contract support remains zero until E2/E3 establish the opcode source of
  truth and the VM decoder, and until contract bodies are lowered on purpose.
