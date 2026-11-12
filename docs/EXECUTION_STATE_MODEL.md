# Execution State Model

Repository: `atclang`  
Rule introduced: 2026-11-12 (Owner audit, E1)  
State: active, not yet bound in `specs/semantics/registry.json`

## Rule

**Compiler Success ≠ Executable Contract.**

Ein erfolgreicher Syntax- oder Typcheck ist kein Nachweis fuer einen
ausfuehrbaren Vertrag. Kein Status darf ohne den zugehoerigen Nachweis
behauptet werden, und kein spaeterer Status darf einen frueheren stillschweigend
voraussetzen.

Diese Regel ist verbindlich fuer Compiler, CLI, Deployment und Dokumentation.
Sie ist als Projektregel in Kraft und noch nicht in die Standard-Registry
(`specs/semantics/registry.json`) eingetragen; die Registry-Aufnahme ist ein
eigener Schritt und darf nicht als erledigt dargestellt werden.

## States

| State | Bedeutung | Nachweis | Stand 12.11.2026 |
|---|---|---|---|
| `PARSED` | Quelle ist syntaktisch wohlgeformt | Parser liefert AST | erreicht fuer den Parser-Subset, Beispiele ausser `kernel.atc` |
| `TYPE_CHECKED` | Typen sind geprueft | Typcheck ohne Befund | nicht implementiert (Rust-Kern hat keinen Typchecker) |
| `SEMANTICALLY_VALIDATED` | Semantik-Regeln SEM-001..012 erfuellt | Semantik-Lauf ohne Befund | nicht implementiert im Rust-Kern |
| `BYTECODE_GENERATED` | Ein Kompilat existiert | `lower_program` liefert `CompiledProgram` | erreicht fuer den ausfuehrbaren i64-Subset |
| `BYTECODE_VERIFIED` | Kompilat ist gegen den Verifizierer geprueft | `CompiledProgram::verify` ohne Befund | erreicht fuer denselben Subset |
| `DEPLOYABLE` | Deployment wird angenommen | Deployment-Grenze nimmt das Artefakt an | nur fuer den verifizierten i64-Subset, nicht fuer Vertraege |
| `EXECUTABLE` | Ausfuehrung liefert Vertragssemantik | Ausfuehrungsergebnis aus dem Vertrag | fuer keinen Vertrag erreicht |

## Consequence for contracts

Ein Vertrag (`Stmt::Contract`) erreicht derzeit **keinen** dieser Zustaende nach
`PARSED`:

- Der Rumpf wird als ausgeglichener Tokenstrom gehalten, nicht als AST.
- Es gibt keine Semantik und kein IR fuer Vertraege.
- Das Lowering senkt Vertragsruempfe nicht zu Bytecode.

Daraus folgt fail-closed: ein Vertrag ist kein gueltiges Compiler-Eingabeformat,
solange `BYTECODE_GENERATED` fuer ihn nicht nachgewiesen ist. Das Gate sitzt in
`lower::executable_subset_gate` und wird von `lower_program`, `atc check` und
`atc run` genutzt. Eine Quelle mit Vertrag wird mit einer Fehlermeldung
abgelehnt, die den Vertrag, seine Basis, die Zahl der Funktionen, Zustandsfelder,
Events und `require`-Guards nennt.

Verboten ist insbesondere:

- den Vertrag ueberspringen und ein Ersatzprogramm (`ConstI64(0); Return`) bauen,
- `ConstI64(0)` durch einen anderen Standardwert zu ersetzen,
- eine leere `__main__` als Programm auszugeben (Ausgabe `0`, Exit `0`),
- aus einem bestandenen `check` eine Ausfuehrbarkeit abzuleiten.

## Statusfuehrung

Ein Status wird nur mit Nachweis gefuehrt. Fehlt der Nachweis, lautet der Status
`NOT VERIFIED`, nicht `PASSED`. Nachweise sind reproduzierbar: Kommando,
Commit, Ergebnis. Dokumentation ohne Nachweis ist kein Status.
