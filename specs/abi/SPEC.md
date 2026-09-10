---
spec_id: ATC-ABI-001
title: "ABI Specification"
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

# ABI Specification (ATC-ABI-001)

> **Ehrlicher Status:** Spezifikations-Grundgerüst (SCR-0071, Owner-Audit-Backlog).
> Implementierung, Tests und Evidence PENDING — gemäß „No status without
> evidence" behauptet diese Datei keinerlei funktionierenden Zustand.

## 1. Zweck

Verbindliche Aufruf- und Typ-Konvention zwischen Bytecode, Host und Contracts.

## 2. Scope (gilt für)

- Calling Convention
- Typ-Encoding (ABI-Primitives)
- Versionierung & Kompatibilität

## 3. Normative Anforderungen (MUST)

- **REQ-ABI-001:** Calling Convention: Argumente/Return über definierte Slots (Stack-Positionen), Frame-Layout fixiert — Compiler (ATC-BC-001) und ATVM implementieren identisch — *Nachweis: unit+vector*
- **REQ-ABI-002:** Typ-Encoding: Kanonische Bytes je ABI-Typ (u8..u256, bool, Address, Bytes-N, Contract-Ref) mit Längenpräfixen; unbekannte Typ-IDs ⇒ Reject — *Nachweis: unit+negative*
- **REQ-ABI-003:** ABI-Version ist im Modul-Header; inkompatible Kombinationen werden hart abgelehnt (COMPAT-001-Kopplung) — *Nachweis: negative*

## 4. Datenmodelle & Schnittstellen

(Datenmodelle werden beim Spec-Freeze finalisiert; diesem Grundgerüst liegen die untenstehenden Anforderungen zugrunde.)

## 5. Invarianten

- Gleiche Signatur ⇒ identisches Encoding über alle Implementierungen

## 6. Conformance-Tests (Mindestkategorien)

- abi_vectors.json
- abi_version_mismatch ⇒ Reject

## 7. Abhängigkeiten & Kompatibilität

Kompatibilität zu ATC-STD-COMPAT-001 (MAJOR-Gate); Änderungen nur via SCR/MINOR (ATC-STD-UPDATE-001).

## 8. Status-Gates (Reihenfolge verbindlich)

- [ ] Spec-Freeze (Owner-Review §9; danach normativ)
- [ ] Implementierung (Rust) mit je-Anforderung-Nachweis
- [ ] Conformance-Suite grün (CI-Evidence: Run-ID + Commit-SHA)
- [ ] Security-Review (threat-bezogen)

## 9. Referenzen

- Owner-Audit 10.09. (P1-4 ABI normative SPEC)
