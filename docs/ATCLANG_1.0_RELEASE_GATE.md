# ATCLang 1.0.0 Release Gate

**Status:** NO-GO (Stand 2026-09-24)  
**Version:** 1.0.0  
**Date:** 2026-09-24  
**Authority:** ATC-STD-000 v1.3.0

This document is the machine-reviewable release gate for ATCLang 1.0.0. A version number, documentation claim, or successful unit-test run does not constitute release readiness.

## Gate matrix

| Gate | Requirement | Status |
|---|---|---|
| G0 | Repository baseline/build | PASS (documented; current CI evidence must still be refreshed) |
| G1 | Normative language specification | PASS |
| G2 | Semantic/type-checking specification | PASS |
| G3 | Canonical frontend/IR/bytecode emission and verification | IMPLEMENTED FOR CURRENT SUBSET — full language conformance remains OPEN |
| G4 | ATVM integration and execution conformance | OPEN |
| G5 | Standard library and host API completion | OPEN |
| G6 | ABI specification and compatibility tests | OPEN |
| G7 | Storage/state model | OPEN |
| G8 | Resource/gas model | OPEN |
| G9 | Deterministic compilation | OPEN |
| G10 | Deterministic execution/state-transition conformance | PARTIAL — deterministic Rust stack-VM path exists; ecosystem/ATVM conformance remains OPEN |
| G11 | Cross-component / cross-implementation conformance | OPEN |
| G12 | Negative/fuzz/malformed-input testing | OPEN |
| G13 | Security hardening | OPEN |
| G14 | Reproducible build | OPEN |
| G15 | Release artifacts/versioning | OPEN |
| G16 | Documentation completeness | PARTIAL |
| G17 | Compatibility/versioning policy | OPEN |
| G18 | Independent security audit | OPEN |
| G19 | Mainnet/production release | OPEN |

## Release rule

ATCLang 1.0.0 MUST NOT be marked production-ready while any required production gate is OPEN. The current implementation is a Rust-only canonical development track and is not production-ready.

## Canonical architecture

```text
ATCLang source
    -> lexer/parser
    -> semantic verification
    -> canonical ATC-IR
    -> canonical bytecode
    -> bytecode verifier
    -> ATVM
    -> deterministic state transition
```

Rust is the canonical compiler/execution/chain-facing implementation boundary. The former Python reference implementation has been removed and is not a production or consensus authority.

## Current implementation evidence

The Rust canonical core contains a deterministic lexer/parser/lowering path, an ATCB-1 bytecode container, deterministic opcode encoding, control-flow lowering, a deterministic stack VM, and structural bytecode verification for the implemented language subset.

The verifier and VM do not by themselves close production gates. Full language conformance, canonical IR, artifact/ABI contracts, capability enforcement, resource/gas accounting, host/state boundaries, ATVM integration, negative/fuzz testing, reproducible builds, and independent security review remain separate release requirements.

## Evidence required for GO

A GO decision requires committed, current evidence for every open gate, including:

- normative IR and bytecode specifications;
- compiler golden fixtures;
- bytecode verifier tests;
- ATVM integration/conformance fixtures;
- deterministic compilation and execution vectors;
- ABI/storage/resource model specifications;
- standard-library conformance tests;
- negative and fuzzing results;
- reproducible build evidence;
- independent security review;
- release artifact hashes and compatibility statement.

Until those artifacts exist and are independently reviewable, the authoritative release state remains NO-GO.