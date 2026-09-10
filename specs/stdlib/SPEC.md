---
spec_id: ATC-STDLIB-001
title: "Standard Library Specification & Trust-Klassifikation"
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

# Standard Library Specification & Trust-Klassifikation (ATC-STDLIB-001)

> **Ehrlicher Status:** Spezifikations-Grundgerüst (SCR-0071, Owner-Audit-Backlog).
> Implementierung, Tests und Evidence PENDING — gemäß „No status without
> evidence" behauptet diese Datei keinerlei funktionierenden Zustand.

## 1. Zweck

Normatives Verzeichnis der 9 Stdlib-Module mit Trust-Klassen — wallet/io/chain sind keine normalen Libraries.

## 2. Scope (gilt für)

- Modul-Katalog (chain, crypto, math, primitives, wallet, io, encoding, collections, string)
- Trust-Klassen je Modul/Funktion
- Determinismus-Regeln

## 3. Normative Anforderungen (MUST)

- **REQ-SL-001:** Jede Stdlib-Funktion hat eine Trust-Klasse: PURE (deterministisch, kein Host-Zugriff) | DETERMINISTIC | STATEFUL | HOST_BOUND | PRIVILEGED | KERNEL_BOUND — katalogisiert im Registry-JSON — *Nachweis: unit+governance*
- **REQ-SL-002:** wallet/io/chain sind PRIVILEGED/HOST_BOUND: Host-Calls laufen ausschließlich über deklarierte, geprügte Schnittstellen (Capability-Modell, keine freie Host-Nutzung) — *Nachweis: architecture+negative*
- **REQ-SL-003:** PURE/DETERMINISTIC-Funktionen sind implizit Conformance-geprüft (Vektoren je Funktion bei Spec-Freeze) — *Nachweis: vector*

## 4. Datenmodelle & Schnittstellen

(Datenmodelle werden beim Spec-Freeze finalisiert; diesem Grundgerüst liegen die untenstehenden Anforderungen zugrunde.)

## 5. Invarianten

- Keine nicht klassifizierte Funktion ist im Stdlib-Export sichtbar

## 6. Conformance-Tests (Mindestkategorien)

- stdlib_registry_completeness.json
- pure_determinism.json
- privileged_call_unauthorized ⇒ Reject

## 7. Abhängigkeiten & Kompatibilität

Kompatibilität zu ATC-STD-COMPAT-001 (MAJOR-Gate); Änderungen nur via SCR/MINOR (ATC-STD-UPDATE-001).

## 8. Status-Gates (Reihenfolge verbindlich)

- [ ] Spec-Freeze (Owner-Review §9; danach normativ)
- [ ] Implementierung (Rust) mit je-Anforderung-Nachweis
- [ ] Conformance-Suite grün (CI-Evidence: Run-ID + Commit-SHA)
- [ ] Security-Review (threat-bezogen)

## 9. Referenzen

- Owner-Audit 10.09. (P2-10: Trust-Klassifikation wallet/io/chain)
