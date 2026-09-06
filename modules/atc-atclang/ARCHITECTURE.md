# ARCHITECTURE.md — atc-atclang
> Copyright © Michael Wroblewski / A-TownChain-Okosystems. All Rights Reserved.

## File Tree
```tree
├── .gitignore
├── ATCLANG_SPEC.md
├── CHANGELOG.md
├── COMPONENT_PLAN.md
├── CONTRIBUTING.md
├── FILE_REGISTER.md
├── LICENSE
├── README.md
├── ROADMAP.md
├── STATUS.md
├── __init__.py
├── compiler/
│   └── __init__.py
├── lexer/
│   └── __init__.py
├── parser/
│   ├── __init__.py
│   └── parser.py
├── programs/
│   └── atcos_main.atc
├── repl/
│   └── __init__.py
├── requirements.txt
├── stdlib/
│   ├── __init__.py
│   ├── chain.py
│   ├── encoding.py
│   ├── io.py
│   └── wallet.py
├── tests/
├── v03/
│   ├── __init__.py
│   └── atclang_v03_features.py
└── vm/
    └── __init__.py
```

## Module Descriptions
- **lexer/**: Lexical analyzer module converting raw ATC source code into a token stream.
- **parser/**: Syntactic parser building an Abstract Syntax Tree (AST) from token sequences.
- **compiler/**: ATC compiler target translating AST into bytecode and optimized execution instructions.
- **tests/**: Test suite validating language grammar rules, parser edge cases, and compiler outputs.
- **stdlib/** & **vm/**: Standard library utilities and lightweight virtual machine runtime for executing compiled ATC bytecode.

## Build System
Python setuptools packaging framework (`pyproject.toml`). Test execution managed via `pytest`.

## Dependencies
Python 3.10+, `pytest`, `ply` / `sly` parsing toolkits, AST visualization and processing tools.
