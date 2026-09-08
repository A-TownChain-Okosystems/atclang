# ATCLang Semantics Specification — Gate G2 (v1.0.0)

spec:
  gate: G2
  title: "Semantics / Verhaltensregeln"
  version: "1.0.0"
  status: accepted
  date: "2026-09-07"
  source: "specs/language/SPEC.md §5-6 (G1) + Referenz-Compiler"
  implementation: "src/atclang/semantics/type_checker.py"
  machine_readable: "specs/semantics/registry.json"
---

## 1. Geltung und Pipelinestelle

G2 macht die Semantik von G1 (§5) operationell: Der **TypeChecker** ist ein
unabhaengiges Subsystem, das den AST nach dem Parsen und vor der Code-
Erzeugung validiert. Es gilt die AD-022-Vertrauensphilosophie: **Compiler
erzeugt Code — Verifier entscheidet Gueltigkeit.** Der TypeChecker erzeugt
keinen Code und mutiert nichts: AST rein, Diagnosen raus.

```text
source → Lexer → Parser → [TypeChecker (G2, hier)] → Compiler → ATVM
```text

## 2. Scopes und Symbole

- Scope-Kette: Modul → Contract → Funktion → Block/Loop. Innere Scopes
  sehen ausseren; **Shadowing ist erlaubt** (Redefinition im selben Scope
  ist ein Fehler, in Kind-Scopes nicht).
- Top-Level-Funktionen und Typdefinitionen (contract/struct/enum) werden
  vor der Pruefung registriert (Vorwaertsreferenzen erlaubt).
- `let`-Definitionen wirken sequenziell (Nutzung vor Definition = Fehler).

## 3. Typmodell (konservativ)

Gepruefte Primitiven: `int`, `float`, `string`, `bool`, `list`, `map`,
`void`. **Alle weiteren Typbezeichner** (u8, u64, u128, Address, Vec<...>,
Map<...>, benutzerdefinierte) gelten als `any` und werden nicht angefochten.
Ziel: keine False Positives gegenueber der Referenz. `int` ist nach
`float` zuweisbar (Promotion), alles andere ist unter den Primitiven strikt.

## 4. Pruefregeln (Regel-IDs → Fehlerklassen)

| Regel | Verletzung | Fehlerklasse (compiler/errors.py) |
|---|---|---|
| SEM-001 | Doppelte Definition im selben Scope (Variablen, Top-Level-Namen, Contract-Mitglieder, Contract-Funktionen) | DuplicateSymbolError |
| SEM-002 | Unbekanntes Symbol in Ausdrucksposition | UndefinedSymbolError |
| SEM-003 | `break` ausserhalb einer Loop | BreakOutsideLoopError |
| SEM-004 | `continue` ausserhalb einer Loop | ContinueOutsideLoopError |
| SEM-005 | `return` ausserhalb einer Funktion | InvalidReturnError |
| SEM-006 | `let`-Annotation passt nicht zum Initialisierungstyp | TypeMismatchError |
| SEM-007 | `return`-Wert passt nicht zum deklarierten Funktionstyp | TypeMismatchError |
| SEM-008 | Built-in mit falscher Aritaet aufgerufen | InvalidCallError |
| SEM-009 | Built-in-Argument definitiv unpassend | TypeMismatchError |
| SEM-010 | Doppelter Funktionsparameter | DuplicateParameterError |
| SEM-011 | Operator zwischen inkompatiblen Primitiven | TypeMismatchError |
| SEM-012 | Bedingung ist string/list/map/null statt bool-faehig | TypeMismatchError |

Nicht angefochten (bewusst konservativ): unbekannte Bezeichner-Aufrufe
(moegliche Stdlib/Runtime-Funktionen wie `now()`), Methoden- und
Namespace-Aufrufe (`self.x.f()`, `ATCMath.sqrt()`, `Vec::new()`), alle
Typen ausserhalb der Primitiven-Liste.

## 5. Built-in-Signaturen (13, unveraendert aus G1 §5.3)

`print(any)→void` · `len(any)→int` · `range(int)→list` · `sha256(any)→string` ·
`int(any)→int` · `float(any)→float` · `str(any)→string` · `bool(any)→bool` ·
`abs(int)→int` · `min(int,int)→int` · `max(int,int)→int` ·
`push(list,any)→void` · `pop(list)→any`

## 6. Typ-Inferenz (Ausdruecke)

- Literale: int/float/string/bool/null/list/map
- Vergleiche und `and`/`or` → bool
- `+`: string+string→string, list+list→list, numerisch→(float wenn ein
  float beteiligt, sonst int)
- `- * / %`: numerisch analog; definitiv unpassende Operanden → SEM-011
- `not`/`!` → bool; unaeres `-` → Operandtyp
- Identifier → deklarierter Typ aus Scope-Kette; Built-in-Aufruf → Tabelle;
  sonst `any`

## 7. API-Vertrag

| Funktion | Verhalten |
|---|---|
| `TypeChecker().check_and_report(ast)` | nicht-werfend, gibt `List[SemanticDiagnostic]` (rule, error_class, message, line, col) |
| `TypeChecker().check(ast)` | strict — wirft die erste Verletzung als CompileError-Subklasse (semantisches Gate vor Codegen) |
| `analyze_source(source)` | Komfort-Entry: parse + check_and_report |

Jede Diagnose traegt die Regel-ID und die Ziel-Fehlerklasse aus
compiler/errors.py (45-Klassen-Modell aus G1 §6). Die Diagnosen sind damit
differenztestbar (G19: identisches Programm → identische Diagnosen).

## 8. G2-Kriterien — ERFUELLT (07.09.2026)

- [x] Semantik als unabhaengiges Subsystem `src/atclang/semantics/`
      (TypeChecker, Trust-Boundary, kein Codegen)
- [x] Alle Pruefregeln der G1-§5-Quelle operationell (Scopes, Typ-Checks,
      break/continue/return-Platzierung, Built-in-Signaturen)
- [x] Normative Spezifikation + maschinenlesbares registry.json
- [x] Diagnosen auf die G1-Fehlerklassen abgebildet (SEM-IDs)
- [x] Referenz-Korpus: alle 4 parsbaren Beispiel-Programme CLEAN
      (atcos_main.atc scheitert vor der Semantik am Parser — `trait`
      ist kein unterstuetztes Keyword; separater Parser-Backlog)
- [x] Testsuite tests/test_semantics.py (Regeln einzeln, valid + invalid)

Naechstes Gate: **G3 (ATC-IR)**.

## 9. Findings bei der G2-Umsetzung (07.09.2026)

1. **Parser-Bug behoben (parse_type):** Die Funktion gab ihr Ergebnis NUR
   im generischen Zweig (`<...>`) zurueck — jeder nicht-generische Typ
   (int, string, u64, ...) lieferte None. Sämtliche Typ-Annotationen
   (`let x: int`, `fn f() -> int`, Parameter) fielen damit bisher aus dem
   AST. Jetzt: `return node` auch im nicht-generischen Pfad; Annotationen
   stehen im AST und sind semantisch pruefbar.
2. **compile_source führt das semantische Gate aus** (`semantic_check=True`
   default): TypeChecker laeuft nach parse, vor Codegen (AD-022: Verifier
   entscheidet). Alle 4 parsbaren Beispiele passieren das Gate.
3. **Compiler-Backlog (KEINE Semantik-Themen, pre-existing per Stash-Verify):**
   `SliceExpr`-Codegen fehlt (event_bus.atc:38), `MatchStatement`-Codegen
   fehlt (shivamon.atc:77), `TypeError: unhashable list` im Constant-Pool
   (kernel.atc), `trait`-Keyword fehlt im Parser (atcos_main.atc). Diese
   Luecken zaehlen zu Phase 2/P2-P3 des Rebuilds, nicht zu G2.
