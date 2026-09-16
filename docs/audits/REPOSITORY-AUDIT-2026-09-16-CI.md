# ATCLang CI / Standards Enforcement Audit — 2026-09-16

**Status:** `IN PROGRESS / FAIL-CLOSED` — production readiness remains `NOT ESTABLISHED`.

## Scope

This audit covers standards enforcement, architecture, syntax/lint/tests, deterministic execution, security boundaries, stubs/false-success behavior, documentation/roadmap/TODO/sprint/wiki consistency, file inventory, duplicate/contradictory primitives, language/file-format suitability, and traceability from Vision to actual software state.

## Normative architecture

- Rust is the canonical production implementation for compiler/verifier/ATVM/runtime/ABI/security-critical paths.
- Python is a reference, SDK, testing and fuzzing layer.
- The bytecode verifier is a hard trust boundary.
- Consensus execution must not depend on host wall-clock, host RNG, network, filesystem or other uncontrolled host capabilities.
- Python reference security/transport/wallet operations must fail closed unless a verified backend is explicitly bound.

This boundary is the lowest-risk architecture because a dynamic reference implementation cannot become an accidental consensus authority.

## Standards enforcement

`.atc/standards.yaml` currently binds:

`ATC-STD-000, 003, 012, 016, 017, 018, 019, 201, 202`.

The repository CI directly enforces only a subset. Therefore registration is not treated as enforcement. Each required standard must map to an executable gate, machine-readable validation, or explicitly reviewed governance control.

Current executable controls include repository governance, required repository metadata, Rust-primary policy, immutable action SHA checks, Ruff lint/format, Python syntax compilation, test suite, differential testing, CodeQL, dependency review, determinism scanning, static security-boundary scanning and this repository audit.

## Current findings

### F-001 — ECDSA reference primitive
- **Class:** P1
- **Category:** Security / cryptographic correctness
- **Family:** Crypto / Signature
- **Tags:** `ecdsa`, `signature`, `authentication`, `fail-closed`
- **Previous defect:** Python VM generated synthetic signatures and accepted a `sig_` prefix.
- **Remediation:** Python VM and stdlib now route through `reference_boundary.py` and fail closed.
- **Remaining closure:** canonical Rust implementation plus production-boundary integration proof and current green CI evidence.

### F-002 — JWT validation
- **Class:** P1
- **Category:** Security / authentication
- **Family:** Token / Identity
- **Tags:** `jwt`, `authentication`, `token-validation`
- **Previous defect:** token-length predicate instead of cryptographic JWT validation.
- **Remediation:** Python reference operation now fails closed.
- **Remaining closure:** canonical Rust validation and integration evidence.

### F-003 — Network false success
- **Class:** P1
- **Category:** Security / network correctness
- **Family:** P2P / Transport
- **Tags:** `network`, `false-success`, `p2p`
- **Remediation:** Python VM network send now fails closed; no synthetic success remains in the replacement VM.
- **Remaining closure:** real transport belongs outside consensus/reference execution and requires authenticated integration tests.

### F-004 — RPC false success
- **Class:** P1
- **Category:** Security / external interface correctness
- **Family:** RPC / Transport
- **Tags:** `rpc`, `false-success`, `transport`
- **Remediation:** Python RPC path now fails closed.
- **Remaining closure:** canonical authenticated RPC adapter and integration evidence.

### F-005 — Wallet/BIP39/address correctness
- **Class:** P1
- **Category:** Cryptographic / wallet correctness
- **Family:** Wallet / Key Derivation
- **Tags:** `bip39`, `wallet`, `address`, `key-derivation`
- **Remediation:** synthetic wallet/BIP39/address operations in the Python VM now fail closed.
- **Remaining closure:** protocol-conformant canonical implementation and conformance vectors.

### F-006/F-008 — Deterministic execution
- **Class:** P1/P2
- **Category:** Determinism / consensus safety
- **Family:** Execution Context / Host Capability
- **Tags:** `determinism`, `consensus`, `wall-clock`, `host-capability`
- **Remediation:** `HostContext`, `ATCChain`, transaction and block-header timestamp handling were made explicit/deterministic. The replacement VM no longer reads host time.
- **Remaining closure:** current repository-wide Determinism Gate must be green; runtime/kernel-runtime host-clock findings must be eliminated or proven unreachable from consensus execution.

### F-007 — Rust production-boundary proof
- **Class:** P2
- **Category:** Architecture / language policy
- **Family:** Runtime / Production Boundary
- **Tags:** `rust-first`, `python-reference`, `production-boundary`, `traceability`
- **Status:** open.
- **Closure:** executable integration test must prove production entry resolves to Rust and cannot silently dispatch to Python reference execution.

### F-011 — LoadLocal verifier bounds
- **Class:** P1
- **Category:** Security / verifier correctness
- **Family:** Bytecode / Local Variables
- **Tags:** `verifier`, `bytecode`, `invalid-local`, `fail-closed`
- **Status:** implementation present; current CI closure pending.

### F-012 — Ruff quality gate
- **Class:** P2
- **Category:** CI quality / lint and formatting
- **Family:** Python tooling / Ruff
- **Tags:** `ci`, `lint`, `formatting`, `ruff`
- **Detected defect:** current CI run 35114977328 reported 216 Ruff findings in the replacement VM plus one import-order finding in the security-boundary regression test.
- **Remediation:** `src/atclang/vm/atcvm.py` was rewritten in Ruff-compliant style and `tests/test_reference_security_boundary.py` import ordering was normalized.
- **Verification:** a new CI cycle is required; closure is not claimed until the latest branch commit is green.

### F-013 — Determinism scanner self-match
- **Class:** P2
- **Category:** CI correctness / static analysis
- **Family:** Determinism / Scanner
- **Tags:** `determinism`, `scanner`, `false-positive`, `ci`
- **Remediation:** scanner self-file exclusion is implemented. Genuine product findings remain fail-closed.

### F-014 — Executable Python security simulations/stub
- **Class:** P1
- **Category:** Security / reference implementation boundary
- **Family:** Python VM / simulated security and transport primitives
- **Tags:** `security`, `reference-vm`, `stub`, `false-success`
- **Remediation:** the previous simulation VM was replaced by a deterministic reference VM. It contains no executable `# STUB:` marker and explicitly fails closed for security, network, RPC, wallet, filesystem and host-sensitive operations.
- **Verification:** negative tests exercise VM dispatch for ECDSA, JWT and network boundaries.
- **Closure:** current CI/static scan must confirm the old patterns are absent.

### F-015 — Dependency Review
- **Class:** P1
- **Category:** Supply-chain security / dependency analysis
- **Family:** Dependency Graph / Dependency Review
- **Tags:** `dependency-review`, `dependency-graph`, `supply-chain`
- **Status:** externally blocked until GitHub Dependency Graph is enabled.
- **Evidence:** current GitHub run 35114977583 fails because Dependency Review reports that Dependency Graph is not enabled for the repository. The immutable action reference itself is intact.

## Consistency / contradiction resolution

The former duplicate crypto paths in the Python VM and `stdlib/crypto.py` could silently disagree. The new architecture makes the Python security-sensitive operations converge on one fail-closed boundary, while canonical production behavior remains Rust.

The former VM `STUB` claim also contradicted the stated Rust-first architecture. It has been removed from the executable VM source.

The repository status, roadmap, TODO and sprint register now consistently describe the security/production gates as incomplete until executable evidence closes them.

## File format / language decision

- Markdown: normative/explanatory documentation.
- YAML: CI/governance machine metadata.
- TOML: Rust/build/version configuration.
- JSON: schemas, fixtures and generated machine data.
- Python: reference/test/fuzzing/tooling.
- Rust: canonical production/consensus/security boundary.

No broad migration is justified; it would increase change surface without improving assurance.

## Security and malware assurance

The repository does **not** claim absolute immunity from hacking, malware, zero-days, compromised dependencies, malicious maintainers or hardware compromise.

For a defined threat class, evidence must be:

`threat → control → negative test → positive test → CI evidence → residual risk`.

Current controls provide evidence against defined classes such as action-reference substitution, known source-level defects, insecure reference primitives, deterministic-source violations and verifier-boundary errors. They do not establish immunity against unknown or future attacks.

## Traceability

```text
Vision
  → Concept
  → Components
  → Architecture
  → Code
  → Tests
  → Evidence
  → Finding
  → Fix
  → Re-test
  → Actual software state
```

A component is only considered present when implementation and executable evidence agree.

## Closure criteria

A finding is closed only after:

1. implementation;
2. source re-read;
3. positive and negative tests;
4. integration evidence where applicable;
5. static security analysis;
6. current GitHub Actions evidence;
7. synchronized status/roadmap/TODO/wiki documentation;
8. no contradictory duplicate implementation remains.

**Production readiness:** `NOT ESTABLISHED`.
