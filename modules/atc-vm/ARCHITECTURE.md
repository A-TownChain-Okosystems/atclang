# ARCHITECTURE.md — atc-vm

> Copyright © Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.

## File Tree
```tree
atc-vm/
├── requirements.txt — Python dependencies
├── setup.py — pip installation configuration
├── README.md — ATC Virtual Machine overview
├── Cargo.toml — ShivaVM Rust workspace manifest (planned port, not yet implemented)
└── vm/
    ├── atcvm.py — Main VM execution engine
    ├── opcodes.atc — Instruction set opcodes
    ├── stack.atc — Operand stack implementation
    ├── gas_meter.atc — Gas metering and resource limits
    ├── interpreter.atc — Bytecode interpreter
    └── bytecode_format.atc — Bytecode serialization format
```

## Module Descriptions
- `vm/atcvm.py` — Main Virtual Machine class with stack-based execution
- `opcodes.atc` — ATC VM instruction set definitions
- `stack.atc` — Operand and call stack management
- `gas_meter.atc` — Deterministic gas metering for opcode execution
- `interpreter.atc` — Bytecode interpreter loop
- `bytecode_format.atc` — Binary bytecode serialization/deserialization

## Build System
- Python 3.11+ (current implementation)
- Rust workspace (Cargo.toml created, src/ port planned but not yet implemented)

## Dependencies
- atc-blockchain (blockchain core for smart contract execution)
- atc-contracts (smart contract templates)

## Status (Active/Migrated/Legacy)
Active (Python, Virtual Machine) — Rust port planned
