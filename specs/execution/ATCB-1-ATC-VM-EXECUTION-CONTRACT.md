---
spec_id: ATCB-ATVM-EXECUTION-001
title: "ATCB-1 / ATC-VM Execution Contract"
version: 0.1.0-DRAFT
status: SPEC-DRAFT — implementation and evidence pending
repository: atclang
layer: L0-Language / L1-Execution
owner: A-TownChain-Okosystems
license: Apache-2.0
---

# ATCB-1 / ATC-VM Execution Contract

## 1. Purpose

This document defines the contract between the canonical ATCLang artifact format (ATCB-1) and the canonical A-TownChain VM implementation.

ATCB-1 is a canonical module artifact. It MUST NOT be defined as the serialization of the VM's internal Op enum.

Canonical path:

    ATCLang
      -> ATC-IR
      -> IR verification
      -> Module / ABI validation
      -> ATCB-1
      -> independent verification
      -> canonical ATC-VM
      -> execution context
      -> state transition

This is a contract baseline. It does not claim that the complete compiler-to-VM path is implemented.

## 2. Explicit non-goals

This contract does not authorize:

- LoadLocal -> persistent Load mapping;
- StoreLocal -> persistent Store mapping;
- implicit i64 -> u64 casts;
- treating .ops as the canonical artifact format;
- bypassing the canonical state-transition execution gate;
- deleting the existing ATCLang reference VM before differential conformance exists.

## 3. Module envelope

An ATCB-1 module MUST contain these logical fields in canonical order:

| Field | Type |
|---|---|
| magic | 4 bytes |
| format_version | u16 |
| abi_version | u16 |
| vm_version | u16 |
| entry_function | u16 |
| function_count | u16 |
| capability_count | u16 |
| functions | sequence |
| capabilities | sequence |

Integer fields use little-endian encoding. No pointer, timestamp, host metadata, hash-map order, or other nondeterministic data may enter the artifact.

### 3.1 Function record

Each function record contains:

- function_id: u16
- param_count: u16
- local_count: u16
- return_arity: u16
- code_len: u32
- code: canonical instruction sequence

Function IDs MUST be unique. entry_function MUST reference an existing function.

The initial ABI baseline permits return_arity 0 or 1. Multi-value returns require an ABI revision.

## 4. Execution model

The VM is stack-based with explicit call frames.

A frame contains at minimum:

- function identifier;
- return program counter;
- caller stack boundary;
- parameter area;
- local area.

### 4.1 Locals

local_count defines frame-local storage.

Local access is private to the active frame and MUST NOT address persistent chain storage.

Therefore:

    ATCLang LoadLocal / StoreLocal
              !=
    ATC-VM persistent Load / Store

Persistent storage is a separate capability and ABI surface.

### 4.2 Arguments and returns

For Call(function_id, argc):

1. exactly argc arguments MUST be available;
2. arguments are transferred to the callee parameter area in source order;
3. the callee receives a fresh local frame;
4. the caller frame is suspended;
5. the callee returns exactly return_arity values;
6. returned values are transferred to the caller;
7. callee locals do not survive return.

The implementation MUST enforce a deterministic maximum call depth.

The entry function is invoked without implicit arguments unless a later ABI revision explicitly defines them.

## 5. Numeric semantics

The contract does not permit implementation-defined signed/unsigned conversion.

The initial ATCLang semantic domain is signed two's-complement i64:

- arithmetic overflow is a deterministic error, not wrapping;
- division by zero is a deterministic error;
- i64::MIN / -1 is a deterministic arithmetic error;
- comparisons use signed i64 ordering.

A VM MAY use another internal representation, but observable behavior MUST be identical.

## 6. Control flow

Jumps use the established PC-relative model:

    target = pc + 1 + displacement

The displacement is signed and little-endian.

Conditional jumps consume their condition from the operand stack. Zero is false; non-zero is true.

All jump targets MUST resolve to valid instruction boundaries.

## 7. Persistent storage boundary

Persistent state access is distinct from frame-local access.

A storage ABI MUST specify:

- key encoding;
- value encoding;
- read/write capabilities;
- gas cost;
- missing-key semantics;
- deterministic serialization;
- state-transition ordering.

Until that contract is frozen, ATCB local instructions MUST NOT be interpreted as persistent storage operations.

## 8. Gas and resources

Every executable instruction MUST have a deterministic resource cost in the canonical VM registry.

Insufficient gas/resources MUST cause deterministic termination. A failed execution MUST NOT expose a partial state transition.

## 9. Capabilities

A module declares required capabilities explicitly.

Capability identifiers are canonical and versioned.

The execution context MUST reject a module when a required capability is unavailable or unauthorized. A capability MUST NOT implicitly grant unrelated host access.

## 10. Verification layers

### IR verifier

Checks typed ATC-IR invariants before code generation.

### ATCB verifier

Checks at minimum:

- module envelope and versions;
- function identifiers;
- entry function;
- instruction boundaries;
- stack safety;
- local bounds;
- call targets and argument counts;
- return arity;
- control-flow targets;
- capability declarations;
- resource/gas metadata.

### Runtime execution gate

The canonical chain path MUST additionally validate:

- chain identity;
- network/genesis identity;
- protocol version;
- VM version;
- execution capabilities;
- gas/resource budget;
- state-transition preconditions.

The raw interpreter API MUST NOT be the canonical chain state-transition boundary.

## 11. Deterministic errors

The conformance matrix MUST cover:

- invalid module/version;
- invalid function reference;
- invalid local;
- stack underflow;
- invalid jump;
- invalid return arity;
- integer overflow;
- division by zero;
- call-depth exhaustion;
- capability rejection;
- out-of-gas;
- execution-context rejection.

Equivalent invalid artifacts MUST produce the same error class across conforming implementations.

## 12. Determinism

For fixed source, language/semantic version, ABI version, VM version, and initial state, a conforming implementation MUST produce:

- identical ATC-IR bytes;
- identical ATCB bytes;
- identical artifact hash;
- identical execution result;
- identical state transition;
- identical canonical error class on failure.

No clock, randomness, host identity, pointer address, locale, or platform-dependent serialization may affect these results.

## 13. V1 arithmetic conformance vector

Source:

    fn main() {
        return (7 + 3) * 2;
    }

Expected result: signed i64 value 20.

Required future pipeline:

    source
      -> AST
      -> semantic/type validation
      -> ATC-IR
      -> IR verification
      -> ATCB-1
      -> independent ATCB verification
      -> canonical ATC-VM
      -> execution gate
      -> result 20

V1 intentionally does not claim that locals, calls, storage, capabilities, or persistence are implemented.

## 14. Conformance progression

| Vector | Scope |
|---|---|
| V1 | arithmetic |
| V2 | local frame |
| V3 | Call / Return |
| V4 | control flow |
| V5 | persistent storage |
| V6 | gas |
| V7 | capabilities |
| V8 | deterministic errors |
| V9 | persistence/restart |
| V10 | Node -> State E2E |

The ATCLang VM remains a reference/differential backend until the canonical ATC-VM path passes the corresponding vectors.

## 15. Compatibility

Changes to module layout, ABI semantics, numeric semantics, instruction encoding, capability identifiers, or error classes require explicit versioning.

A runtime MUST NOT silently reinterpret an existing ATCB artifact.

## 16. Evidence gate

For each requirement:

1. specification;
2. implementation;
3. unit tests;
4. negative tests;
5. integration/conformance test;
6. determinism test;
7. CI evidence;
8. artifact/evidence record.

Until these exist, this contract remains a draft and no production-readiness claim is made.
