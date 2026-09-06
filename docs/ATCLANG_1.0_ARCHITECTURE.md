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
