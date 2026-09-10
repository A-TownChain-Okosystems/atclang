---
spec_id: ATC-BC-001
title: "Bytecode Specification"
version: 0.1.0-DRAFT
status: SPEC-DRAFT — normativ erst nach Spec-Freeze; Implementierung PENDING
repository: atclang
layer: L0-Language
owner: A-TownChain-Okosystems
copyright: Michael Wroblewski
license: Apache-2.0
created: 2026-09-10
scr: SCR-0071
depends: []
---

# Bytecode Specification (ATC-BC-001)

> **Ehrlicher Status:** Spezifikations-Grundgerüst (SCR-0071, Owner-Audit-Backlog).
> Implementierung, Tests und Evidence PENDING — gemäß „No status without
> evidence" behauptet diese Datei keinerlei funktionierenden Zustand.

## 1. Zweck

Das verbindliche ATVM-Bytecode-Format (für ATCLang und unabhängige Compiler).

## 2. Scope (gilt für)

- Datei-/Modul-Layout (Magic, Version, Sections)
- Opcode-Katalog & Semantik
- Determinismus des Compilers

## 3. Normative Anforderungen (MUST)

- **REQ-BC-001:** Modul-Layout: Magic „ATC1“ + version(u16) + Sections (Header, Konstanten, Code, Typen, Debug optional, Checksum) — unbekannte Sections ⇒ Reject (kein permissives Parsen) — *Nachweis: unit+negative*
- **REQ-BC-002:** Opcode-Katalog ist versioniert und im Registry-JSON maschinenlesbar (Opcode, Operanden-Encodings, Stapelwirkung) — Quelle für ATVM (ATC-VM-001) und Disassembler — *Nachweis: unit+vector*
- **REQ-BC-003:** Determinismus-Pflicht: same source + same compiler_version + same target ⇒ bit-identischer Bytecode (bytecode_hash stabil) — testbar über ATCLANG-DETERMINISM-Suite — *Nachweis: property+vector*

## 4. Datenmodelle & Schnittstellen

(Datenmodelle werden beim Spec-Freeze finalisiert; diesem Grundgerüst liegen die untenstehenden Anforderungen zugrunde.)

## 5. Invarianten

- Checksum über Bytecode-Datei ist Teil des Moduls; Divergenz ⇒ ungültig

## 6. Conformance-Tests (Mindestkategorien)

- bytecode_vectors.json
- unknown_opcode ⇒ Reject
- deterministic_compile.json (Hash-Stabilität)

## 7. Abhängigkeiten & Kompatibilität

Kompatibilität zu ATC-STD-COMPAT-001 (MAJOR-Gate); Änderungen nur via SCR/MINOR (ATC-STD-UPDATE-001).

## 8. Status-Gates (Reihenfolge verbindlich)

- [ ] Spec-Freeze (Owner-Review §9; danach normativ)
- [ ] Implementierung (Rust) mit je-Anforderung-Nachweis
- [ ] Conformance-Suite grün (CI-Evidence: Run-ID + Commit-SHA)
- [ ] Security-Review (threat-bezogen)

## 9. Referenzen

- Owner-Audit 10.09. (P1-2 Bytecode normative SPEC, P2-9 ATCLANG-DETERMINISM-001)
