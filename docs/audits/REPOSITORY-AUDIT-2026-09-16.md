# ATCLang Repository Audit — 2026-09-16

Status: **IN PROGRESS — release blocked for production use until security/reference-boundary findings are resolved**

Audit mode: CI-independent source/static audit because GitHub Actions evidence is currently unavailable/incomplete.

## Scope

Checked individually:

- repository structure and governance files
- README / architecture / baseline / release-gate documentation
- Python/Rust language boundary
- compiler → VM → runtime connectivity
- TODO/FIXME/HACK/placeholder/stub markers
- obvious security-sensitive implementations
- deterministic/consensus-sensitive VM surface
- documentation consistency and implementation traceability
- file-format/language policy

## Architecture baseline

The repository documentation states that Rust is canonical for production compiler, verifier, ATVM, runtime, ABI/artifact validation, security/sandbox and CLI, while Python is the reference implementation / SDK / test and fuzzing tooling. This is the correct architectural direction for consensus-critical execution.

The current Python VM remains imported by compiler modules and the Python reference runtime. Therefore the reference/production boundary must be enforced explicitly so that reference stubs cannot be mistaken for secure production primitives.

## Findings

### F-20260916-ATCLANG-001

- Class: **P1**
- Category: **Security / Cryptographic correctness**
- Family: **ATCLang / Python reference VM / Cryptography / ECDSA**
- Tags: `P1 security crypto ecdsa reference-vm fail-closed`
- Evidence: `src/atclang/vm/atcvm.py` implements `ecdsa_sign()` as SHA-256 over string-concatenated data and private key, and `ecdsa_verify()` accepts any string beginning with `sig_`.
- Risk: this is not ECDSA and must never be treated as a signature primitive. If a production path reaches it, forged signatures are accepted.
- Required remediation: make these operations fail closed in the Python reference VM unless backed by a real, explicitly tested cryptographic implementation; production paths must resolve to the canonical Rust cryptographic implementation. Add negative tests proving arbitrary `sig_*` values are rejected.
- Closure evidence: source re-read + deterministic unit/negative tests + integration test proving production execution cannot dispatch to this reference primitive + CI/runtime evidence when GitHub Actions is restored.

### F-20260916-ATCLANG-002

- Class: **P1**
- Category: **Security / Authentication correctness**
- Family: **ATCLang / Python reference VM / JWT validation**
- Tags: `P1 security jwt authentication validation reference-vm`
- Evidence: `verify_jwt()` returns true for any non-empty token longer than ten characters.
- Risk: this is not JWT validation and can create authentication bypass if exposed outside reference-only tests.
- Required remediation: fail closed or delegate to a real, policy-constrained verifier. Define accepted algorithms, issuer/audience rules, expiration/not-before validation, signature verification and key handling.

### F-20260916-ATCLANG-003

- Class: **P1**
- Category: **Security / Network correctness**
- Family: **ATCLang / Python reference VM / Network boundary**
- Tags: `P1 security network false-success reference-vm`
- Evidence: `net_send()` always returns `True` without sending data.
- Risk: callers can interpret an operation as successfully transmitted when nothing was sent, breaking reliability/security assumptions.
- Required remediation: fail closed with an explicit `ReferenceImplementationError` or route to an injected test transport. Never report success for an unperformed network operation.

### F-20260916-ATCLANG-004

- Class: **P1**
- Category: **Security / RPC correctness**
- Family: **ATCLang / Python reference VM / RPC boundary**
- Tags: `P1 security rpc false-success reference-vm`
- Evidence: `rpc_call()` fabricates a HTTP-like 200 response without executing a request.
- Risk: false-success semantics can hide unavailable authorization, transport and response-validation logic.
- Required remediation: fail closed by default; test transports must be explicit dependency-injected mocks and must not masquerade as production transport.

### F-20260916-ATCLANG-005

- Class: **P1**
- Category: **Cryptographic / wallet correctness**
- Family: **ATCLang / Python reference VM / BIP39 / Address derivation**
- Tags: `P1 crypto wallet bip39 address reference-vm`
- Evidence: the embedded mnemonic implementation uses a short embedded word list and maps SHA-256 digest bytes into that list; `generate_atc_address()` generates an unrelated random value and hashes it rather than deriving an address from the supplied public-key material.
- Risk: outputs are not BIP-39 compliant and address generation is not key-bound.
- Required remediation: remove these as claimed protocol primitives or delegate to the canonical wallet implementation; add conformance vectors before allowing protocol use.

### F-20260916-ATCLANG-006

- Class: **P2**
- Category: **Determinism / consensus boundary**
- Family: **ATCLang / Python reference VM / nondeterministic host capabilities**
- Tags: `P2 determinism consensus random time vm-boundary`
- Evidence: the Python VM exposes random/time-sensitive operations alongside consensus-oriented opcodes.
- Risk: accidental use in consensus execution can create divergent state.
- Required remediation: make nondeterministic operations explicitly host-only and unavailable to canonical consensus execution; add verifier tests that reject them from consensus bytecode where required by the protocol.

### F-20260916-ATCLANG-007

- Class: **P2**
- Category: **Architecture / language policy enforcement**
- Family: **ATCLang / Rust-canonical boundary / Python reference implementation**
- Tags: `P2 architecture rust-canonical python-reference enforcement`
- Evidence: the documentation declares Rust canonical for production, but multiple Python compiler/runtime modules directly import `atclang.vm.atcvm`.
- Interpretation: this is consistent for a reference implementation, but the boundary is currently a convention rather than a demonstrated enforcement mechanism.
- Required remediation: add an explicit production-entrypoint guard and integration test proving production artifacts/execution resolve to the Rust implementation and cannot silently select the Python reference VM.

## Security posture

Static source review found no `pull_request_target`, mutable checkout refs, merge conflict markers, or obvious plaintext private-key patterns in the targeted ATCLang scan. This does **not** prove immunity to malware, supply-chain compromise, memory corruption, or runtime attacks.

For the findings above, the current protection claim is **not sufficient**: fake cryptography, permissive JWT validation and false-success network/RPC operations are themselves security boundaries that must be fail-closed.

## File format / language decision

- Markdown is appropriate for specifications, architecture, governance, audit and roadmap documentation.
- YAML is appropriate for machine-readable repository/governance metadata where already standardized.
- Python is appropriate for the reference implementation, SDK, testing and fuzzing roles documented by the repository.
- Rust is the appropriate canonical production language for consensus-critical compiler/VM/runtime/security components according to the repository's own baseline and architecture documents.
- No blind file migration was performed: changing formats/languages without preserving the canonical protocol boundary would increase risk.

## Verification state

- Static source findings: verified by current default-branch source inspection.
- Runtime tests: **not claimed**; GitHub Actions evidence is unavailable/incomplete.
- Findings are not closed until source changes are re-read and appropriate tests/runtime evidence are available.
- Production readiness: **NOT ESTABLISHED**.
