# ARCHITECTURE.md — atclang
> Copyright © Michael Wroblewski / A-TownChain-Okosystems. All Rights Reserved.

## File Tree
```tree
atclang/
├── README.md                 # ATCLang specification overview
├── ATCLANG_SPEC.md           # Formal language specification
├── compiler.py               # Top-level compiler CLI executable
├── lexer.py                  # Tokenizer entry point
├── parser.py                 # AST generator entry point
├── atclang/                  # ATCLang main standard library scripts
│   └── main.atc              # ATCLang runtime entry point
├── compiler/                 # Compiler backend (type checker, optimizer, code generator)
│   ├── compiler.py
│   ├── optimizer.py
│   └── type_checker.py
├── lexer/                    # Lexical scanner implementation
│   └── lexer.py
├── parser/                   # Grammar rules and AST node definitions
│   ├── ast_nodes.py
│   └── parser.py
└── programs/                 # Standard ATCLang program examples
    ├── atc8300.atc
    ├── atcos_main.atc
    ├── event_bus.atc
    └── kernel.atc
```

## Module Descriptions
- README.md — Guide to the ATCLang domain-specific smart contract language
- ATCLANG_SPEC.md — Formal EBNF syntax grammar and type rules specification
- compiler.py — Entry point CLI for compiling .atc code into bytecode
- lexer.py — Lexical analysis module converting source text into token streams
- parser.py — Parser module transforming tokens into Abstract Syntax Trees
- compiler/ — Type checking, optimization passes, and code emission pipeline
- lexer/ — Modular tokenizer engine
- parser/ — AST node declarations and recursive descent parsing logic
- programs/ — Reference .atc programs demonstrating language features

## Build System
- Python setuptools / pytest

## Dependencies
- Python 3.10+

## Status (Active/Migrated/Legacy)
Migrated to a-townchain-os / Legacy repo
