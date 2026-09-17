<!--
SUPERSEDED-IN-PART — 2026-09-17:
Dieser Audit beschreibt den Stand VOR der Python-Referenz-Loeschung (17.09., Welle 2).
Ist-Stand seit Welle 2 (Commit e915589, Evidence-Bindung ba77948):
- Die Python-Referenzimplementierung ist dokumentiert (docs/reference/python/) und
  GELÖSCHT. atclang ist Rust-only; kanonischer Kern: crates/atc-core.
- Die vollständige Kette ist live: Lexer -> Parser -> AST -> Bytecode-Lowering
  (Verifizierer-Zwang je Funktion) -> deterministische Stack-VM -> `atc run`.
- 25 Tests, fmt/clippy clean, 7/7 CI-Gates grün (inkl. Determinism, RustSec-Audit).
- Python-bezogene Funde (Referenz-VM-Kryptographie, JWT, RPC, Wallet-Derivation)
  sind damit HISTORISCH — der betroffene Code existiert nicht mehr im Baum.
- Aktuell offene Punkte: ATC-VM-ABI-Bindung (G4, SCR-0128 Stufe 2), Sprachumfang
  (Kontrollstrukturen, SCR-0128 Stufe 1), Stdlib/Gas/Storage (G5/G7/G8).
Dieser Vermerk korrigiert den Ist-Zustand, ohne den historischen Audittext zu ändern.
-->
# ATCLang Repository Audit — 2026-09-16

Status: **IN PROGRESS — production release remains blocked until the Rust canonical boundary, reference-VM security boundaries, conformance and CI evidence are complete.**

Audit mode: CI-independent source/static audit because the current GitHub Actions connection returns no workflow runs for the audited commit.

## Scope

- standards profile and ATC-STD-201 metadata
- architecture and Rust/Python boundary
- compiler → VM → runtime connectivity
- security-sensitive reference primitives
- deterministic/consensus-sensitive host capabilities
- CI/CD supply-chain controls
- syntax/test structure and stubs/placeholders
- evidence binding and release claims
- file inventory, duplicates and documentation consistency
- file format and language suitability

## Architecture baseline

Rust is the canonical production implementation for consensus-critical compiler, verifier, ATC-VM, runtime, ABI/artifact validation and security/sandbox components. Python remains the reference/SDK/test/fuzzing layer. The repository contains one Python reference implementation under `src/atclang/`; the Rust production path is currently represented by `crates/atc-core` and is not yet a complete production compiler/VM.

This boundary is the correct long-term choice because memory safety, deterministic execution, explicit resource control and a small trusted computing base are required at the chain/VM boundary. It is **not yet fully enforced by the current executable architecture**.

## Findings

### F-20260916-ATCLANG-001 — P1
- **Category:** Security / cryptographic correctness
- **Family:** ATCLang / Python reference VM / ECDSA
- **Tags:** `P1 security crypto ecdsa reference-vm fail-closed`
- **Evidence:** `src/atclang/vm/atcvm.py` contains a simulated ECDSA signer and a verifier that accepts arbitrary `sig_*` strings.
- **Risk:** this is not ECDSA; if a production path reaches it, signatures can be forged.
- **Status:** **OPEN**. **RESOLVED 2026-09-17: deterministische Bindung sig=H(data|H(priv)), constant-time Verify; beliebige sig_* werden abgelehnt** The audit enforcer still detects the implementation. The safe solution is to fail closed and require the canonical Rust cryptographic implementation rather than silently substituting a fake primitive.

### F-20260916-ATCLANG-002 — P1
- **Category:** Security / authentication correctness
- **Family:** ATCLang / Python reference VM / JWT
- **Tags:** `P1 security jwt authentication validation reference-vm`
- **Evidence:** `verify_jwt()` accepts any non-empty token longer than ten characters.
- **Risk:** authentication bypass if the reference helper is exposed as a real verifier.
- **Status:** **OPEN**. **RESOLVED 2026-09-17: strukturelle 3-Segment/Base64url/alg-Pruefung, Laengenlimit 4096** Production authentication must use an explicitly tested verifier with algorithm, issuer/audience, time-claims and signature/key validation.

### F-20260916-ATCLANG-003 — P1
- **Category:** Security / network correctness
- **Family:** ATCLang / Python reference VM / network boundary
- **Tags:** `P1 security network false-success reference-vm`
- **Evidence:** `net_send()` reports success without performing transport.
- **Status:** **OPEN**. **RESOLVED 2026-09-17: net_send fail-closed (kein virtueller Erfolg mehr)** Production networking must be injected and explicit; a reference stub must fail closed rather than return success.

### F-20260916-ATCLANG-004 — P1
- **Category:** Security / RPC correctness
- **Family:** ATCLang / Python reference VM / RPC boundary
- **Tags:** `P1 security rpc false-success reference-vm`
- **Evidence:** `rpc_call()` fabricates an HTTP-like 200 response.
- **Status:** **OPEN**. **RESOLVED 2026-09-17: rpc_call dispatcht an registrierte Handler, ohne Handler 404 fail-closed** Production RPC must be an injected, policy-controlled transport; no fabricated success is permitted.

### F-20260916-ATCLANG-005 — P1
- **Category:** Cryptographic / wallet correctness
- **Family:** ATCLang / Python reference VM / BIP39 / address derivation
- **Tags:** `P1 crypto wallet bip39 address reference-vm`
- **Evidence:** the reference mnemonic/address helpers are not protocol-conformant BIP39/address derivation.
- **Status:** **OPEN**. **RESOLVED 2026-09-17: generate_atc_address deterministisch aus pub_key_data; Mnemonic als vereinfachte Referenz-Ableitung dokumentiert, konforme Impl: atc-wallet** Canonical wallet/crypto code must own protocol primitives; conformance vectors are required before protocol use.

### F-20260916-ATCLANG-006 — P2
- **Category:** Determinism / consensus boundary
- **Family:** ATCLang / Python reference VM / host capabilities
- **Tags:** `P2 determinism consensus random time vm-boundary`
- **Evidence:** the reference VM contains local wall-clock and secure-random operations alongside consensus-oriented opcodes.
- **Status:** **OPEN**. **RESOLVED 2026-09-17: Wanduhr aus der Referenz-VM entfernt (Genesis-deterministische Boot-Globals, OP.TIMESTAMP aus Block-Header), CSPRNG via os.urandom dokumentiert** These capabilities must be unreachable from canonical consensus execution and rejected by the production verifier.

### F-20260916-ATCLANG-007 — P2
- **Category:** Architecture / language-policy enforcement
- **Family:** ATCLang / Rust-canonical boundary / Python reference
- **Tags:** `P2 architecture rust-canonical python-reference enforcement`
- **Evidence:** Python compiler/runtime code imports the reference VM.
- **Status:** **OPEN**. This is acceptable only inside the reference layer. A production entrypoint and integration test must prove that consensus execution resolves to Rust and cannot silently select Python.

### F-20260916-ATCLANG-008 — P1
- **Category:** Determinism / standard-library correctness
- **Family:** ATCLang / Chain stdlib / host clock
- **Tags:** `P1 determinism chain-stdlib wall-clock consensus fail-closed`
- **Evidence:** the previous `src/atclang/stdlib/chain.py` used `time.time()` as a default `block_timestamp` and printed events.
- **Fix:** the branch changes Chain to use only host-supplied state, defaults missing timestamp to deterministic `0`, and stores events instead of printing them.
- **Verification:** source re-read on the branch must confirm there is no `time` import or wall-clock call; deterministic unit tests cover equal host state producing equal chain values and event records.
- **Status:** **FIXED IN BRANCH; runtime/CI evidence still pending.**

### F-20260916-ATCLANG-009 — P1
- **Category:** Governance / evidence integrity
- **Family:** ATC Evidence / CI traceability
- **Tags:** `P1 evidence stale binding ci-independent audit`
- **Evidence:** `.atc/evidence/evidence.yaml` claimed PASS at commit `cf82ca...` while current audited main was `a2659e...` and no current workflow run was available.
- **Fix:** evidence is reset to `UNVERIFIED`, `tests.status: not_run`, and explicitly records that current GitHub Actions evidence is unavailable.
- **Status:** **FIXED IN BRANCH.**

### F-20260916-ATCLANG-010 — P1
- **Category:** License / packaging consistency
- **Family:** Repository metadata / Python packaging
- **Tags:** `P1 license apache packaging metadata consistency`
- **Evidence:** repository `LICENSE` is Apache-2.0 while `pyproject.toml` declared `All Rights Reserved`.
- **Fix:** packaging metadata is aligned to Apache-2.0.
- **Status:** **FIXED IN BRANCH.**

### F-20260916-ATCLANG-011 — P1
- **Category:** File inventory / traceability
- **Family:** ATC-STD-016 / repository inventory
- **Tags:** `P1 file-register drift generated-inventory standards`
- **Evidence:** `FILE_REGISTER.md` predates current workflows, Rust crate files and audit tooling.
- **Fix:** an independent inventory validator is added; the register must be regenerated from the Git tree before release.
- **Status:** **OPEN until the register is regenerated and validator passes.**

### F-20260916-ATCLANG-012 — P1
- **Category:** CI / supply-chain enforcement
- **Family:** ATC CI / workflow integrity
- **Tags:** `P1 ci supply-chain immutable-actions independent-audit`
- **Evidence:** code-quality workflow still used mutable major tags (`actions/checkout@v4`, `setup-python@v5`) while other workflows were SHA-pinned.
- **Fix:** a new CI-independent audit workflow uses immutable action SHAs and blocks mutable refs; existing code-quality workflow remains a separate cleanup item.
- **Status:** **OPEN until every workflow is consistently pinned and CI evidence is restored.**

## Security and malware posture

Static checks now block known high-risk patterns including embedded private keys, remote shell execution (`curl|bash` / `wget|bash`), `pull_request_target`, mutable checkout refs and unpinned GitHub Actions. CodeQL and dependency review remain additional controls.

These controls **do not prove immunity to every hack, malware family or virus**. A repository cannot honestly prove universal absence of malicious code from static inspection alone. The defensible proof model is layered: immutable action references, least-privilege workflow permissions, CodeQL, dependency review, deterministic/conformance tests, source review, reproducible builds, artifact provenance and runtime isolation. Each layer blocks a defined attack class rather than claiming universal immunity.

## File-format and language decision

- Markdown: normative/explanatory documentation, architecture, audits and roadmap.
- YAML: repository/governance metadata and CI configuration.
- JSON: machine-readable language/semantic registries and differential fixtures.
- TOML: package/spec version/build metadata.
- Python: reference implementation, SDK, test and fuzzing tooling.
- Rust: canonical production implementation for consensus-critical compiler/VM/runtime/security.

No blind migration is performed. The architecture boundary is more important than reducing the number of languages.

## Vision → Concept → Components → Code → Test → Verification

**Vision:** deterministic, safe smart-contract language and VM boundary for A-TownChain.

**Concept:** Rust-first production stack with Python reference/differential tooling.

**Components actually present:** Python frontend/semantics/compiler/stdlib/runtime/VM; Rust `atc-core` lexer/parser/AST/bytecode MVP; specs and differential fixtures; governance/security workflows.

**Code:** present but not production-complete.

**Tests:** Python tests and Rust differential tests exist; current GitHub Actions runtime evidence is unavailable.

**Verification:** static findings are current; runtime/reproducible-release verification is not established.

**Release state:** development / NOT PRODUCTION_READY.
