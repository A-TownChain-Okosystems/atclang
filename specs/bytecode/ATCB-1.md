# ATCLang Canonical Bytecode ATCB-1

**Status:** Draft implementation baseline
**Authority:** ATC-STD-000 v1.3.0
**Scope:** G3 canonical bytecode encoding and structural verification

## 1. Deterministic container

Every bytecode stream starts with:

| Field | Size | Encoding |
|---|---:|---|
| Magic | 4 | ASCII `ATCB` |
| Format version | 2 | unsigned little-endian, currently `1` |
| Instruction count | 4 | unsigned little-endian |
| Instructions | variable | opcode-specific canonical encoding |

No host endianness, pointer value, hash-map iteration order, or platform metadata is permitted in the encoding.

## 2. Opcodes

| Opcode | Instruction | Operand |
|---:|---|---|
| `0x01` | `ConstI64` | i64 LE |
| `0x02` | `LoadLocal` | u16 LE |
| `0x03` | `StoreLocal` | u16 LE |
| `0x10` | `Add` | none |
| `0x11` | `Sub` | none |
| `0x12` | `Mul` | none |
| `0x13` | `Div` | none |
| `0x14` | `Neg` | none |
| `0x20` | `Call` | function:u16 LE, argc:u16 LE |
| `0x30` | `Return` | none |
| `0x31` | `Pop` | none |

## 3. Verification baseline

The Rust canonical verifier rejects:

- operand-stack underflow;
- references to undeclared locals;
- references to undeclared function indices;
- `Return` without exactly one result on the operand stack.

This is a structural verifier baseline, **not yet the complete ATVM verifier**. Control-flow joins, type safety, resource accounting, ABI, storage access and cryptographic host capabilities remain open release gates.

## 4. Canonical evidence

The implementation is covered by Rust unit tests for deterministic encoding, valid return programs, stack underflow and invalid local access. These tests are implementation evidence for the G3 baseline; they do not close G3/G4/G9/G10/G11/G13/G14/G18.
