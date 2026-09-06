# 📚 ATCLang Standard Library (`atc-stdlib`)

> ## 🤖 Fuer KI-Agenten — Pflichtlektuere vor jeder Aenderung
> Governance liegt zentral im Wiki-Repo `a-townchain-os-docs`:
> 1. [`AGENT_POLICY.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/AGENT_POLICY.md) — verbindliche Regeln, Reality-Check, Konsolidierungsziel
> 2. [`AGENT_COORDINATION.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/AGENT_COORDINATION.md) — wer arbeitet gerade woran, Todos, Agent-IDs
> 3. [`DECISIONS_REGISTER.md`](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/blob/main/docs/DECISIONS_REGISTER.md) — verbindliche Architektur-Entscheidungen

**ATCLang Standard Library (`atc-stdlib`)** — Offizielle, plattformübergreifende Standardbibliothek für die ATCLang-Sprache. Enthält standardisierte Module für Primitiven, Mathematik, String-Verarbeitung, Datenstrukturen, Kryptographie, Blockchain, Wallet und I/O.

[![Layer](https://img.shields.io/badge/Layer-L2--L3-purple)](https://github.com/A-TownChain-Okosystems)
[![KAI-OS](https://img.shields.io/badge/KAI--OS-v1.0.0-blue)](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs)
[![Org](https://img.shields.io/badge/Org-A--TownChain--Okosystems-green)](https://github.com/A-TownChain-Okosystems)
[![Wiki](https://img.shields.io/badge/Wiki-📖_atc--stdlib--wiki-blue)](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/tree/main/docs/archive/wiki/atc-stdlib-wiki)

---

## 🏛️ Architektur Diagramm

```
+-----------------------------------------------------------------+
|                       ATCLang Standard Library                  |
+-----------------------------------------------------------------+
    |          |          |          |          |          |
    v          v          v          v          v          v
+-------+  +-------+  +--------+  +--------+  +-------+  +--------+
| Prims |  | Math  |  | String |  | Crypto |  | Chain |  | Wallet |
+-------+  +-------+  +--------+  +--------+  +-------+  +--------+
```

---

## 🧩 Komponenten Tabelle

| Modul | Inhalt / Funktionen | Beschreibung |
|-------|--------------------|--------------|
| `primitives` | Type Casting, Assertions, Basic Conversions | Basis-Typen und grundlegende Konvertierungen |
| `math` | Abs, Pow, Sqrt, Min, Max, Bitwise Ops | Mathematische Hilfsfunktionen und Arithmetik |
| `string` | Concat, Substr, Length, Trim, Split | Zeichenketten-Operationen |
| `collections` | List, Map, Set, Stack, Queue | Hochperformante Datenstrukturen |
| `crypto` | SHA256, Keccak256, Ed25519, Secp256k1 | Kryptographische Hashes & Signaturprüfungen |
| `chain` | GetBlock, GetTx, EventEmit, StateRead/Write | Blockchain & Contract Interaction APIs |
| `wallet` | GetAddress, SignTransaction, VerifySignature | Wallet-Guthaben & Transaktions-Signing |
| `io` | Print, Read, FileIO, NetworkSocket | Input / Output Schnittstellen |

---

## 💻 Usage Example

```atc
use std::crypto;
use std::chain;
use std::wallet;

fn main() {
    let hash = crypto::sha256("ATC-2026");
    let sender = wallet::get_address();
    
    chain::emit_event("TransferInit", sender, hash);
    print("Standard Library Transfer Initialized for:", sender);
}
```

---

## 🛠️ Build & Installation

```bash
git clone https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-stdlib.git
cd atc-stdlib

# Module testen
python3 -m unittest discover
```

---

## 🌐 Verwandte Repos

| Repo | Beschreibung |
|------|--------------|
| [atclang](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atclang) | ATCLang Kern-Sprache |
| [atc-atclang](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-atclang) | Erweiterte ATCLang Toolchain |
| [atc-vm](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-vm) | Virtual Machine Execution Engine |
| [atc-atcpkg](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-atcpkg) | Package Manager für ATCLang Module |

---

## 📖 Wiki Link

Vollständige Modulreferenz und API-Dokumentation:
👉 **[atc-stdlib-wiki Repository](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs/tree/main/docs/archive/wiki/atc-stdlib-wiki)**


## Abhängigkeiten
- [`A-TownChain-Okosystems/atc-shivacore`](https://github.com/A-TownChain-Okosystems/a-townchain-os/tree/main/src/modules/atc-shivacore)

---

## ⚖️ Lizenz

Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. **All Rights Reserved.**
ATC-LIC Lizenzmodell.
