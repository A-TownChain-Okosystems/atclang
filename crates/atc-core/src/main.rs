// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! ATCLang Compiler-CLI (Frontend-Gate, SCR-0083/0085).
//! `compile`: Lex -> Parse -> kanonische AST-JSON auf stdout (differentialfaehig).
//! `check`:   stille Validierung, Ergebnis nur via Exit-Code.
//! Noch NICHT Bestandteil: AST->Bytecode-Lowering (der Bytecode-Verifizierer ist
//! als Bibliothek ueber atc_core::bytecode erreichbar; Lowering folgt via SCR).

use atc_core::parser::parse_program;
use std::env;
use std::fs;
use std::process::ExitCode;

const USAGE: &str = "ATCLang Compiler-CLI

USAGE:
    atc compile <datei.atc>   kompiliert: kanonische AST-JSON auf stdout
    atc check   <datei.atc>   validiert still (Exit-Code 0 = ok)

EXIT-CODES:
    0  ok
    1  Kompilier-/Parse-Fehler
    2  Aufruffehler";

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
        "check" => {
            eprintln!("OK: {path} validiert");
            ExitCode::SUCCESS
        }
        _ => {
            eprintln!("{USAGE}");
            ExitCode::from(2)
        }
    }
}
