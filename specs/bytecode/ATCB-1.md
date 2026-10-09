# ATCLang Canonical Bytecode ATCB-1

**Status:** Implementation baseline. NORMATIVE CARRIER IS
`specs/bytecode/SPEC.md` (ATC-BC-001 v1.0.0-FROZEN, ATCB v1, frozen
2026-10-06). In case of conflict, ATC-BC-001 v1.0.0-FROZEN wins.
**Authority:** ATC-STD-000 v1.3.0 / ATC-BC-001 v1.0.0
**Scope:** G3 canonical bytecode encoding and structural verification

Corrections against the earlier revision of this file: endianness is
big-endian (not little-endian), and the opcode catalog has 19 opcodes
including comparison and jump instructions (Return = 0x21, Pop = 0x40,
Jump = 0x30 / JumpIfFalse = 0x31). See SPEC.md sections 2 and 3.

## 1. Deterministic container

Every bytecode stream starts with:

| Field | Size | Encoding |
|---|---:|---|
| Magic | 4 | ASCII `ATCB` |
| Format version | 2 | unsigned big-endian, currently `1` |
| Instruction count | 4 | unsigned big-endian |
| Instructions | variable | opcode-specific canonical encoding (big-endian) |

No host endianness, pointer value, hash-map iteration order, or platform
metadata is permitted in the encoding.

## 2. Verification baseline

The Rust canonical verifier rejects (fail-closed): magic mismatch, version
mismatch, count overflow, unknown opcodes, truncated instructions, trailing
bytes; and structurally: operand-stack underflow, references to undeclared
locals or function indices, invalid jump targets, missing or inconsistent
returns, division by constant zero.

This is the structural verifier baseline, **not yet the complete ATVM
verifier**. Type safety, resource accounting, ABI, storage access and
cryptographic host capabilities remain open release gates.

## 3. Canonical evidence

The implementation is covered by Rust unit tests for deterministic encoding,
canonical vector lock, valid return programs, stack underflow, invalid local
access and fail-closed decode cases. These tests are implementation evidence
for the G3 baseline; they do not close G4/G9/G10/G11/G13/G14/G18.
