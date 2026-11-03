# ATCLang Component and Function Catalog

- **Repository:** `A-TownChain-Okosystems/atclang`
- **Baseline:** `main` at catalog preparation time; each source file's blob SHA is recorded below.
- **Purpose:** source-derived inventory for completeness reviews, API ownership, test coverage, and explicit residual tracking.
- **Status:** inventory baseline, not a production-readiness declaration.

## Scope and completeness rules

This catalog inventories the active Rust implementation and checked-in integration tests. It does not treat historical Python references, README claims, or an issue's status as proof of current implementation. A component is considered inventoried only when its current source path and public entry points are recorded. A function is considered verified only when a current test/CI run provides evidence; names in this catalog alone are not verification evidence.

Canonical production language core: `crates/atc-core`.
Canonical ATC-VM implementation: `a-townchain/components/vm`. This repository must not create a competing production VM.

## Component catalog

| ID | Component / path | Responsibility and current public surface | Source blob SHA | Current test evidence in repository |
|---|---|---|---|---|
| C-01 | `crates/atc-core/src/lib.rs` | Crate API exports: `artifact`, `ast`, `bytecode`, `ir`, `lexer`, `lower`, `native`, `parser`, `value`, `vm`. | `b10786e8b26597dda844575ff1083a9492e82ce1` | Integration/unit tests under crate |
| C-02 | `lexer.rs` | `Token`, `LexError`, `tokenize(src)`; lexical recognition and invalid-character rejection. | `6f503a1b1c7a7145284eb5670830946fdcfdac09` | lexer unit tests |
| C-03 | `parser.rs` | `ParseError`, `parse_program(src)`; statements, functions, types, expressions, precedence, if/else, while, calls. | `993df7a9a6626d869ef3e22f02a006fa13466586` | parser unit tests |
| C-04 | `ast.rs` | AST model: `Expr`, `TypeHint`, `LetStmt`, `Param`, `FunctionDef`, `Stmt`, `Program`; `Program::to_json()`. | `8721d367971ac93db2578303006045bac754993b` | parser and differential tests exercise serialization |
| C-05 | `lower.rs` | `LowerError`, `CompiledFunction`, `CompiledProgram`; `CompiledProgram::function_count()`, `CompiledProgram::verify()`, `lower_program(program)`; source AST to stack bytecode. | `ab3c28accab95339594fb5d797d83bc855ef0d0f` | lower unit tests; end-to-end tests |
| C-06 | `bytecode.rs` | `Instruction`, `Bytecode`, `VerifyError`; `Instruction::encode()`, `Bytecode::encode()` (legacy), `encode_canonical()`, `verify()`, `verify_with_signatures()`; ATCB encoding and control-flow/stack validation. | `d63ba13087a71d6f06ec44c0dc2496644906eeea` | verifier and canonical encoding unit tests |
| C-07 | `artifact.rs` | ATCA artifact types and limits; `Artifact::from_program()`, `canonical_payload()`, `compute_hash()`, `encode()`, `verify()`, `decode_and_verify()`, `into_program()`; verified artifact accessors. | `1b98def2f848a51c147eaad13a39fd8154fa2b06` | deterministic hash, round-trip, tamper rejection, metadata canonicality tests |
| C-08 | `vm.rs` | `RunError`, `MAX_CALL_DEPTH`, `MAX_STEPS`, `execute_verified(artifact)`; deterministic i64 stack execution with checked arithmetic and bounded steps/depth. Internal `execute` is crate-private. | `009bdec170527898957b9622cb29ec406f77ed81` | invalid program, non-termination bound, overflow; integration runtime tests |
| C-09 | `native.rs` | Native-contract AST structures; `parse_native_contract(src)`, `validate_native_contract(contract)`; directives, state declarations, function signatures, capability/policy decorators. | `43fdf67e3b9b57f38aed5c008ae6e8da3cc9e477` | native parser positive and negative tests |
| C-10 | `value.rs` | `AbiType`, `U256`, `TypedValue`; `AbiType::from_name()`, `TypedValue::abi_type()`, `TypedValue::is_type()`. | `cb720e71cbdc26f01cae36388a99d6f2c1a5d8a0` | canonical numeric type and identity tests |
| C-11 | `ir.rs` | `ProtocolType`, `IrType`, `IrValue`; `ProtocolType::host_type()`, `IrValue::ir_type()`; separates protocol counters and ABI economic values. | `081cf8df0600cb952fc2b569122eed5a22912047` | ABI/protocol domain separation tests |
| C-12 | `main.rs` | `atc` CLI; internal `compile_to_bytecode()` and `main()`; command-line compile/check/run paths. | `95ffe8f6c37fb7d687f77f2c778e3802cf34d760` | CLI integration tests |
| C-13 | `tests/cli.rs` | CLI corpus checks, invalid program/call rejection, runtime behavior, Rust-only production CLI boundary. | `ffd1883cdd838c7331dd2d0aeaaab22ae8677bf5` | 4 named integration tests in source |
| C-14 | `tests/differential.rs` | Common-subset differential corpus conformance. | `5f588cb83291ea1be90ef455a15f9d6bce8bd193` | one differential integration test |
| C-15 | `tests/run.rs` | End-to-end compile/verify/execute, calls, entry function, divide-by-zero, overflow, recursion and fail-closed lowering. | `d4e758b4213ca433778d2d076915459cc563b6e9` | named runtime integration tests |
| C-16 | `tests/stdlib_reference_conformance.rs` | Test/reference helpers for BE u128/U256, length-delimited canonical bytes, SHA-256, checked arithmetic/casts and require. **This is test-side reference code, not proof of a production stdlib module.** | `a7ada9f5e3c8597ca647cec206201e1ef0ede68c` | helper-specific positive and negative tests |
| C-17 | `specs/` | Normative/draft specifications for ABI, artifact, bytecode, execution, gas, IR, language, profiles, runtime classification, security, semantics, stdlib and VM. | Inventory tracked in `FILE_REGISTER.md`; individual spec SHAs not recorded in this table | Conformance vectors and release-gate documents |
| C-18 | `tools/` | `ci_independent_audit.py`, `determinism_check.py`; CI-independent repository checks and determinism checks. | Paths inventoried in `FILE_REGISTER.md` | Must be run against the exact candidate SHA |
| C-19 | `crates/atc-core/differential/corpus/` and `expected/` | Paired source fixtures and expected AST JSON for arithmetic, calls, comparisons, conditionals, loops, functions and declarations. | Paths inventoried in `FILE_REGISTER.md` | Exercised by CLI and differential tests |
| C-20 | `.github/workflows/` | Cargo audit, independent audit, quality, CodeQL, dependency review, determinism, evidence binding, governance, markdown lint and test-suite workflows. | Workflow files inventoried in `FILE_REGISTER.md` | Status must be read from current GitHub Actions runs; no status inferred here |

## Function and API inventory

This is the source-visible public API at the recorded blob SHAs. Private helpers are intentionally not promoted into a public API catalog.

### Lexing and parsing

- `tokenize(src: &str) -> Result<Vec<Token>, LexError>`
- `parse_program(src: &str) -> Result<Program, ParseError>`
- `Program::to_json() -> String`

### Lowering and validation

- `lower_program(prog: &Program) -> Result<CompiledProgram, LowerError>`
- `CompiledProgram::function_count() -> u16`
- `CompiledProgram::verify() -> Result<(), LowerError>`
- `Bytecode::verify(local_count, function_count)`
- `Bytecode::verify_with_signatures(...)`
- `Bytecode::encode_canonical() -> Result<Vec<u8>, VerifyError>`
- `Artifact::verify() -> Result<VerifiedArtifact, ArtifactError>`
- `Artifact::decode_and_verify(bytes) -> Result<VerifiedArtifact, ArtifactError>`

### Artifacts and runtime

- `Artifact::from_program(...)`
- `Artifact::canonical_payload() -> Result<Vec<u8>, ArtifactError>`
- `Artifact::compute_hash() -> Result<[u8; 32], ArtifactError>`
- `Artifact::encode() -> Result<Vec<u8>, ArtifactError>`
- `VerifiedArtifact::metadata()`
- `VerifiedArtifact::artifact_hash()`
- `VerifiedArtifact::into_program()`
- `execute_verified(artifact: &VerifiedArtifact) -> Result<i64, RunError>`
- Runtime limits: `MAX_CALL_DEPTH = 1024`, `MAX_STEPS = 1_000_000`

### Native contract syntax and values

- `parse_native_contract(src: &str) -> Result<NativeContract, NativeParseError>`
- `validate_native_contract(contract: &NativeContract) -> Result<(), NativeParseError>`
- `AbiType::from_name(name: &str) -> Option<AbiType>`
- `TypedValue::abi_type()`, `TypedValue::is_type(ty)`
- `ProtocolType::host_type()`, `IrValue::ir_type()`

### CLI

The `atc` binary exposes compile, check and run workflows according to the current README and `main.rs`. CLI behavior is owned by the Rust binary; the integration test `production_cli_boundary_is_rust_only` specifically guards against silently restoring the historical Python VM as the production path.

## Completeness gaps and required follow-up

The following are **review findings from the current source inventory**, not claims that the relevant feature is entirely absent from every specification or other repository.

| ID | Area | Observed gap / risk | Required next action | Exit evidence |
|---|---|---|---|---|
| G-01 | Catalog generation | This inventory is manually source-derived and blob-SHA-bound; it can drift after source changes. | Add a deterministic generator that extracts Rust modules, public symbols, tests, specs and workflows from the checked-out tree; fail CI when generated catalog differs. | Generator test plus clean regeneration diff on exact SHA |
| G-02 | Native contracts | `native.rs` parses contract declarations and stores function bodies as tokens; this catalog does not identify a native-contract lowering/ABI execution path. | Define the boundary and either implement reviewed lowering or explicitly mark parsing-only behavior in conformance docs. Do not invent a second VM. | Positive/negative native conformance vectors and explicit unsupported-case tests |
| G-03 | Value model vs execution | `value.rs` includes `U256`/typed ABI values, while `vm.rs` executes `i64` values. The current surface therefore does not establish end-to-end typed/U256 execution. | Define the type/ABI boundary and tests before extending execution semantics; align with canonical ATC-VM and standards. | ABI vectors, overflow/underflow negatives, cross-component conformance |
| G-04 | Standard library | The checked-in stdlib reference-conformance file contains test/reference helpers; it does not by itself prove a production stdlib implementation or compiler binding. | Inventory each specified stdlib function against Rust implementation, compiler binding, vectors and canonical VM support. Mark each IMPLEMENTED / VERIFIED / RESIDUAL. | One row per function with implementation path, vector IDs and exact-SHA test evidence |
| G-05 | Bytecode compatibility | `bytecode.rs` retains a legacy little-endian `encode()` alongside canonical `encode_canonical()`. | Audit all callers and normative docs; keep legacy use explicit and non-consensus, or remove only in a reviewed compatibility change. | Caller search, compatibility decision, golden vectors |
| G-06 | End-to-end artifact path | Artifact verification and `execute_verified` exist, but the CLI's compile/run route must be checked to ensure the consensus-facing artifact path is used wherever required. | Trace CLI and integration boundaries; document which path is for local execution vs consensus artifact execution. | End-to-end test that tampered/unverified artifacts cannot enter the authoritative execution boundary |
| G-07 | Security and CI evidence | Cataloging tests does not indicate the latest Actions status or release gate. | Run current tests, independent audit, determinism check and applicable GitHub Actions on the exact head SHA; record run/job/step and exit evidence. | Exact SHA plus Run → Job → Step → exit/log; failures remain RESIDUAL |

## Test and evidence matrix

| Test surface | Primary command / location | What it can establish | What it does not establish alone |
|---|---|---|---|
| Rust unit and integration tests | `cargo test --manifest-path crates/atc-core/Cargo.toml` | Behavior exercised by tests on that checked-out tree | Production readiness, external canonical VM compatibility, or current remote CI state |
| Independent audit | `python3 tools/ci_independent_audit.py` | Checks implemented by the audit script on that tree | Security correctness outside its checks |
| Determinism checker | `python3 tools/determinism_check.py` | Determinism rules covered by the checker | Full consensus conformance |
| GitHub Actions | Current runs for candidate SHA | Remote workflow outcomes for exact commit | Any check that is not actually run or whose logs are unavailable |
| Canonical VM conformance | `a-townchain/components/vm` plus shared vectors | Cross-component behavior once vectors are wired and run | Not established by ATCLang-local tests alone |

## Status vocabulary

- **IMPLEMENTED:** code exists at the referenced path.
- **VERIFIED:** exact-SHA test/CI evidence passes for the stated scope.
- **RESIDUAL:** a gap, failing gate, unavailable log, unverified path, or unresolved specification boundary remains.
- **PRODUCTION_READY:** prohibited as an inference from this catalog alone; requires all applicable release, security, reproducibility and canonical conformance gates.

## Update protocol

1. Read the current source tree and exact candidate commit before changing this catalog.
2. Update component rows when paths, exported APIs, tests, specs or workflows change.
3. Never label a function VERIFIED solely because it appears in source or has a test name.
4. Regenerate the catalog and inventory deterministically; avoid hand-editing generated artifacts.
5. Keep unresolved items visible as RESIDUAL until exact-SHA evidence closes them.
