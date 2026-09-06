# ⚙️ ATCLang Virtual Machine (ATVM)

> ## 🤖 Fuer KI-Agenten — Pflichtlektuere vor jeder Aenderung
> Governance liegt zentral im Wiki-Repo `a-townchain-os-docs`:
> 1. [`AGENT_POLICY.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/AGENT_POLICY.md) — verbindliche Regeln, Reality-Check, Konsolidierungsziel
> 2. [`AGENT_COORDINATION.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/AGENT_COORDINATION.md) — wer arbeitet gerade woran, Todos, Agent-IDs
> 3. [`DECISIONS_REGISTER.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/DECISIONS_REGISTER.md) — verbindliche Architektur-Entscheidungen

**ATVM (`atc-vm`)** — Virtual Machine Runtime Engine für das A-TownChain Ökosystem. Bietet eine deterministische, stack-basierte Ausführungsumgebung für ATCLang Bytecode mit integriertem Metering, Call-Stack Management, Memory-Heap, System-Calls und ATC-99 Policy Enforcement.

[![Layer](https://img.shields.io/badge/Layer-L2-purple)](https://github.com/A-TownChain-Okosystems)
[![KAI-OS](https://img.shields.io/badge/KAI--OS-v1.0.0-blue)](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs)
[![Org](https://img.shields.io/badge/Org-A--TownChain--Okosystems-green)](https://github.com/A-TownChain-Okosystems)
[![Wiki](https://img.shields.io/badge/Wiki-📖_atc--vm--wiki-blue)](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/tree/main/docs/archive/wiki/atc-vm-wiki)

---

## 🏛️ Architektur Diagramm

```
+---------------------------------------------------------------+
|                       ATVM Execution Engine                   |
+---------------------------------------------------------------+
|  +---------------------+             +---------------------+  |
|  |     Operand Stack   |             |   Call Frames / IP  |  |
|  +---------------------+             +---------------------+  |
|  |  Heap & Registries  |             | Gas & Metering      |  |
|  +---------------------+             +---------------------+  |
+---------------------------------------------------------------+
                               |
                               v
+---------------------------------------------------------------+
|                   Opcode Dispatcher Engine                    |
|  [PUSH, POP, ADD, SUB, CALL, RET, SYS_CALL, ATC99_CHECK, ...] |
+---------------------------------------------------------------+
```

---

## 🧩 Komponenten Tabelle

| Komponente | Modul / Bereich | Beschreibung |
|------------|-----------------|--------------|
| **Execution Loop** | `atcvm.py` / `core` | Hauptausführungsschleife für Bytecode-Opcodes |
| **Operand Stack** | `stack` | Stack-basierte Datenverarbeitung mit Push/Pop/Dup Operations |
| **Call Stack & Frames** | `frames` | Verwaltung lokaler Variablen, Argumente und Rücksprungadressen |
| **Gas & Metering** | `gas` | Ressourcen-Limitierung & Execution-Cost-Checking |
| **System Calls & Crypto** | `syscalls` | Schnittstellen zu Kernel, Chain, Crypto & State |
| **ATC-99 Enforcement** | `policy` | Verifikation von Vertragslizenzen vor Ausführung |

---

## 💻 Usage Example

```python
# Beispiel: Direkte Bytecode Ausführung in der ATVM
from atc_vm import ATVM

vm = ATVM(gas_limit=1_000_000)

# Bytecode: PUSH 10, PUSH 20, ADD, HALT
bytecode = bytes([0x01, 10, 0x01, 20, 0x05, 0x00])

result = vm.execute(bytecode)
print("ATVM Execution Result:", result)
```

---

## 🛠️ Build & Running

```bash
git clone https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-vm.git
cd atc-vm

# Testsuite ausführen
python3 -m unittest discover
```

---

## 🌐 Verwandte Repos

| Repo | Beschreibung |
|------|--------------|
| [atclang](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atclang) | ATCLang Compiler & Syntaktische Werkzeuge |
| [atc-atclang](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-atclang) | Erweitertes Modulset für ATCLang |
| [atc-stdlib](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-stdlib) | Standard-Bibliothek für ATVM |
| [a-townchain-os-docs](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs) | Zentrale Dokumentation & Governance |

---

## 📖 Wiki Link

Opcode-Tabellen, Spezifikation und Ausführungsmodelle:
👉 **[atc-vm-wiki Repository](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/tree/main/docs/archive/wiki/atc-vm-wiki)**


## Abhängigkeiten
- [`A-TownChain-Okosystems/atc-shivacore`](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-shivacore)

---

## ⚖️ Lizenz

Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. **All Rights Reserved.**
ATC-LIC Lizenzmodell.
