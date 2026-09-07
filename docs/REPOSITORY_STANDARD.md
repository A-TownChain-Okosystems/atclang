# Repository Standard — atclang

**Klassifizierung:** CORE · **Maturity:** R4 · **Layer:** L0 · **Domain:** language

Dieses Repository folgt den ATC-Repository-Standards (kanonisch im
[atc-standards](https://github.com/A-TownChain-Okosystems/atc-standards)):

- **ATC-STD-201** Repository Structure (Metadaten, Struktur, Compliance-Matrix)
- **ATC-STD-202** Repository Naming & Classification (R0-R4, S0-S4, Namensregeln ATC-STD-000 §7)
- **ATC-STD-203** Repository Security & Release (Branching, Conventional Commits, Release-Gates)

## Zwei-Ebenen-Entscheidungsmodell (AD-029)

1. **Zentral:** docs/DECISIONS_REGISTER.md im Docs-Hub — AD-Nummern sind
   verbindlich und haben Vorrang (ATC-STD-000 §31: hoechste Governance-Prioritaet).
2. **Lokal:** repo-spezifische Entscheidungen in docs/decisions/ (ADR-NNN-Form,
   ATC-STD-000 §7.2; zentrales Register behaelt die grandfathered AD-NNN-Form).

## Struktur

```
atclang/
├── .atc/            Metadaten (repository/ownership/lifecycle/compliance.yaml)
├── .github/         CI (governance-ci.yml; Produkt-Pipelines je Meilenstein)
├── docs/            REPOSITORY_STANDARD.md, decisions/
├── tests/           Testplan bis zur Meilenstein-Umsetzung (M6/M7)
├── modules|src|specs|docs/  je Repo-Typ (CORE)
├── README.md        mit ATC-COMPLIANCE-Anhang
├── SECURITY.md · CHANGELOG.md · CODEOWNERS · LICENSE
```

## Regeln

- Conventional Commits (feat/fix/docs/security/chore...)
- Aenderungen an Produkt-Modulen via PR; Sync-Punkte via scripts/sync_modules.py (AD-017)
- Kein POSIX-Cloning; from-scratch-Oekosystem (AD-005-Reihe)
- Naming: IDs gemaess ATC-STD-000 §7 (maschinenpruefbar, min. 3-stellig, immutable)
