# ATCLang Architecture Baseline v1.0 (VERBINDLICH, AD-022, 06.09.2026)

**Kernsatz:** Der Compiler erzeugt Code. Der Verifier entscheidet, ob Code
gueltig ist. Die ATVM fuehrt AUSSCHLIESSLICH verifizierten Code deterministisch aus.

**Beschluss:** ATCLang 1.0 = Rust Canonical Core + Python Reference/Tooling +
formal spezifizierte Bytecode/ABI/Artifact/VM-Schichten. Python kontrolliert
NIEMALS die Konsensus-Ausfuehrung auf A-TownChain L1.

## Pipeline (10 Ebenen)

LANGUAGE LAYER (Lexer, Parser, AST, Semantics) -> ATC-IR (Typed IR, IR
Validator) -> Compiler (Optimization, Deterministic, Bytecode Gen) -> ATC
Bytecode + ABI + Artifact -> INDEPENDENT VERIFIER (Bytecode, Artifact, ABI,
Gas, Capabilities, Profile) -> ATVM (Deterministic Execution, Gas Meter,
State Access) -> Runtime (Contract Engine, State Machine, ABI Dispatcher) ->
HOST BOUNDARY (Capabilities, System Calls, External Data) -> A-TownChain L1
(Consensus, State, Transactions).

Parallel: TOOLING LAYER (Python SDK, Test Harness, Fuzzer, Reference Impl,
Dev Tools).

## Ziel-Repo-Struktur

    crates/   atclang-lexer, -parser, -ast, -semantics, -ir, -ir-verifier,
             -compiler, -bytecode, -bytecode-verifier, -abi, -artifact, -vm,
             -runtime, -host, -security, -profiles, -contracts, -gas, -state,
             -package, -cli                      (21 Rust-Crates, Phase 2)
    python/   sdk, reference, testing, fuzzing, tools
    specs/    language, bytecode, abi, artifact, vm, gas, security, profiles
    tests/    conformance, determinism, differential, compiler, verifier, vm,
             abi, artifact, security, fuzz
    docs/

## ATC-IR (zentrale Schicht)

Enthaelt: Typinformationen, Kontrollfluss, Datenfluss, Calls, Storage-Zugriffe,
Capability-Anforderungen, Gas-relevante Operationen, deterministische
Eigenschaften, Contract Entry Points, ABI-relevante Informationen.
Compiler und VM sind dadurch unabhaengig voneinander entwickelbar.

## Independent Verifier (Trust Boundary)

Der Verifier vertraut NIE dem Compiler und lehnt fremden oder manipulierten
Bytecode sicher ab. Pruefliste: Opcode-Validity, Stack-Safety, Control-Flow,
Jump Targets, Operand Types, Bounds, Memory/Storage Access, Capability
Requirements, Gas Validity, Profile Restrictions, ABI Consistency,
Artifact Integrity.

## Artifact (ATCA) — First-Class Protocol Object / Deployment Unit

Magic, Format Version, Language Version, Compiler Version, Target Profile,
ABI Version, Capability Set, Bytecode, Metadata, Code Hash, Artifact Hash,
Signature.

## Profiles

CONTRACT (deterministisch, restricted host access, bounded gas, keine
nondeterministischen APIs) · APPLICATION (breitere APIs, kontrollierte
Host-Capabilities) · SYSTEM (privilegierte Caps, OS/Runtime-Integration,
explizite Autorisierung) · UNRESTRICTED (nur außerhalb des L1-Konsensus).

## Capability Security (Deny-by-Default)

contract -> Capability -> Host Boundary -> Authorized Operation.
CAP_STORAGE_READ, CAP_STORAGE_WRITE, CAP_CALL_CONTRACT, CAP_EVENT_EMIT,
CAP_ORACLE_READ. Nicht vorhandene Capability: REQUEST -> DENY.
Keine versteckten Systemzugriffe.

## Determinismus (Protokollregel)

Im Contract-Kontext VERBOTEN: OS Time, Randomness, Filesystem, Unrestricted
Network, Threads, Process Spawn, hardware-spezifisches Verhalten,
Floating-Point-Konsenslogik, nichtdeterministische Iteration, unbounded
Resource Consumption.

## Konsensus-Grenze

Transaction -> Contract Artifact -> Artifact Validation -> Profile Validation
-> Capability Validation -> Bytecode Verification -> ABI Validation -> ATVM ->
Gas Accounting -> State Transition -> State Root -> Consensus.

## Differential Testing (Rust vs Python)

Rust Canonical und Python Reference muessen fuer identische Programme
identische ASTs, IR und Bytecode erzeugen. Abweichung = FAIL. Python ist
Referenz- und Kontrollsystem, nie Konkurrenz zum Produktionsruntime.

## Security Gates G0-G19 — KEIN FREEZE vor G18

G0 Repository Cleanup (ERLEDIGT 06.09.) · G1 Language Specification ·
G2 AST/Semantics · G3 ATC-IR · G4 IR Verifier · G5 Bytecode Specification ·
G6 Independent Bytecode Verifier · G7 ABI · G8 Artifact Format · G9 Capability
Security · G10 Profiles · G11 Deterministic ATVM · G12 Gas · G13 State
Transition · G14 Conformance · G15 Differential Testing · G16 Fuzzing ·
G17 Consensus Integration · G18 Security Audit · G19 FREEZE.

## Rollen

Rust Canonical: Lexer, Parser, AST, Semantics, IR, Compiler, Bytecode,
Verifier (Konsensus-Security), VM, Runtime, Gas, State (Konsensus), ABI,
Artifact (Protocol), Security (Sandbox), Profiles (Policy), CLI (Primary).
Python: SDK (Developer), Reference (Validation), Fuzzer (Testing), CI/Test-
Orchestrierung. UI: TypeScript (Developer UX).

## Migrationspfad — KEIN zweiter Rewrite

CURRENT PYTHON -> preserve -> REFERENCE IMPLEMENTATION -> specification
extraction -> FORMAL ATCLANG 1.0 SPEC -> RUST CANONICAL CORE -> DIFFERENTIAL
TESTING -> CONFORMANCE -> SECURITY AUDIT -> ATCLANG 1.0 FREEZE.

Bestehende Struktur (src/atclang/ = Python-Referenz) bleibt unveraendert
erhalten; docs/ATCLANG_1.0_ARCHITECTURE.md beschreibt sie weiter.
