// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! E1 (Audit 12.11.2026, F1) — Vertragsruempfe werden nicht mehr stillschweigend
//! verworfen. Der Compiler lehnt einen Vertrag fail-closed ab, statt scheinbar
//! gueltigen Bytecode zu erzeugen, der die Vertragslogik nicht enthaelt.
//!
//! Abnahmekriterien (Owner-Freigabe 12.11.2026):
//!  1. `Stmt::Contract` wird nicht mehr stillschweigend uebersprungen.
//!  2. Nicht unterstuetzte Vertragsruempfe erzeugen einen expliziten Compilerfehler.
//!  3. `atc run` liefert keinen falschen Exit 0.
//!  4. Ein fehlerhafter Vertrag kommt nicht bis zum Deployment (kein Artefakt).
//!  5. Kein `ConstI64(0); Return`-Ersatzprogramm entsteht.
//!  6. Regressionstest fuer den Vertrag mit `main = 42`.
//!  7. Regressionstest fuer die verlorenen Vertragsfunktionen (examples/main.atc).
//!
//! Compiler-Erfolg ist kein ausfuehrbarer Vertrag: ein bestandener Syntax- oder
//! Typcheck ist kein Nachweis fuer einen ausfuehrbaren Vertrag.

use atc_core::artifact::{Artifact, ArtifactMetadata};
use atc_core::bytecode::Instruction;
use atc_core::lower::{lower_program, require_entry_point};
use atc_core::parser::parse_program;
use std::path::{Path, PathBuf};
use std::process::Command;

fn metadata() -> ArtifactMetadata {
    ArtifactMetadata {
        language_version: "1.0".into(),
        compiler_version: "atc-core-0.1.0".into(),
        target_profile: "l1-deterministic-v1".into(),
        capabilities: Vec::new(),
    }
}

fn lower_err(src: &str) -> String {
    let prog = parse_program(src).expect("Parse-Fehler im Testfixture");
    match lower_program(&prog) {
        Ok(_) => panic!("Erwartet: Lowering-Fehler, erhalten: gueltiges Kompilat"),
        Err(e) => e.message,
    }
}

fn examples_path(name: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../examples")
        .join(name)
}

// ---------------------------------------------------------------------------
// 1 + 2 + 6: Vertrag mit `main = 42` wird abgelehnt, nicht zu 0 kompiliert.
// ---------------------------------------------------------------------------

#[test]
fn vertrag_mit_main_42_ist_kein_gueltiges_programm() {
    // Der Audit-Befund: dieser Vertrag ergab frueher `Ok(Some(0))` bzw. Exit 0
    // mit Ausgabe "0" — obwohl `return 42` nie im Bytecode ankam.
    let src = "contract Vault {\n    fn main() -> i64 {\n        return 42;\n    }\n}\n";
    let msg = lower_err(src);
    assert!(
        msg.contains("Vertrag 'Vault'"),
        "Fehlermeldung nennt den Vertrag nicht: {msg}"
    );
    assert!(
        msg.contains("nicht ausfuehrbar"),
        "Fehlermeldung verwischt den Befund: {msg}"
    );
    assert!(
        msg.contains("1 Funktionen"),
        "verlorene Funktion wird nicht beziffert: {msg}"
    );
    // Kein Ersatzprogramm: das Lowering liefert gar kein Kompilat.
    let prog = parse_program(src).unwrap();
    assert!(
        lower_program(&prog).is_err(),
        "Vertrag darf kein CompiledProgram ergeben"
    );
}

#[test]
fn vertrag_mit_require_wird_abgelehnt() {
    let src = "contract Token {\n    state owner: Address\n    fn transfer(to: Address, amount: u128) -> bool {\n        require(amount > 0, \"Betrag\")\n        return true\n    }\n}\n";
    let msg = lower_err(src);
    assert!(msg.contains("Vertrag 'Token'"), "Meldung: {msg}");
    assert!(
        msg.contains("1 require-Guards"),
        "require-Verwurf wird nicht beziffert: {msg}"
    );
}

#[test]
fn vertrag_mit_zustand_und_events_ist_nicht_ausfuehrbar() {
    let src = "contract Book {\n    state count: u64\n    event Booked(who: Address)\n}\n";
    let msg = lower_err(src);
    assert!(msg.contains("1 Zustandsfelder"), "Meldung: {msg}");
    assert!(msg.contains("1 Events"), "Meldung: {msg}");
}

#[test]
fn vertrag_mit_basis_bleibt_abgelehnt() {
    let src = "contract Child: Base::Parent {\n    fn init() {\n        return\n    }\n}\n";
    let msg = lower_err(src);
    assert!(
        msg.contains("Basen: Base::Parent"),
        "Basispfad wird nicht ausgewiesen: {msg}"
    );
}

// ---------------------------------------------------------------------------
// 4 + 5: Kein Artefakt, kein Deployment, kein ConstI64(0)-Ersatz im Bytecode.
// ---------------------------------------------------------------------------

#[test]
fn vertrag_erreicht_kein_artefakt_und_kein_deployment() {
    // Deployment setzt ein Artefakt voraus; ohne Kompilat gibt es keins.
    let src =
        "contract Gateway {\n    fn route(path: String) -> bool {\n        return true\n    }\n}\n";
    let prog = parse_program(src).unwrap();
    let compiled = lower_program(&prog).expect_err("Vertrag muss das Lowering ablehnen");
    assert!(
        compiled.message.contains("Vertrag 'Gateway'"),
        "Meldung: {}",
        compiled.message
    );

    // Gegenprobe zum alten Verhalten: fuer diesen Quelltext existiert kein
    // Artefakt, dessen Bytecode nur `ConstI64(0); Return` waere.
    let leeres_ersatzprogramm = [Instruction::ConstI64(0), Instruction::Return];
    let plain = parse_program("fn main() -> i64 { return 1; }").unwrap();
    let compiled_plain = lower_program(&plain).unwrap();
    let artifact = Artifact::from_program(&compiled_plain, metadata()).unwrap();
    let program = artifact
        .into_program()
        .expect("Artefakt muss rueckuebersetzbar sein");
    let entry_fn = &program.functions[program.entry as usize];
    assert!(
        entry_fn.bytecode.instructions != leeres_ersatzprogramm,
        "gueltiges Programm darf nicht auf das Ersatzprogramm zusammenfallen"
    );
}

#[test]
fn programm_ohne_einstiegspunkt_wird_nicht_ausgefuehrt() {
    // Frueher: leere __main__ -> ConstI64(0); Return -> Exit 0 / Ausgabe 0.
    // Das Lowering bleibt fuer Deklarationsmodule nutzbar; die Ausfuehrungs-
    // und Deployment-Grenze verlangt einen Einstiegspunkt.
    for src in ["", "fn helper(x: i64) -> i64 { return x + 1; }"] {
        let prog = parse_program(src).unwrap();
        let err = require_entry_point(&prog).expect_err("Einstiegspunkt fehlt");
        assert!(
            err.message.contains("keinen ausfuehrbaren Einstiegspunkt"),
            "Meldung: {}",
            err.message
        );
    }

    // An der CLI-Grenze: `atc run` darf daraus keinen Erfolg machen.
    let exe = env!("CARGO_BIN_EXE_atc");
    let path = std::env::temp_dir().join("atc_e1_no_entry.atc");
    std::fs::write(&path, "fn helper(x: i64) -> i64 { return x + 1; }\n").unwrap();
    let out = Command::new(exe).arg("run").arg(&path).output().unwrap();
    assert_eq!(out.status.code(), Some(1), "atc run muss Exit 1 liefern");
    assert!(
        String::from_utf8_lossy(&out.stdout).trim().is_empty(),
        "atc run darf keine Erfolgsausgabe zeigen"
    );
    assert!(
        String::from_utf8_lossy(&out.stderr).contains("Einstiegspunkt"),
        "Meldung: {}",
        String::from_utf8_lossy(&out.stderr)
    );
}

// ---------------------------------------------------------------------------
// 7: Regression gegen den echten Vertrag in examples/main.atc (Gateway).
// ---------------------------------------------------------------------------

#[test]
fn example_gateway_verliert_keine_funktionen() {
    let path = examples_path("main.atc");
    let src = std::fs::read_to_string(&path).expect("examples/main.atc fehlt");
    let msg = lower_err(&src);
    assert!(msg.contains("Vertrag 'Gateway'"), "Meldung: {msg}");

    // Der Vertrag enthaelt 10 Funktionsdeklarationen. Der Test bindet die Zahl
    // an die Datei: aendert sich der Vertrag, muss die Erwartung mitwachsen,
    // statt dass Funktionen unbemerkt verschwinden.
    let erwartete_funktionen = 10usize;
    let tatsaechlich = src
        .lines()
        .filter(|l| l.trim_start().starts_with("fn "))
        .count();
    assert_eq!(
        tatsaechlich, erwartete_funktionen,
        "examples/main.atc hat {tatsaechlich} Funktionen, erwartet {erwartete_funktionen}"
    );
    assert!(
        msg.contains(&format!("{erwartete_funktionen} Funktionen")),
        "verlorene Funktionen des Beispiels werden nicht beziffert: {msg}"
    );
    // Die Vertragsbestandteile werden ebenfalls ausgewiesen.
    assert!(msg.contains("Zustandsfelder"), "Meldung: {msg}");
    assert!(msg.contains("Events"), "Meldung: {msg}");
}

#[test]
fn weitere_beispiel_vertraege_werden_abgelehnt() {
    for name in ["atc8300.atc", "event_bus.atc", "kernel.atc", "shivamon.atc"] {
        let path = examples_path(name);
        let Ok(src) = std::fs::read_to_string(&path) else {
            continue;
        };
        // Beispiele, die am Parser scheitern, sind ein separater Befund (F1
        // betrifft das Lowering). Sie werden hier nicht mitgezaehlt, aber auch
        // nicht als gueltig behandelt: `check` schlaegt fuer sie ebenfalls fehl.
        let Ok(prog) = parse_program(&src) else {
            continue;
        };
        let err = lower_program(&prog).expect_err(&format!(
            "{name}: Vertrag darf nicht als ausfuehrbares Programm gelten"
        ));
        assert!(
            err.message.contains("Vertrag '"),
            "{name}: Ablehnung nennt keinen Vertrag: {}",
            err.message
        );
    }
}

// ---------------------------------------------------------------------------
// Das Gate ist nicht breiter als noetig: gewoehnliche Programme laufen weiter.
// ---------------------------------------------------------------------------

#[test]
fn programm_ohne_vertrag_bleibt_gueltig() {
    let src =
        "fn add(a: i64, b: i64) -> i64 { return a + b; }\nfn main() -> i64 { return add(20, 22); }";
    let prog = parse_program(src).unwrap();
    let compiled = lower_program(&prog).expect("Programm ohne Vertrag muss kompilieren");
    assert!(compiled.verify().is_ok());
}

// ---------------------------------------------------------------------------
// 3: CLI — `run` und `check` liefern fuer einen Vertrag keinen Erfolg.
// ---------------------------------------------------------------------------

#[test]
fn cli_run_und_check_lehnen_vertrag_ab() {
    let exe = env!("CARGO_BIN_EXE_atc");
    let dir = std::env::temp_dir();
    let path = dir.join("atc_e1_contract_vault.atc");
    std::fs::write(
        &path,
        "contract Vault {\n    fn main() -> i64 {\n        return 42;\n    }\n}\n",
    )
    .unwrap();

    for mode in ["run", "check"] {
        let out = Command::new(exe).arg(mode).arg(&path).output().unwrap();
        assert_eq!(
            out.status.code(),
            Some(1),
            "atc {mode} muss Exit 1 liefern, war {:?} (stderr: {})",
            out.status.code(),
            String::from_utf8_lossy(&out.stderr)
        );
        let stdout = String::from_utf8_lossy(&out.stdout);
        assert!(
            stdout.trim().is_empty(),
            "atc {mode} darf keine Ausgabe als Erfolg zeigen, war: {stdout:?}"
        );
        let stderr = String::from_utf8_lossy(&out.stderr);
        assert!(
            stderr.contains("Kompilierfehler") && stderr.contains("nicht ausfuehrbar"),
            "atc {mode}: Fehlermeldung fehlt: {stderr}"
        );
    }
}
