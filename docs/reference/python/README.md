# ATCLang Python-Bestand — Referenz-Dokumentation

> Vollstaendige AST-generierte Bestandsaufnahme des Python-Codes in atclang
> (Stand 2026-09-17, vor der Rueckfuehrung auf Rust-only). Rust bleibt
> kanonischer Konsens-Kern (crates/atc-core); dieses Dokument ersetzt nach
> Loesung der Python-Referenz deren Rolle als Beschreibung.

## Architektur-Grenze

- **Rust is canonical**: crates/atc-core = produktiver Bytecode-Verifizierer (fail-closed Bounds).
- **Python = Referenz**: Pipeline fuer Tests/Simulation — wird mit diesem Stand
  vollstaendig dokumentiert und anschliessend geloescht (Historie bleibt im Git).

## Paket-Uebersicht (src/atclang)

| Paket | Rolle |
|---|---|
| `abi/` | ABI-Definition (Call-/Callee-Views, Funktions-ABI) |
| `artifact/` | Artefakt-Handling (ATC-Artefakt-Format) |
| `cli/` | Kommandozeilen-Frontend |
| `compiler/` | Bytecode-Compiler (kontrollfluss, konstanten, ausdruecke, funktionen, klassen, ...) |
| `contracts/` | Contract-Utilities |
| `frontend/` | Lexer/Parser-Frontend (Tokenisierung, AST) |
| `host/` | Hostcalls (ATCHost) |
| `ir/` | Zwischendarstellung (IR) |
| `package/` | Paket-Handling |
| `profiles/` | Build-Profile |
| `runtime/` | Treiber-Laufzeit (driver_framework, event-Handling) |
| `security/` | Security-Gate (statische Analyse, fail-closed Verboets-Importe) |
| `semantics/` | Semantik-Analyse (Gate-Checks vor Codegen) |
| `stdlib/` | Standardbibliothek (collections, chain, crypto, io, math, net, strings, types, wallet) |
| `vm/` | Stack-VM (ATCStdlib-Hostcalls, ATCVM-Interpreter, OP-Opcode-Tabelle) |

## Verzeichnis

## src/atclang/ — Referenz-Implementierung (Pipeline)

*57 Dateien, 23003 Zeilen*

- [src/atclang/](src-atclang.md) — 57 Dateien, 23003 Zeilen

## tests/ — Test-Suiten

*6 Dateien, 1575 Zeilen*

- [tests/](tests.md) — 6 Dateien, 1575 Zeilen

## tools/ — Governance-Werkzeuge

*3 Dateien, 588 Zeilen*

- [tools/](tools.md) — 3 Dateien, 588 Zeilen

## Kern-Semantik der Referenz-VM (kuratiert)

Die folgenden Eigenschaften sind im Rust-Kern (crates/atc-core) verbindlich
abgebildet und hier als Beschreibung konserviert:

- **Stack-VM**: Operanden-Stack, Call-Frames, Gas-Limit (GasError/RequireError
  fail-closed). Verifizierer prueft Bounds von Stack, Locals und Funktionen
  (LoadLocal-Bounds-Check ist Teil der Verifikation, nicht der Laufzeit).
- **Konsens-Zeit**: OP.TIMESTAMP liest ausschliesslich den Block-Header
  (`block.timestamp`); Boot-Globals sind Genesis-deterministisch (0). Keine
  Wanduhr, kein os-RNG im Konsens-Pfad.
- **Hostcall-Vertrag**: ATCStdlib-Hostcalls sind Referenz-Failures per Design:
  `net_send` fail-closed (kein virtueller Transport), `rpc_call` dispatcht nur
  an registrierte Handler (sonst 404), ECDSA/JWT sind deterministische
  Simulations-/Strukturpruefungen mit dokumentierten Grenzen — echte Krypto:
  atc-wallet (ECDSA) bzw. Auth-Modul.
- **Security-Gate** (static_analysis.py): fail-closed Verboets-Import-Detektion
  auf Contract-Quellen; Rust-Verifizierer als Konsens-Ziel.
- **Compiler-Pipeline**: frontend (lexer->parser) -> semantics (Gate) ->
  ir -> compiler (Bytecode + Determinismus-/Bounds-Patches) -> vm/artifact.
- **Determinismus-Test**: determinism_check.py (Checker v2, SCR-0126) mit
  Allowlist; zwei identische Testlaeufe als Evidenz.

## Loesch-Protokoll

Mit Stand nach dieser Dokumentation wird `src/atclang/` (Referenz-Pipeline)
und `tests/` (Python-Test-Suiten) geloescht. Git-Historie bleibt vollstaendig
erhalten (subtree/merge-Historie). Kanonisch verbleibt: `crates/atc-core`
(Rust) plus die .atc-Programm-Korpusdateien (verschoben nach `examples/`).
