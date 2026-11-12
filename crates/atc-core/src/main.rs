// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! ATCLang Compiler-CLI (Frontend-Gate, SCR-0083/0085).
//! `compile`: Lex -> Parse -> kanonische AST-JSON auf stdout (differentialfaehig).
//! `check`:   Validierung mit demselben Pfad wie `run` (Parse -> Lowering ->
//!            Verifizierer), Ergebnis nur via Exit-Code. Ein Programm, das
//!            `run` ablehnt, ist auch fuer `check` nicht gueltig — eine Pruefung
//!            darf nicht erfolgreich sein, wo die Ausfuehrung scheitert.
//! `run`:     kompiliert, verifiziert, fuehrt aus.

use atc_core::artifact::{Artifact, ArtifactMetadata};
use atc_core::lower::{
    executable_subset_gate, lower_program, require_entry_point, CompiledProgram,
};
use atc_core::parser::parse_program;
use std::env;
use std::fs;
use std::process::ExitCode;

const USAGE: &str = "ATCLang Compiler-CLI

USAGE:
    atc compile <datei.atc>   kompiliert: kanonische AST-JSON auf stdout
    atc run     <datei.atc>   kompiliert, verifiziert und fuehrt aus
    atc check   <datei.atc>   validiert (Parse + Lowering + Verifizierer), Exit-Code 0 = ok

EXIT-CODES:
    0  ok
    1  Kompilier-/Parse-/Laufzeit-Fehler
    2  Aufruffehler";

fn compile_to_bytecode(src: &str) -> Result<CompiledProgram, String> {
    let program = parse_program(src).map_err(|e| e.message)?;
    lower_program(&program).map_err(|e| e.message)
}

fn main() -> ExitCode {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.len() != 2 {
        eprintln!("{USAGE}");
        return ExitCode::from(2);
    }
    let mode = args[0].as_str();
    let path = args[1].as_str();
    let src = match fs::read_to_string(path) {
        Ok(s) => s,
        Err(e) => {
            eprintln!("Fehler: Datei nicht lesbar ({path}): {e}");
            return ExitCode::from(2);
        }
    };
    let program = match parse_program(&src) {
        Ok(p) => p,
        Err(e) => {
            eprintln!("Kompilierfehler in {path}: {}", e.message);
            return ExitCode::from(1);
        }
    };
    match mode {
        "run" => {
            let compiled = match compile_to_bytecode(&src) {
                Ok(c) => c,
                Err(msg) => {
                    eprintln!("Kompilierfehler in {path}: {msg}");
                    return ExitCode::from(1);
                }
            };
            // Kein Erfolg ohne Einstiegspunkt: eine leere __main__ ist kein
            // Programm. Sonst entstuende Ausgabe 0 / Exit 0 fuer "nichts".
            if let Err(e) = require_entry_point(&program) {
                eprintln!("Kompilierfehler in {path}: {}", e.message);
                return ExitCode::from(1);
            }
            let metadata = ArtifactMetadata {
                language_version: "1.0".into(),
                compiler_version: env!("CARGO_PKG_VERSION").to_string(),
                target_profile: "l1-deterministic-v1".into(),
                capabilities: Vec::new(),
            };
            let artifact = match Artifact::from_program(&compiled, metadata) {
                Ok(a) => a,
                Err(e) => {
                    eprintln!("Artifact-Fehler in {path}: {e:?}");
                    return ExitCode::from(1);
                }
            };
            let verified = match artifact.verify() {
                Ok(v) => v,
                Err(e) => {
                    eprintln!("Artifact-Verifikation fehlgeschlagen in {path}: {e:?}");
                    return ExitCode::from(1);
                }
            };
            match atc_core::vm::execute_verified(&verified) {
                Ok(value) => {
                    println!("{value}");
                    ExitCode::SUCCESS
                }
                Err(e) => {
                    eprintln!("Laufzeitfehler in {path}: {e:?}");
                    ExitCode::from(1)
                }
            }
        }
        "compile" => {
            println!("{}", program.to_json());
            let mut fns = 0;
            let mut stmts = 0;
            for s in &program.statements {
                stmts += 1;
                if let atc_core::ast::Stmt::Fn(f) = s {
                    fns += 1;
                    stmts += f.body.len();
                }
            }
            eprintln!("OK: {path} ({fns} Funktionen, {stmts} Anweisungen)");
            ExitCode::SUCCESS
        }
        // `check` validiert denselben Befund wie `run`: deklarierte Logik, die
        // nicht gesenkt wird (E1), ist keine gueltige Eingabe. Die volle
        // Lowering-Paritaet bleibt eigener Befund (schwaches Check, P1/P2).
        "check" => match executable_subset_gate(&program) {
            Ok(()) => {
                eprintln!("OK: {path} validiert");
                ExitCode::SUCCESS
            }
            Err(e) => {
                eprintln!("Kompilierfehler in {path}: {}", e.message);
                ExitCode::from(1)
            }
        },
        _ => {
            eprintln!("{USAGE}");
            ExitCode::from(2)
        }
    }
}
