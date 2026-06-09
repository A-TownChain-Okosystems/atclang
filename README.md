# ATCLang — A-TownChain Programming Language
![Version](https://img.shields.io/badge/ATCLang-v0.2.0--alpha-a259ff?style=for-the-badge)

Proprietäre Blockchain-Programmiersprache des A-TownChain Ökosystems.

## Features
- Statisch typisiert: `u8`, `u16`, `u32`, `u64`, `u128`, `bool`, `string`, `bytes32`, `Address`
- Blockchain-Primitiven: `require()`, `emit()`, `safe_add()`, `caller`, `now()`
- Eigene VM: Stack-basiert, 30+ Opcodes, 128 Call-Depth-Limit, 10M Gas-Limit
- REPL, Compiler, Stdlib inklusive

## Repo-Struktur
```
atclang/
├── lexer/      Token-Erkennung
├── parser/     AST-Generierung
├── compiler/   Bytecode-Kompilierung
├── vm/         Stack-VM
├── repl/       Interaktive Shell
└── stdlib/     Built-in Funktionen
```

## Wiki
📖 [ATCLang Wiki](https://github.com/A-TownChain-Okosystems/atclang-wiki)
