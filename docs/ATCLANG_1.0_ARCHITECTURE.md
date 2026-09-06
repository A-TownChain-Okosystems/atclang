# ATCLang 1.0.0 — Master-Architektur (VERBINDLICH, AD-019)

**Status:** ARCHITECTURE FREEZE: GO (Design, 06.09.2026) · Repository: Phase-1-Konsolidierung umgesetzt (EINE Implementierung je Verantwortlichkeit) · Phase 2: Subsystem-Implementierungen + Conformance.

## Kanonische Struktur

    atclang/
    ├── specs/          # NORMATIVE SPEZIFIKATION (VERSION.toml; language/types/abi/bytecode/vm/contracts/consensus)
    ├── docs/           # ERKLÄREND (Sprach-/Typ-/ABI-/VM-/Sicherheits-Doku)
    ├── src/atclang/    # IMPLEMENTIERUNG (das einzige Architekturzentrum)
    │   ├── frontend/      # Source → Lexer → Parser → AST (keine Blockchain-Ausführung)
    │   ├── semantics/     # Resolver → TypeChecker → Ownership/Borrow → CapabilityChecker → Validated AST
    │   ├── ir/            # ATC-IR + unabhängiger IR-Verifier
    │   ├── compiler/      # Codegen-Pipeline (Pipeline/Lowering/Optimizer)
    │   ├── bytecode/      # ATC-Bytecode + Bytecode-Verifier (harte Sicherheitsgrenze — vertraut NIE dem Compiler)
    │   ├── artifact/      # DAS transportierbare Objekt (Singular, analog bytecode/runtime): Versionen, Profile, Capability-Set, ABI, Bytecode, Metadata, Code-/Artifact-Hash
    │   ├── vm/            # WIE eine Instruktion ausgeführt wird (machine/interpreter/stack/memory/storage/gas/calls/traps/limits)
    │   ├── runtime/       # IN WELCHEM ZUSTAND (context/transaction/block/caller/world_state/state_transition/environment)
    │   ├── contracts/      # WAS ein Contract ist (Contract → ABI → Invocation → Runtime → ATVM)
    │   ├── abi/           # standardisierte Schnittstelle Wallet ↔ Contract ↔ ATVM
    │   ├── host/          # externe Ressourcen (storage/crypto/blockchain/network)
    │   ├── security/      # ZENTRAL: capabilities/determinism/secrets/limits/validation
    │   ├── profiles/      # contract/application/system/unrestricted (determinism liegt in security/, NICHT hier; unrestricted ist nie automatisch als Contract deploybar)
    │   ├── stdlib/        # Standardbibliothek (core/crypto/blockchain/wallet/storage/network/os)
    │   ├── package/       # Manifest/Dependency/Resolver/Lockfile/Registry
    │   └── cli/           # check/compile/run/test/fmt/lint/inspect/disassemble/verify/package
    ├── tests/         # frontend…compatibility + fixtures (source→ast→ir→bytecode→artifact)
    ├── examples/      # .atc-Programme
    └── tools/         # format/lint/verify/generatoren/conformance

## Kontrollfluss

SOURCE → FRONTEND → SEMANTICS → ATC-IR → IR-VERIFIER → OPTIMIZER → BYTECODE → BYTECODE-VERIFIER → ARTIFACT → ARTIFACT-VALIDATOR → PROFILE-CHECK → SECURITY-CHECK → ATVM → RUNTIME → STATE-TRANSITION → WORLD-STATE → HOST

**Konsensgrenze (A-TownChain):** nur Transaction → Contract-Artifact → Validation → Profile → Deterministic-Policy → ATVM → Gas → State-Transition → New-World-State ist konsensrelevant. Im Contract-Kontext VERBOTEN: OS-Zeit, random(), Filesystem, unrestricted Network, Threads, Process-Spawning, hardwareabhängiges Verhalten, nichtdeterministische Iteration, Floating-Point-Konsenslogik.

## Source-of-Truth-Regel

specs/ → Implementierung → generierte Tabellen → Conformance-Tests. KEINE zweite Opcode-, ABI- oder Grammar-Definition in der Implementierung.

## Konsolidierungs-Audit 06.09.2026 (Phase-1-Basis)

| Bereich | Befund | Maßnahme |
|---|---|---|
| VM | atc-vm = 116/98-LOC-Stub vs. kanonisch 978 LOC | entfernt (Vault+Historie) |
| Stdlib | atc-stdlib: 4 identisch, math.py differs (154/138), 4 unique (*_ext) | entfernt; Merge-Kandidaten Phase 2 |
| atc-atclang | kleinere Parallel-Implementierungen (Parser 1431/892, Compiler 561/2229 LOC) | entfernt; Re-Export-Layer entfällt |
| Legacy-Shims | lexer.py/parser.py/compiler.py à 5–6 LOC | entfernt |
| Kanonisch | src/atclang/ — 40 py, 22.617 LOC, end-to-end verifiziert | SOURCE OF TRUTH |

Entfernte Inhalte: bewahrt im Wiki-Vault (a-townchain-os-docs/docs/archive/monorepo-full/) und Git-Historie.

## Phase-2-Arbeitsliste

1. bytecode/-Subsystem-Split (opcodes/format/verifier) aus compiler/bytecode*.py
2. semantics/, ir/, artifact/, contracts/, abi/, host/, security/, profiles/, package/, cli/ implementieren
3. specs/ normativ ausformulieren (VERSION.toml-Skelett steht)
4. Conformance-Fixtures verbindlich (hello.atc → expected.ast → expected.ir → expected.atcb → expected.artifact)
5. Meta-Doku aus src/atclang/ an 1.0-Positionen (docs/, root) verschieben


---

## Re-Audit 06.09.2026 (Commit 044604f) — GATE: YELLOW

Architektur 8.5/10 · Implementierung 5.5/10 · Production/Consensus-Readiness
noch nicht gegeben. Phase 1 bestaetigt. Ab jetzt: VERTIKALE Subsystem-
Implementierung mit Conformance-Absicherung — kein weiterer grosser Rebuild.

**R-01 (Legacy-Artefakte im Tree: modules/atc-atclang/__pycache__,
tests/__pycache__/*.pyc) — beseitigt; .gitignore um __pycache__/, *.py[cod],
.pytest_cache/ erweitert.**

## Priorisierte Phase-2-Roadmap (VERBINDLICH)

- **P0:** (1) Hygiene ERLEDIGT · (2) Semantics · (3) ATC-IR · (4) IR-Verifier · (5) Bytecode-Verifier
- **P1:** (6) Artifact-Format · (7) Artifact-Validator · (8) ABI · (9) Capability-Security · (10) Profiles
- **P2:** (11) Contracts · (12) Host-Boundary · (13) Package-System · (14) CLI
- **P3:** (15) Conformance-Fixtures · (16) Determinism-Suite · (17) Gas-Tests · (18) Fuzzing · (19) Differential-Testing

## Normative Verschärfungen (aus dem Re-Audit)

1. **Bytecode-Verifier = harte Trust-Boundary:** prueft Opcode-/Operand-Validity,
   Stack-Safety, Control-Flow, Jump-Targets, Limits, Determinismus, Resource-
   Bounds. Compiler-Output ist NIEMALS Vertrauensanker.
2. **Capability-Policy-Matrix** (Contract/Application/System/Unrestricted) als
   Enforcement-Pflicht: Netzwerk, Filesystem, Clock, Randomness, Threads,
   Process-Spawn im Contract-Kontext VERBOTEN; deterministische Arithmetik
   Pflicht; Storage/Ausgaben kontrolliert und geprüft.
3. **Sprachstrategie (AD-021, VERBINDLICH): ATCLang = Rust-first, Python = Referenz.**
   Rust kanonisch/Produktion: Compiler (Lexer/Parser/AST/Semantics/ATC-IR/
   Optimizer/Codegen), Bytecode-Verifier, ATVM, Runtime, ABI/Artifact-Validator,
   Security/Sandbox, CLI. Python: Referenz-Implementierung (bestehender Code
   bleibt — KEIN Wegwerfen), SDK, Test-/Fuzzing-Tooling, AI-Integration.
   Phasen: (1) Python-Referenz weiterentwickeln (Sprachentwicklung) ·
   (2) Rust-Kernkomponenten: atclang-core/-ir/-bytecode/-verifier/-vm/
   -runtime/-abi · (3) Rust = kanonische Produktionsimplementierung.
   **DUAL-STACK-DIFFERENTIAL-MODELL:** Rust- und Python-Stacks muessen fuer
   identische Programme identische ASTs, IR, Bytecode und State-Transitions
   erzeugen — Differential Testing ist damit verbindliches Conformance-
   Kriterium (Roadmap-Item 19 aufgewertet). Begruendung: ATCLang ist keine
   Skriptsprache — Smart Contracts erfordern Memory Safety, Determinismus,
   Geschwindigkeit, geringe Runtime-Overheads, sichere Concurrency,
   Ressourcen-Kontrolle und eine harte Host/VM-Security-Boundary.

**Aurora AI (AD-021):** Rust Core (Model Manager, Scheduler, Hardware-
Abstraction, Security, IPC, Plugin-Runtime) + Python AI-Layer (PyTorch/ONNX/
LLM, ROCm). ATCLang -> Rust-first; Aurora -> Rust-Core + Python-AI-Layer.
