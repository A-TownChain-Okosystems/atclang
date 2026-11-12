# Changelog — ATCLang

Alle wesentlichen Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
und dieses Projekt hält sich an [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - 2026-11-12

### Fixed (E1 — Audit 2026-11-12, F1: Contract-Lowering fail-closed)

- **Lowering:** Vertragsruempfe werden nicht mehr stillschweigend verworfen. `atc-core` senkt Contract-Ruempfe nicht zu Bytecode; deshalb lehnt `lower::executable_subset_gate` jede Quelle mit Vertrag fail-closed ab, bevor irgendein Kompilat entsteht. Die Meldung nennt Vertrag, Basis, Funktionen, Zustandsfelder, Events und `require`-Guards.
- **CLI `run`:** liefert fuer Vertraege keinen falschen Exit 0 mehr (vorher Ausgabe `0`, Exit `0`). Zusaetzlich verlangt `run` einen Einstiegspunkt (`lower::require_entry_point`), damit weder eine leere Datei noch ein reines Deklarationsmodul als Erfolg gilt.
- **CLI `check`:** prueft denselben Befund wie `run` (E1-Gate) statt kommentarlos OK zu melden. Die volle Lowering-Paritaet bleibt eigenes Finding (F3).
- **Kein Ersatzprogramm:** weder `Push(0); Halt` noch `ConstI64(0); Return` dienen als Platzhalter fuer abgelehnte Quellen.
- **Tests:** `crates/atc-core/tests/contract_e1_failclosed.rs` (10 Tests): Vertrag mit `main = 42`, Vertrag mit `require`, Vertrag mit Zustand/Events, Vertrag mit Basis, `examples/main.atc` (Gateway, 10 Funktionen) und weitere Beispiel-Vertraege, kein Artefakt fuer Vertraege, CLI-Exit-Codes fuer `run`/`check`. Gesamtsuite: 105 Tests, 0 Fehler.
- **Doku:** `docs/EXECUTION_STATE_MODEL.md` (Regel "Compiler Success ≠ Executable Contract", Zustaende PARSED bis EXECUTABLE) und Befundliste in `docs/ENGINEERING_AUDIT.md`.

## [Unreleased] - 2026-09-11

### Added (SCR-0098 — fehlende Kernmodule)

- **ABI:** `atclang.abi` — kanonischer Wert-Codec (UInt8..256/Int256/Bool/Address/Bytes/String/Vec/Map) und 4-Byte-Methoden-Selektoren (SHA3-256 der kanonischen Signatur).
- **Smart Contract Engine:** `atclang.contracts` — Deploy (deterministische Adressen aus Artifact-ID+Nonce), Call mit ABI-Selektor-Dispatch und msg-Kontext (caller/value/block/chain_id), persistenter `ContractStorage` mit State-Root-Hash, ATC-8300-Transfer-Referenzsemantik, Event-Log.
- **Host:** `atclang.host` — `HostContext` als einzige deterministische Quelle fuer Umgebung (block_timestamp statt Wanduhr, vm_seed statt random), `HostPolicy` mit Consensus-Pflichten, Gas-Zaehlung, Event-Log.
- **Artifact:** `atclang.artifact` — `.atca`-Format: kanonische JSON-Serialisierung, reproduzierbare Artifact-ID (sha3-256), Manipulationserkennung, ATC-STD-043/041-Feldpruefung.
- **Security:** `atclang.security` — statisches Gate (SEC-001..005): Host-Aufrufe/Random im Consensus-Profil = BLOCKER, unsafe_ ohne require = MEDIUM; profilabhaengige Gate-Semantik.
- **Profiles:** `atclang.profiles` — consensus/off_chain/debug mit Determinismus- und Host-Freigaben.
- **Package:** `atclang.package` — atcpkg-Manifest mit SPDX-, SemVer- und Range-Validierung (kein `*`-Pinning).
- **IR:** `atclang.ir` — JSON-IR (AST-Normalisierung) mit kanonischem IR-Hash fuer Differential-Gates.
- **CLI:** `atc compile|check|ir` — CI-taugliche Exit-Codes; compile schreibt `.atca`.
- **Tests:** 20 neue Tests (126 -> 146 passing).

## [1.0.0] - 2026-09-07

### Added

- **Gate G2 (Semantics):** `src/atclang/semantics/` TypeChecker-Subsystem mit Regeln SEM-001..SEM-012.
- **Spezifikation:** Normative Spezifikationen `specs/semantics/SPEC.md` und maschinenlesbare `registry.json`.
- **Governance & Standards:** Dokumentations-Konformität mit `ATC-STD-README-001` und `ATC-STD-MD-001`.
- **Pflichtdokumente:** `STATUS.md`, `CONTRIBUTING.md`, `ROADMAP.md`, `ARCHITECTURE.md`, `AGENTS.md`, `CODE_OF_CONDUCT.md`, `GOVERNANCE.md`.

### Fixed

- **Parser:** `parse_type` Korrektur für typ-annotierte Let-Bindings und Rückgabewerte.
- **Compliance:** Behebung aller MD-01..MD-10 Quality Gate Verstöße.

### Changed

- **Compiler:** `compile_source` führt standardmäßig semantischen Gate-Check aus.
