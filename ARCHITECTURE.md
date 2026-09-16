---
document_id: ATC-DOC-LANG-004
title: ATCLang Architecture
version: 1.1.0
status: active
owner: A-TownChain-Okosystems
created: 2026-09-07
updated: 2026-09-16
standard: ATC-STD-MD-001
---

# ATCLang Architecture

> Technische Architektur der proprietären System- und Contract-Sprache ATCLang.

## Systemübersicht

ATCLang ist als Multi-Pass-Compiler- und Sprachschicht strukturiert. Die Produktionsausführung folgt einer strikt getrennten Rust-first-Architektur:

1. **Frontend (`src/atclang/frontend/`):** Lexer/Tokenizer und Parser.
2. **Semantik (`src/atclang/semantics/`):** TypeChecker, Scope-Analyse und semantische Regeln.
3. **Compiler & IR (`src/atclang/compiler/`):** Codegen, Optimierung und Transformation in ATC-IR.
4. **VM/Runtime (`src/atclang/vm/`, `src/atclang/runtime/`):** Sprach-/Referenzwerkzeuge und Integrationsschicht.
5. **Stdlib (`src/atclang/stdlib/`):** Standardbibliothek für Chain, Crypto, Math, Primitives, Wallet, IO, Encoding und Collections.
6. **Rust Production Stack:** Kanonische Produktionsimplementierung für Compiler-/Verifier-Pfade, ATVM, Runtime, ABI/Artefaktvalidierung und sicherheitskritische Grenzen.

## Datenfluss

```text
Quellcode (.atc)
  -> Lexer
  -> AST
  -> TypeChecker / Semantik
  -> IR Compiler
  -> Bytecode
  -> Bytecode-Verifier (harte Trust-Boundary)
  -> kanonischer Rust ATVM / Runtime
  -> A-TownChain
```

## Rust-first / Python-reference policy

**Rust-first:** Konsens-, Verifikations-, ATVM-, Runtime-, ABI-, Sandbox- und sicherheitskritische Produktionspfade dürfen nicht von Python als Ausführungsinstanz abhängen.

**Python = Referenz:** Python ist Referenzimplementierung, SDK-/Tooling-, Test- und Fuzzing-Schicht. Eine Python-Referenzfunktion darf niemals eine erfolgreiche sicherheitskritische oder netzwerkseitige Produktionsoperation simulieren.

**Fail-closed:** Wenn eine Referenzfunktion keine echte Implementierung besitzt, muss sie explizit fehlschlagen oder in einem klar gekennzeichneten Testadapter laufen. False-success-Semantik ist unzulässig.

## Determinismus

Konsenspfade müssen deterministisch sein. Host-Zeit, Host-Zufall, Netzwerk-I/O, Dateisystem-I/O und sonstige externe Seiteneffekte dürfen nicht ungeprüft in kanonische Ausführung gelangen. Capability- und Verifier-Gates müssen solche Operationen vor der Produktionsausführung begrenzen oder ablehnen.

## DUAL-STACK-DIFFERENTIAL-MODELL

Rust ist die kanonische Produktionsausführung. Python kann als Referenzmodell dienen. Für gemeinsam unterstützte Sprach-/Bytecode-Semantik wird Differential Testing eingesetzt. Abweichungen zwischen den Stacks sind Release-blockierend, sofern sie nicht durch eine normative Spezifikationsänderung erklärt und getestet wurden.

## Sicherheitsgrenze

Der Bytecode-Verifier ist eine harte Trust-Boundary. Er validiert Bytecode, bevor kanonische Produktionsausführung erfolgt. Der Verifier darf keine nicht validierten Referenz- oder Host-Operationen als konsensgültig durchreichen.

## Architekturentscheidungen

Die Trennung wurde gewählt, weil Konsenscode deterministisch, auditierbar und unabhängig von einer dynamisch typisierten Referenzlaufzeit sein muss. Python bleibt dadurch für schnelle Referenztests und Fuzzing nutzbar, ohne die Vertrauensgrenze der Produktionsausführung zu vergrößern.
