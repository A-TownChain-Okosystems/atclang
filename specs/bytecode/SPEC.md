---
spec_id: ATC-BC-001
title: "Bytecode Specification (ATCB v1 - Canonical Encoding)"
version: 1.0.0
status: SPEC-FROZEN - normativ seit 2026-10-06 (erster kanonischer Normstand)
repository: atclang
layer: L0-Language
owner: A-TownChain-Okosystems
license: Apache-2.0
created: 2026-09-10
frozen: 2026-10-06
scr: SCR-0071
depends: [ATC-STD-000]
supersedes: 0.1.0-DRAFT (Geometrie-Konflikt mit ATCB-1.md aufgeloest)
---

# Bytecode Specification (ATC-BC-001) - ATCB v1

> **Normativitaet:** Diese Spezifikation ist der normative Traeger von ATCB v1
> (ATC-STD-000 §21). Referenzimplementierungen sind
> `crates/atc-core/src/bytecode.rs::encode_canonical()` (Enkodierung) und
> `crates/atc-core/src/artifact.rs::decode_bytecode()` (Dekodierung).
> Aenderungen an dieser Datei sind Normaenderungen (SCR/MINOR,
> ATC-STD-UPDATE-001); Abweichungen der Referenzimplementierung sind Fehler.

## 0. Freeze-Block

| Feld | Wert |
|---|---|
| Formatversion | ATCB v1 (`format_version` u16 BE = 1) |
| Dokumentversion | 1.0.0-FROZEN |
| Freeze-Datum | 2026-10-06 |
| Gueltigkeitsbereich | Kanonische Bytecode-Enkodierung und strukturelle Container-Dekodierung (G3) |
| Nicht im Scope | Integritaet/Checksum (liegt in der ATCA-Artefakt-Schicht: SHA-256 ueber kanonisches Payload); Verifikation jenseits der Struktur-Regeln |
| Freeze-Anker | SHA dieses Freeze-Commits (post-push dokumentiert) |

## 1. Zweck

Das verbindliche ATVM-Bytecode-Format: kanonische Serialisierung des
ATC-IR-Codegen-Outputs, Eingabe fuer strukturelle Verifikation und
ATCA-Artefakt-Bindung.

## 2. Container-Geometrie (normativ)

| Feld | Groesse | Kodierung |
|---|---:|---|
| Magic | 4 | ASCII `ATCB` |
| Format-Version | 2 | u16 big-endian, derzeit `1` |
| Instruction-Count | 4 | u32 big-endian |
| Instructions | variabel | opcode-spezifisch, big-endian |

- **Endianness:** ALLE Multi-Byte-Ganzzahlen (Container-Felder UND Operanden) sind big-endian.
- **KEINE Checksum im Container.** Integritaet liegt in der ATCA-Artefakt-Schicht (SHA-256 ueber das kanonische Payload, siehe `crates/atc-core/src/artifact.rs`).
- Der Container ist flach; kein Section-Layout.
- Keine Host-Metadaten: keine Endianness-Marker, Pointer-Werte, Hash-Map-Iterierordnung oder Plattformdaten in der Enkodierung.

## 3. Opcode-Katalog (normativ, 19 Opcodes)

| Opcode | Instruction | Operand (big-endian) |
|---:|---|---|
| `0x01` | ConstI64 | i64 |
| `0x02` | LoadLocal | u16 |
| `0x03` | StoreLocal | u16 |
| `0x10` | Add | - |
| `0x11` | Sub | - |
| `0x12` | Mul | - |
| `0x13` | Div | - |
| `0x14` | Neg | - |
| `0x15` | Eq | - |
| `0x16` | Ne | - |
| `0x17` | Lt | - |
| `0x18` | Gt | - |
| `0x19` | Le | - |
| `0x1A` | Ge | - |
| `0x20` | Call | function:u16, argc:u16 |
| `0x21` | Return | - |
| `0x30` | Jump | i16 |
| `0x31` | JumpIfFalse | i16 |
| `0x40` | Pop | - |

## 4. Dekodier-Regeln (normativ, MUST-Reject, fail-closed)

Ein ATCB-v1-Stream ist UNGUELTIG, wenn:

- **REQ-BC-F1 Magic-Mismatch:** Die ersten 4 Bytes sind nicht `ATCB`.
- **REQ-BC-F2 Version-Rejection:** `format_version` != 1.
- **REQ-BC-F3 Count-Ueberlauf:** instruction_count > Anzahl verbleibender Bytes (jede Instruction benoetigt mindestens 1 Opcode-Byte; keine Allokation aus attacker-kontrolliertem Count).
- **REQ-BC-F4 Unknown Opcode:** Opcode ausserhalb des Katalogs.
- **REQ-BC-F5 Truncation:** Opcode oder Operand abgeschnitten.
- **REQ-BC-F6 Trailing Bytes:** Nach der letzten Instruction bleiben Bytes uebrig.

Alles nicht explizit Erlaubte ist ungueltig; kein permissives Parsen.

## 5. Strukturelle Verifikation (G3-Baseline)

Zusaetzlich zur Container-Gueltigkeit verwirft die strukturelle Verifikation
u. a. leere Bytecode-Funktionen, Stack-Underflow, unzulaessige Locals und
Function-Indizes, ungueltige Sprungziele, fehlendes oder inkonsistentes
Return sowie Division durch Konstante Null. Vollstaendige Liste: Referenz
`crates/atc-core/src/bytecode.rs::verify()` - Implementierungs-Baseline,
nicht Teil der Container-Norm dieses Abschnitts.

## 6. Nicht-kanonische Serialisierung

`Bytecode::encode()` (Little-Endian) ist LEGACY / NON-CANONICAL und darf
nicht als kanonische Serialisierung referenziert werden (im Code per
Dokumentationskommentar markiert). Entfernung ist NICHT Teil dieses Freezes:
Die Entscheidung ueber die Nichtnutzung faellt in Gate 0 (Folgecommit).

## 7. BE-Bindungsnachweis (Ableitung, keine Setzung)

Grund der BE-Entscheidung, verifiziert auf Commit-Ebene (06.10.2026):
`encode_canonical()` ist seit Geburt big-endian (Commit 06b36367); der
Canonical-Vektor wurde als BE gelockt (Commit 3c73d7ba, byte-identisch zum
heutigen Stand); `artifact.rs` hasht seit Geburt (Commit 75f56f82) SHA-256
ueber `encode_canonical()`; ein LE-Hash-Pfad hat nie existiert (Commit
8b7bffff fuegte nur die sha2-Dependency hinzu). Materialisierte Identitaeten
sind Repo-/CI-intern.

## 8. Cross-Reference (Bindungswirkung)

ATCB v1 bindet: **ATCLang** (Codegen erzeugt ausschliesslich ATCB v1),
**ATC-VM/ATVM** (verifiziert und fuehrt ausschliesslich ATCB v1, geliefert
ueber ATCA-Artefakte), **atc-toolchain** (Verifikations-Adapter konsumieren
ATCB v1). Dieser Freeze ist eine Normaenderung mit Wirkung auf diese drei
Komponenten, keine reine ATCB-Modifikation.

### 8.1 SSOT-Trägerschaft (Setzung, Owner-Wahl 2026-10-06)

ATCB v1 wird normativ von atclang getragen. Diese Zuweisung ist eine
**gewählte Setzung, keine Ableitung**: Bytecode ist ein Laufzeitformat —
die Sprache produziert es, die VM konsumiert es; „Sprachformat" wäre keine
kategorische Begründung. Tragendes Argument ist pragmatisch: **wo die
Referenzimplementierung liegt, liegt die Norm** — `encode_canonical()` /
`decode_bytecode()` und die Determinism-/Differential-Suiten leben in
atclang; der Freeze-Anker ee26531338787667ae417333b4900b302eb36353 liegt
hier und wandert nicht.

Entscheidungsträger außerhalb dieses Commits (die Antwort auf „warum
ATCB in atclang?" ist nie „weil ee265313 das sagt"):

1. **SCR-0129** (atc-standards/change-requests/, PENDING Owner-Approve) —
   trägt die Setzung samt Begründung.
2. **Registry-Bindung `bytecode_format: atclang`** — maschinenlesbare
   SSOT-Zuweisung, folgt der SCR-0129-Freigabe (Umsetzungsequenz:
   Registry → Standard → Validator/CI); zwischenzeitlich zurückgezogen
   (06.10., Owner-Anordnung: keine vorgezogene normative
   Registry-Änderung).
3. **Registry-Pointer** (atc-standards/references/standards/ATCB-v1-POINTER.md).

Durchsetzung: RV-001 im Revalidierungs-Regelkatalog
(atc-standards/references/revalidation/REVALIDATION_RULES.md) — normative
ATCB-Geometrie außerhalb dieses SSOT-Pfads ist VIOLATION; klassifizierte
ARCHIVE/MIRROR-Kopien zulässig. Trägerschafts-Wechsel bleibt SCR-pflichtig
(ATC-STD-UPDATE-001).

## 9. Statustrennung

Dieser Freeze erzeugt ATCB v1 als kanonische Norm mit eigenem Commit-SHA.
`abe17cc5bc37a3c1d52ea9941f2d3e63d259208d` (atc-toolchain,
`anchor/compiler-baseline`) bleibt PRESERVATION-ANKER
(EXISTENT / DANGLING / NOT VERIFIED) - keine kanonische Baseline, auch nach
diesem Freeze nicht.

## 10. Referenzen

- ATC-STD-000 (Standard-Governance), ATC-STD-UPDATE-001 (Aenderungsprozess)
- specs/ir/SPEC.md (ATC-IR-001, DRAFT - Eingabe des Codegen)
- crates/atc-core/src/bytecode.rs, crates/atc-core/src/artifact.rs (Referenzimplementierungen)
- SCR-0071 (Owner-Audit-Backlog), specs/language/SPEC.md (G1-PASSED)
