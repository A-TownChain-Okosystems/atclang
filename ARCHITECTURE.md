---
document_id: ATC-DOC-LANG-004
title: ATCLang Architecture
version: 1.0.0
status: active
owner: A-TownChain-Okosystems
created: 2026-09-07
updated: 2026-09-07
standard: ATC-STD-MD-001
---

# ATCLang Architecture

> Technische Architektur der proprietären System- und Contract-Sprache ATCLang.

## Systemübersicht

ATCLang ist als Multi-Pass-Compiler und Ausführungsumgebung strukturiert:

1. **Frontend (`src/atclang/frontend/`):** Lexer (Tokenizer) und Parser (AST-Generierung, 100% Parse-Rate).
2. **Semantik (`src/atclang/semantics/`):** TypeChecker, Scope-Analyse und Regeln SEM-001 bis SEM-012.
3. **Compiler & IR (`src/atclang/compiler/`):** Codegen, Optimierung und Transformation in ATC-IR.
4. **VM & Runtime (`src/atclang/vm/`, `src/atclang/runtime/`):** ATVM Bytecode-Interpreter und Driver Framework.
5. **Stdlib (`src/atclang/stdlib/`):** Standardbibliothek (Chain, Crypto, Math, Primitives, Wallet, IO, Encoding, Collections, String).

## Datenfluss

```text
Quellcode (.atc) -> Lexer -> AST -> TypeChecker (Semantik) -> IR Compiler -> Bytecode -> ATVM Runtime
```
