# ATCLang CI / Standards Enforcement Audit — 2026-09-16

**Status:** `IN PROGRESS` / production release remains blocked by P1 security findings and incomplete current GitHub evidence.

**Audit mode:** repository source/static audit plus implementation of a fail-closed CI audit gate. GitHub Actions evidence is reported only when a current run proves it.

## 1. Scope

The audit covers:

- standards enforcement and repository governance;
- architecture and language boundary;
- syntax/lint/test/differential gates;
- security and deterministic execution boundaries;
- stubs, placeholders and false-success implementations;
- documentation, roadmap and file-register consistency;
- file format and implementation-language suitability;
- traceability from Vision → Concept → Components → Code → Tests → Evidence.

## 2. Normative architecture

The repository declares Rust as the production/canonical language in `.atc/repository.yaml`. The architecture baseline defines Rust as canonical for compiler, verifier, ATVM, runtime, ABI/artifact validation, security/sandbox and CLI, while Python is the reference implementation, SDK and test/fuzzing layer. The bytecode verifier is a hard trust boundary and differential agreement between Rust and Python stacks is required.

This architecture is retained. It is the lowest-risk boundary for consensus-critical software because production execution does not depend on a dynamically typed reference implementation.

## 3. CI enforcement implemented by this change

Added `tools/audit/atclang_ci_audit.py` and `.github/workflows/atclang-ci-audit.yml`.

The gate is fail-closed and checks:

1. mandatory governance/specification files;
2. required workflow set;
3. Rust-primary repository metadata;
4. normative agent-standard references;
5. repository audit, lint/format, tests, differential and evidence workflow presence;
6. targeted insecure reference-VM primitives;
7. executable `STUB` markers in the VM;
8. architecture enforcement statements;
9. stale file-register entries;
10. TODO/FIXME/XXX markers in executable source;
11. suspicious executable supply-chain/runtime primitives;
12. immutable SHA pinning of GitHub Actions.

The gate is intentionally not an immunity claim. It proves only the controls encoded in CI and fails when known unsafe implementation patterns remain.

## 4. Findings

### F-20260916-ATCLANG-001
- **Class:** P1
- **Category:** Security / cryptographic correctness
- **Family:** Python reference VM / ECDSA
- **Tags:** `P1 security crypto ecdsa reference-vm fail-closed`
- **Finding:** reference ECDSA functions are simulation logic rather than ECDSA.
- **Impact:** forged signatures can be accepted if the reference primitive is reached.
- **Closure:** replace with a real, explicitly tested implementation or fail closed; prove production dispatch cannot select the reference primitive.

### F-20260916-ATCLANG-002
- **Class:** P1
- **Category:** Security / authentication correctness
- **Family:** Python reference VM / JWT
- **Tags:** `P1 security jwt authentication validation`
- **Finding:** JWT helper accepts arbitrary sufficiently long strings.
- **Impact:** authentication bypass if exposed outside reference-only tests.
- **Closure:** real signature/claims validation or fail closed, with negative tests.

### F-20260916-ATCLANG-003
- **Class:** P1
- **Category:** Security / network correctness
- **Family:** Python reference VM / network
- **Tags:** `P1 security network false-success`
- **Finding:** network send reports success without transport.
- **Impact:** callers can make incorrect security/reliability decisions.
- **Closure:** explicit transport injection for tests or fail closed.

### F-20260916-ATCLANG-004
- **Class:** P1
- **Category:** Security / RPC correctness
- **Family:** Python reference VM / RPC
- **Tags:** `P1 security rpc false-success`
- **Finding:** RPC helper fabricates a successful response.
- **Impact:** authorization/transport/response-validation paths can be bypassed semantically.
- **Closure:** real transport or fail closed.

### F-20260916-ATCLANG-005
- **Class:** P1
- **Category:** Cryptographic / wallet correctness
- **Family:** Python reference VM / BIP39 / address derivation
- **Tags:** `P1 crypto wallet bip39 address`
- **Finding:** embedded mnemonic/address helpers are not protocol-conformant and address generation is not key-bound.
- **Impact:** incompatible or insecure wallet material.
- **Closure:** canonical wallet implementation plus conformance vectors, or explicit reference-only failure.

### F-20260916-ATCLANG-006
- **Class:** P2
- **Category:** Determinism / consensus boundary
- **Family:** Python reference VM / host capabilities
- **Tags:** `P2 determinism consensus random time`
- **Finding:** nondeterministic operations are exposed in the reference VM.
- **Impact:** accidental consensus use could produce divergent state.
- **Closure:** capability/profile enforcement and verifier rejection for consensus-incompatible operations.

### F-20260916-ATCLANG-007
- **Class:** P2
- **Category:** Architecture / language policy enforcement
- **Family:** Rust canonical / Python reference boundary
- **Tags:** `P2 architecture rust-canonical python-reference enforcement`
- **Finding:** the Rust-first boundary is documented but must be demonstrated by executable production-entrypoint enforcement.
- **Closure:** integration test proving production artifacts/execution resolve to Rust and cannot silently dispatch to the Python VM.

### F-20260916-ATCLANG-008
- **Class:** P1
- **Category:** Determinism / consensus safety
- **Family:** Execution context / host capability boundary
- **Tags:** `P1 determinism consensus wall-clock execution-context fail-closed`
- **Finding:** the repository contained host-clock fallbacks in `HostContext`, `ATCChain` and blockchain primitives, while the determinism gate also detected clock access in the reference VM/runtime.
- **Remediation implemented:** `HostContext` no longer imports or reads the host clock; `ATCChain.block_timestamp` now requires explicit block state; transaction and block-header timestamps are explicit inputs with deterministic defaults. Regression tests were added for reproducibility and missing authenticated block timestamps.
- **Residual blocker:** the Python VM still contains direct wall-clock usage and an executable `STUB` marker. Therefore F-008 is **not closed**; the remaining VM/runtime boundary must be removed or made explicitly fail-closed before release.
- **Impact:** accidental consensus execution through the reference VM could diverge between nodes.
- **Closure:** remove/fail-closed all remaining consensus-reachable wall-clock sources, prove the production entrypoint cannot reach them, and obtain a current green determinism workflow run.

## 5. Consistency findings

`FILE_REGISTER.md` is generated metadata and currently omits newer CI/audit files visible in the Git tree. This is documentation/registry drift rather than a runtime security defect. The audit reports it as a warning so the register can be regenerated from the authoritative Git tree.

The repository status says language/semantics work is complete while the roadmap still lists backend, VM integration, security audit and production gates as incomplete. This is internally coherent: language/semantics completion does not imply compiler-backend, VM integration, security audit or production readiness.

## 6. File format / language assessment

- Markdown: correct for normative/explanatory documentation.
- YAML: correct for repository/governance machine metadata.
- TOML: appropriate for package/build/version configuration.
- JSON: appropriate for generated registries and fixtures where schema-stable machine consumption is required.
- Python: correct for reference implementation, SDK, tests and fuzzing.
- Rust: required as the canonical production implementation for consensus-critical execution and security boundaries.

No broad file-format migration is justified; unnecessary migration would increase change surface without increasing assurance.

## 7. Security assurance boundary

The audit does **not** claim immunity from malware, supply-chain compromise, memory corruption, zero-days, or all possible runtime attacks. Protection is established only for a defined threat class when the relevant control, negative test and current CI evidence all exist.

Current controls provide concrete resistance against several defined classes: immutable GitHub Action references reduce tag/ref substitution risk; CodeQL and dependency review provide static/dependency analysis; fail-closed governance blocks known unsafe reference primitives; deterministic gates block detected wall-clock/RNG sources; and the architecture keeps Python outside the canonical production trust boundary. None of these proves immunity to arbitrary future malware or unknown vulnerabilities.

For F-001 through F-008, complete protection is **not established** until implementation changes and current evidence close the findings.

## 8. Closure evidence required

A finding may only be marked closed after:

1. implementation change;
2. source re-read;
3. positive and negative tests;
4. integration test for the Rust production boundary where applicable;
5. static security scan;
6. current GitHub Actions evidence;
7. documentation/status/roadmap update;
8. no contradictory remaining implementation or duplicate primitive.

## 9. Vision → implementation traceability

`Vision → Concept → Components → Code → Test → Evidence` is represented by the repository architecture/specification hierarchy, source tree, test suite, differential gate, governance audit and evidence artifacts. The remaining assurance gap is closure of the known P1 implementation findings and current runtime evidence, not documentation of intent alone.

**Production readiness:** `NOT ESTABLISHED`.
