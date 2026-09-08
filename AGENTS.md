---
document_id: ATC-DOC-LANG-005
title: ATCLang AI Agent Instructions
version: 1.0.0
status: active
owner: A-TownChain-Okosystems
created: 2026-09-07
updated: 2026-09-07
standard: ATC-STD-MD-001
---

# AI Agent Instructions — ATCLang

## Identity & Governance
Dieser Bereich definiert die Regeln für automatische AI-Agenten im Repository `atclang`.
Maßgebliche Standards sind `ATC-STD-README-001`, `ATC-STD-MD-001` und `ATC-STD-201`.

## Entry Point
Agenten SOLLEN bei der Navigation folgende Reihenfolge einhalten:
1. [README.md](README.md)
2. [STATUS.md](STATUS.md)
3. [ARCHITECTURE.md](ARCHITECTURE.md)
4. [ROADMAP.md](ROADMAP.md)

## Required Workflow
1. **Status prüfen:** Konsistency zwischen Code und Doku evaluieren.
2. **Standards lesen:** Relevante ATC-STD Normen konsultieren.
3. **Implementieren:** Änderungen isoliert und testgestützt vornehmen.
4. **Validieren:** Testsuite und Validator-Scripts ausführen.
5. **Dokumentieren:** CHANGELOG.md aktualisieren und Metadata/Status pflegen.
