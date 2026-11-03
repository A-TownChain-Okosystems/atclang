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

## ATCB-1 / ATC-VM Execution Contract

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

This is a draft execution-boundary contract. It does not claim that the complete compiler-to-VM path is implemented.

**Normative precedence (blocking clarification):** `specs/bytecode/SPEC.md` (ATC-BC-001 v1.0.0-FROZEN) is the sole normative definition of ATCB v1 container geometry and instruction encoding. This draft MUST NOT redefine those bytes. In particular, ATCB v1 is a flat `ATCB` + big-endian version/count + instruction stream; it has no module-section envelope. The module/function/ABI/capability model below is therefore a *proposed execution/ABI design only*, not an ATCB v1 wire format. It MUST NOT be serialized into or assumed present in an ATCB v1 stream without an approved, versioned normative change.

Until that separate ABI/container decision is approved, only the frozen ATCB v1 bytecode contract is normative for encoding. Any richer module metadata must remain outside the ATCB v1 byte stream and be explicitly specified by the owning artifact/ABI contract. No production VM behavior is implied by this draft.

## 2. Explicit non-goals

This contract does not authorize:

- LoadLocal -> persistent Load mapping;
- StoreLocal -> persistent Store mapping;
- implicit i64 -> u64 casts;
- treating .ops as the canonical artifact format;
- bypassing the canonical state-transition execution gate;
- deleting the existing ATCLang reference VM before differential conformance exists.

## 3. ATCB v1 encoding boundary

ATCB v1 byte encoding is defined exclusively by `specs/bytecode/SPEC.md` (ATC-BC-001 v1.0.0-FROZEN). This section records the cross-boundary constraints and does not define a second encoding.

The frozen container is:

| Field | Size | Encoding |
|---|---:|---|
| Magic | 4 bytes | ASCII `ATCB` |
| Format version | u16 | Big-endian; currently 1 |
| Instruction count | u32 | Big-endian |
| Instructions | variable | Frozen opcode-specific encoding; all multi-byte operands big-endian |

Requirements:

- A producer MUST emit the canonical bytes defined by the frozen bytecode specification and `Bytecode::encode_canonical()`.
- A consumer MUST reject invalid or non-canonical ATCB v1 input according to the frozen specification; it MUST NOT silently reinterpret the stream as a different module format.
- `Bytecode::encode()` is documented as legacy/non-canonical and MUST NOT be used as the canonical artifact encoding.
- Function tables, ABI version, VM version, entry function, capabilities, and other module metadata are **not fields in the frozen ATCB v1 container**. Their transport and validation remain unresolved in a separately versioned ABI/artifact contract.
- The proposed function-record and module-envelope layout from earlier drafts is withdrawn as an ATCB v1 wire-format definition. It may only return through a normative, versioned change with updated golden vectors and cross-runtime conformance evidence.

## 3.1 Unresolved module/ABI design (non-normative)

The following items remain design questions, not claims about the ATCB v1 byte stream:

- function identifiers and function table representation;
- parameter/local counts and return arity;
- entry-function selection;
- ABI and VM version binding;
- capability declarations and their canonical encoding;
- the boundary between the ATCA artifact envelope and ATCB bytecode payload.

No implementation may assume these fields are present in ATCB v1 until the normative owner has specified and versioned them.

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

The displacement is signed and big-endian, consistent with the frozen ATCB v1 opcode encoding.

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

Changes to module layout, ABI semantics, numeric semantics, instruction encoding, capability identifiers, or error classes require explicit versioning. Any change to ATCB v1 bytes must go through the normative change process for `specs/bytecode/SPEC.md`; this draft alone cannot amend the frozen format.

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
