---
spec_id: ATC-IR-001
title: "ATC-IR Specification (Intermediate Representation)"
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

# ATC-IR Specification (Intermediate Representation) (ATC-IR-001)

> **Ehrlicher Status:** Spezifikations-Grundgerüst (SCR-0071, Owner-Audit-Backlog).
> Implementierung, Tests und Evidence PENDING — gemäß „No status without
> evidence" behauptet diese Datei keinerlei funktionierenden Zustand.

## 1. Zweck

Normatives Typed-IR zwischen Semantic Gate G2 und Codegen — Kompilierungs-Determinismus und Sprache-Governance.

## 2. Scope (gilt für)

- IR-Node-Katalog
- Typisierung & Coercions
- Serialisierung (kanonisch)

## 3. Normative Anforderungen (MUST)

- **REQ-IR-001:** IR ist ein versioniertes, typisiertes Node-Set (Deklarationen, Ausdrücke, Kontrollfluss, Contract-/Host-Grenzen); jede Node-Art ist im Registry-JSON katalogisiert — *Nachweis: unit+vector*
- **REQ-IR-002:** IR-Serialisierung ist kanonisch (feldfixiert, Little-Endian, keine Anker) — Grundlage für deterministischen Codegen (ATC-BC-001) — *Nachweis: unit+property*
- **REQ-IR-003:** IR ist vollständig typisiert (G2-Output); untypisierte IR ist ungültig (G2-Gate bleibt hart) — *Nachweis: negative*

## 4. Datenmodelle & Schnittstellen

(Datenmodelle werden beim Spec-Freeze finalisiert; diesem Grundgerüst liegen die untenstehenden Anforderungen zugrunde.)

## 5. Invarianten

- Identischer AST + identische Semantik-Version ⇒ identisches IR

## 6. Conformance-Tests (Mindestkategorien)

- ir_roundtrip.json
- ir_determinism.json
- untyped_ir ⇒ Reject

## 7. Abhängigkeiten & Kompatibilität

Kompatibilität zu ATC-STD-COMPAT-001 (MAJOR-Gate); Änderungen nur via SCR/MINOR (ATC-STD-UPDATE-001).

## 8. Status-Gates (Reihenfolge verbindlich)

- [ ] Spec-Freeze (Owner-Review §9; danach normativ)
- [ ] Implementierung (Rust) mit je-Anforderung-Nachweis
- [ ] Conformance-Suite grün (CI-Evidence: Run-ID + Commit-SHA)
- [ ] Security-Review (threat-bezogen)

## 9. Referenzen

- Owner-Audit 10.09. (P1-1: ATC-IR normative SPEC)
- specs/language/SPEC.md, specs/semantics/SPEC.md (bestehend)
