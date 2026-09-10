---
spec_id: ATC-VM-001
title: "ATVM Specification"
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

# ATVM Specification (ATC-VM-001)

> **Ehrlicher Status:** Spezifikations-Grundgerüst (SCR-0071, Owner-Audit-Backlog).
> Implementierung, Tests und Evidence PENDING — gemäß „No status without
> evidence" behauptet diese Datei keinerlei funktionierenden Zustand.

## 1. Zweck

Semantik der ATVM-Ausführung (Normativ-Grundlage für atc-vm; eine Implementierung allein ist nicht Spec und Orakel zugleich).

## 2. Scope (gilt für)

- Ausführungsmodell (Stack, Frames, Call-Conv.)
- Gas-/Ressourcen-Modell
- Determinismus & Fehlerbehandlung

## 3. Normative Anforderungen (MUST)

- **REQ-VM-001:** Ausführung ist deterministisch: same bytecode + same state + same vm_version ⇒ same effects/state (plattformunabhängig, kein Float, checked Integer) — *Nachweis: property+differential*
- **REQ-VM-002:** Gas-Modell: je Opcode dokumentierte Kosten (Registry-JSON); Ressourcen-Erschöpfung ⇒ deterministischer Abbruch mit Fehlercode (kein halber Effekt) — *Nachweis: unit+negative*
- **REQ-VM-003:** Fehlerklassen sind katalogisiert (stack underflow, invalid jump, type mismatch, out-of-gas, memory limit) — je mit eindeutigem Code — *Nachweis: unit+negative*
- **REQ-VM-004:** Verifikations-Pflicht: ATVM wird gegen Bytecode-Vektoren von Dritten getestet (Conformance-Suite, ATC-STD-PROTOCOL-002-Analog) — *Nachweis: integration*

## 4. Datenmodelle & Schnittstellen

(Datenmodelle werden beim Spec-Freeze finalisiert; diesem Grundgerüst liegen die untenstehenden Anforderungen zugrunde.)

## 5. Invarianten

- VM-State-Übergänge sind total geordnet deterministisch

## 6. Conformance-Tests (Mindestkategorien)

- vm_conformance.json
- vm_error_matrix.json
- cross_vm_differential.json (Rust vs. Referenz-Oracle)

## 7. Abhängigkeiten & Kompatibilität

Kompatibilität zu ATC-STD-COMPAT-001 (MAJOR-Gate); Änderungen nur via SCR/MINOR (ATC-STD-UPDATE-001).

## 8. Status-Gates (Reihenfolge verbindlich)

- [ ] Spec-Freeze (Owner-Review §9; danach normativ)
- [ ] Implementierung (Rust) mit je-Anforderung-Nachweis
- [ ] Conformance-Suite grün (CI-Evidence: Run-ID + Commit-SHA)
- [ ] Security-Review (threat-bezogen)

## 9. Referenzen

- Owner-Audit 10.09. (P1-3 ATVM normative SPEC; „eine VM darf nicht Spec und Orakel sein«)
