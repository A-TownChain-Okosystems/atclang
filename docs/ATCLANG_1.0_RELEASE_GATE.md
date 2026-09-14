# ATCLang 1.0.0 Release Gate

**Status:** `NO-GO`  
**Version:** 1.0.0  
**Date:** 2026-09-14  
**Authority:** ATC-STD-000 v1.3.0

This document is the machine-reviewable release gate for ATCLang 1.0.0. A version number, documentation claim, or successful unit-test run does not constitute release readiness.

## Gate matrix

| Gate | Requirement | Status |
|---|---|---|
| G0 | Repository baseline/build | PASS (documented) |
| G1 | Normative language specification | PASS |
| G2 | Semantic/type-checking specification | PASS |
| G3 | Canonical IR, bytecode emission and verification | PARTIAL — ATCB-1 baseline implemented |
| G4 | ATVM integration and execution conformance | OPEN |
| G5 | Standard library and host API completion | OPEN |
| G6 | ABI specification and compatibility tests | OPEN |
| G7 | Storage/state model | OPEN |
| G8 | Resource/gas model | OPEN |
| G9 | Deterministic compilation | OPEN |
| G10 | Deterministic execution | OPEN |
| G11 | Cross-implementation conformance | OPEN |
| G12 | Negative/fuzz/malformed-input testing | OPEN |
| G13 | Security hardening | OPEN |
| G14 | Reproducible build | OPEN |
| G15 | Release artifacts/versioning | OPEN |
| G16 | Documentation completeness | PARTIAL |
| G17 | Compatibility/versioning policy | OPEN |
| G18 | Independent security audit | OPEN |
| G19 | Mainnet/production release | OPEN |

## Release rule

ATCLang 1.0.0 MUST NOT be marked production-ready while any P0 gate is OPEN. The current P0 blockers are G3, G4, G9, G10, G11, G13, G14 and G18.

## Canonical architecture

```text
ATCLang source
    -> lexer/parser
    -> semantic verifier
    -> canonical ATC-IR
    -> canonical bytecode
    -> bytecode verifier
    -> ATVM
    -> deterministic state transition
```

Rust is the canonical execution/chain-facing implementation boundary. Python reference tooling may be used for development and differential testing, but it MUST NOT be treated as consensus authority.

## Current implementation evidence

The Rust canonical core now contains an ATCB-1 bytecode container, deterministic opcode encoding, and a structural bytecode verifier. The normative baseline is `specs/bytecode/ATCB-1.md`.

This closes no production gate by itself. The verifier is intentionally limited to structural stack/local/function checks; control-flow, type safety, ABI, storage, gas/resource accounting, host capabilities and ATVM execution remain separate gates.

## Evidence required for GO

A GO decision requires committed evidence for every open gate, including:

- normative IR and bytecode specification;
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

Until those artifacts exist and are independently reviewable, the authoritative release state remains `NO-GO`.
