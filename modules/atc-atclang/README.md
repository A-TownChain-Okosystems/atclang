# 📦 ATCLang Modular System & Extensions

> ## 🤖 Fuer KI-Agenten — Pflichtlektuere vor jeder Aenderung
> Governance liegt zentral im Wiki-Repo `a-townchain-os-docs`:
> 1. [`AGENT_POLICY.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/AGENT_POLICY.md) — verbindliche Regeln, Reality-Check, Konsolidierungsziel
> 2. [`AGENT_COORDINATION.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/AGENT_COORDINATION.md) — wer arbeitet gerade woran, Todos, Agent-IDs
> 3. [`DECISIONS_REGISTER.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/DECISIONS_REGISTER.md) — verbindliche Architektur-Entscheidungen

**ATCLang Modular Extensions (`atc-atclang`)** — Modulare Erweiterungen für die ATCLang Toolchain. Enthält den erweiterten Parser, Compiler mit AST-Optimizer, statischen TypeChecker, v0.3.0 Sprach-Features, erweiterte Standardbibliothek (`crypto`, `chain`, `wallet`, `encoding`, `collections`, `io`) sowie REPL und VM.

[![Layer](https://img.shields.io/badge/Layer-L2--L4-purple)](https://github.com/A-TownChain-Okosystems)
[![KAI-OS](https://img.shields.io/badge/KAI--OS-v1.0.0-blue)](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs)
[![Org](https://img.shields.io/badge/Org-A--TownChain--Okosystems-green)](https://github.com/A-TownChain-Okosystems)
[![Wiki](https://img.shields.io/badge/Wiki-📖_atc--atclang--wiki-blue)](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/tree/main/docs/archive/wiki/atc-atclang-wiki)

---

## 🏛️ Architektur Diagramm

```
+-------------------------------------------------------------------------+
|                           ATCLang Extensions                            |
+-------------------------------------------------------------------------+
       |                  |                    |                  |
       v                  v                    v                  v
+--------------+  +---------------+  +------------------+  +--------------+
| Lexer/Parser |  | Compiler Stack|  | Standard Library |  | ATVM Runtime |
| (ast_nodes)  |  | - TypeChecker |  | - primitives,math|  | - Execution  |
| (parser.py)  |  | - Optimizer   |  | - crypto, chain  |  | - Bytecode   |
|              |  | - v03 Features|  | - wallet, io     |  | - Sandbox    |
+--------------+  +---------------+  +------------------+  +--------------+
```

---

## 🧩 Komponenten Tabelle

| Modul | Verzeichnis | Beschreibung |
|-------|-------------|--------------|
| **Compiler Engine** | `compiler/` | `compiler.py` (AST to Bytecode), `optimizer.py` (AST Transformations & Constant Folding), `type_checker.py` (Statische Typenprüfung) |
| **Lexer Engine** | `lexer/` | Tokenisierung, ATCLang Keywords, Multi-Line Support, Error Recovery |
| **Parser Engine** | `parser/` | Rekursiver Parser, AST-Node Definitionen (`ast_nodes.py`), Sprach-Grammatik |
| **v0.3.0 Features** | `v03/` | Sprach-Features Version 0.3.0 (`atclang_v03_features.py`) |
| **VM Runtime** | `vm/` | Execution Engine (`atcvm.py`), Memory Management, Opcode Handler |
| **Extended Stdlib** | `stdlib/` | Reiche Standardbibliothek: `crypto`, `chain`, `wallet`, `encoding`, `math`, `collections`, `io`, `primitives`, `string` |
| **REPL Shell** | `repl/` | Interaktive Konsole (`repl.py`) |
| **System-Code** | `programs/` | Referenz-Programme wie `atcos_main.atc` |

---

## 💻 Usage Example

```python
from compiler.compiler import Compiler
from compiler.type_checker import TypeChecker
from compiler.optimizer import ASTOptimizer
from lexer.lexer import Lexer
from parser.parser import Parser
from vm.atcvm import ATVM

code = '''
fn main() {
    let x = 10 + 20;
    print("Calculated:", x);
}
'''

# 1. Lexing & Parsing
lexer = Lexer(code)
tokens = lexer.tokenize()
parser = Parser(tokens)
ast = parser.parse()

# 2. Type Checking & Optimization
tc = TypeChecker()
tc.check(ast)
opt = ASTOptimizer()
opt_ast = opt.optimize(ast)

# 3. Compilation & Execution
compiler = Compiler()
bytecode = compiler.compile(opt_ast)
vm = ATVM()
vm.execute(bytecode)
```

---

## 🛠️ Build & Setup

```bash
git clone https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-atclang.git
cd atc-atclang

# Virtual Environment erstellen und Abhängigkeiten installieren
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# REPL starten
python3 -m repl.repl
```

---

## 🌐 Verwandte Repos

| Repo | Beschreibung |
|------|--------------|
| [atclang](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atclang) | ATCLang Kern-Compiler & Referenz-Implementierung |
| [atc-vm](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-vm) | Dedicated Execution Engine |
| [atc-stdlib](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-stdlib) | Standard-Bibliotheks-Paket |
| [atc-atcpkg](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-atcpkg) | Package Manager |

---

## 📖 Wiki Link

Ausführliche Dokumentation der Sprachkomponenten & APIs:
👉 **[atc-atclang-wiki Repository](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/tree/main/docs/archive/wiki/atc-atclang-wiki)**

---

## ⚖️ Lizenz

Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. **All Rights Reserved.**
ATC-LIC Lizenzmodell.
