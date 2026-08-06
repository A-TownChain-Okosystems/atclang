# ⚡ ATCLang Compiler & Runtime Engine

> ## 🤖 Fuer KI-Agenten — Pflichtlektuere vor jeder Aenderung
> Governance liegt zentral im Wiki-Repo `a-townchain-os-docs`:
> 1. [`AGENT_POLICY.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/AGENT_POLICY.md) — verbindliche Regeln, Reality-Check, Konsolidierungsziel
> 2. [`AGENT_COORDINATION.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/AGENT_COORDINATION.md) — wer arbeitet gerade woran, Todos, Agent-IDs
> 3. [`DECISIONS_REGISTER.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/DECISIONS_REGISTER.md) — verbindliche Architektur-Entscheidungen

**ATCLang Compiler & Execution Stack (v0.3.0)** — Proprietäre, performante Programmiersprache für das A-TownChain Ökosystem mit nativer Unterstützung für Smart Contracts, Kernel-Services und P2P-Netzwerke. Durchsetzung der **ATC-99 First Policy**.

[![Layer](https://img.shields.io/badge/Layer-L2--L4-purple)](https://github.com/A-TownChain-Okosystems)
[![KAI-OS](https://img.shields.io/badge/KAI--OS-v1.0.0-blue)](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs)
[![Org](https://img.shields.io/badge/Org-A--TownChain--Okosystems-green)](https://github.com/A-TownChain-Okosystems)
[![Wiki](https://img.shields.io/badge/Wiki-📖_atclang--wiki-blue)](https://github.com/A-TownChain-Okosystems/atclang-wiki)

---

## 🏛️ Architektur & Pipeline

ATCLang transformiert Quellcode in ATVM-Bytecode und führt diesen in einer isolierten Register/Stack-basierten Virtual Machine aus:

```
+------------------+     +------------------+     +------------------+
| Quellcode (.atc) | --> |   Lexer Engine   | --> | Tokens Stream    |
+------------------+     +------------------+     +------------------+
                                                           |
                                                           v
+------------------+     +------------------+     +------------------+
| ATVM Bytecode    | <-- | AST Compiler     | <-- | Parser & AST     |
+------------------+     +------------------+     +------------------+
         |
         v
+------------------+
|  ATVM Runtime    | (Execution & State Engine)
+------------------+
```

---

## 🧩 Komponenten Übersicht

| Komponente | Verzeichnis / Datei | Beschreibung |
|------------|---------------------|--------------|
| **Lexer Engine** | `lexer/lexer.py`, `lexer.py` | Tokenisierung, Schlüsselwörter (`fn`, `let`, `if`, `contract`, `policy`), Operatoren |
| **Parser & AST** | `parser/parser.py`, `ast_nodes.py` | Rekursiver Abstiegs-Parser, Erzeugung des Abstract Syntax Tree (AST) |
| **Compiler** | `compiler/compiler.py`, `compiler.py` | AST-zu-Bytecode Übersetzung, Opcode-Generierung, Symboltabellen |
| **Virtual Machine** | `vm/atcvm.py`, `vm.py` | Stack-basierte Ausführungsumgebung, Call Stack, Frame Pointer, Memory Management |
| **Standard Library** | `stdlib/atc_stdlib.py` | Basis-Builtins für String, Math, I/O und Datenstrukturen |
| **REPL Engine** | `repl/repl.py` | Interaktive Shell zur direkten Evaluierung von ATCLang Befehlen |
| **Programme** | `programs/` | ATC-Systemprogramme (`atcos_main.atc`, `kernel.atc`, `gateway.atc`, `atc8300.atc`, etc.) |

---

## 💻 Usage Example

### 1. ATCLang Programm kompilieren und ausführen
```bash
# REPL starten
python3 repl/repl.py

# Quellcode direkt kompilieren und in ATVM ausführen
python3 compiler.py programs/atcos_main.atc

# Oder die VM direkt mit Opcodes starten
python3 vm.py
```

### 2. Quellcode Beispiel (`example.atc`)
```atc
fn main() {
    let system_id = "ATC-99";
    let status = check_compliance(system_id);
    print("ATCLang System Status:", status);
}
```

---

## 🛠️ Build & Installation

```bash
# Repository klonen
git clone https://github.com/A-TownChain-Okosystems/atclang.git
cd atclang

# Abhängigkeiten installieren
pip install -r requirements.txt

# Tests & Module ausführen
python3 -m unittest discover -s .
```

---

## 🌐 Verwandte Repos & Ökosystem

| Repo | Rolle | Beschreibung |
|------|-------|--------------|
| [a-townchain-os-docs](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs) | `Governance` | Zentrale Spezifikationen & Governance |
| [atc-atclang](https://github.com/A-TownChain-Okosystems/atc-atclang) | `Modules` | Erweiterte Module, TypeChecker & Optimizer |
| [atc-vm](https://github.com/A-TownChain-Okosystems/atc-vm) | `Runtime` | Standalone ATVM Execution Engine |
| [atc-stdlib](https://github.com/A-TownChain-Okosystems/atc-stdlib) | `Library` | Standard-Bibliothek Module |
| [atc-atcpkg](https://github.com/A-TownChain-Okosystems/atc-atcpkg) | `PackageManager` | ATCLang Paketverwaltung |

---

## 📖 Wiki & Dokumentation

Vollständige Sprachspezifikation, Opcode-Referenzen und Beispiele:
👉 **[atclang-wiki Documentation Repository](https://github.com/A-TownChain-Okosystems/atclang-wiki)**

---

## ⚖️ Lizenz

Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. **All Rights Reserved.**
Dieses Projekt nutzt das **ATC-LIC Lizenzmodell**.
