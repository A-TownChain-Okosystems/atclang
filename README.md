# ATCLang — Proprietäre Programmiersprache

> **Produkt-Repo des A-TownChain-Ökosystems** · [Monorepo](https://github.com/A-TownChain-Okosystems/a-townchain-os) · [Docs-Hub](https://github.com/A-TownChain-Okosystems/a-townchain-os-docs) · Mainnet: **15.09.2026**

ATCLang (v0.1.0-alpha) ist die vollständig eigenentwickelte Sprache des A-TownChain-Ökosystems: Lexer, rekursiver Parser, Compiler und Stack-basierte VM mit proprietärem Namespace-Schema (ATC::Wallet::new). Kern-Systemlogik läuft in .atc-Dateien.

## Module (aus Monorepo `src/modules/` überführt)

| Modul | Dateien | Zeilen |
|---|---|---|
| `atclang` | 46 | 21,604 |
| `atc-atclang` | 38 | 8,037 |
| `atc-vm` | 19 | 713 |
| `atc-stdlib` | 35 | 1,993 |
| **Total** | **138** | **32,347** |

## Richtlinien

- Architektur-Vorgaben: AD-012/AD-013 (ShivaCore Microkernel, Gate v1.1) — siehe Docs-Hub `docs/architecture/`
- Neue Produkt-Entwicklung läuft hier; Integration & Deployment über das Monorepo
- Standards: ATC-01…35 · ATS-1000…1007 · Lizenz: All Rights Reserved (Michael Wroblewski / ShivaCore / A-TownChain-Okosystems)

*Eingerichtet am 06.09.2026 durch Agent Aurora (Base44) im Auftrag des Owners.*
