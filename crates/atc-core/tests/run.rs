// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! End-to-End: Quelle -> Parse -> Lower (mit Verifizierung) -> Execute.
//! Deckt Welle 2 ab: Lowering-Fehler (fail-closed) und deterministische
//! Laufzeitfehler (checked-Arithmetik, feste Aufruftiefe).

use atc_core::lower::{lower_program, LowerError};
use atc_core::parser::parse_program;
use atc_core::vm::execute;

fn run(src: &str) -> Result<i64, String> {
    let prog = parse_program(src).map_err(|e| e.message)?;
    let compiled = lower_program(&prog).map_err(|LowerError { message }| message)?;
    execute(&compiled).map_err(|e| format!("{e:?}"))
}

#[test]
fn end_to_end_main_mit_funktionsaufruf() {
    let src =
        "fn add(a: i64, b: i64) -> i64 { return a + b } fn main() -> i64 { return add(2, 3) }";
    assert_eq!(run(src), Ok(5));
}

#[test]
fn end_to_end_verschachtelte_calls() {
    // ohne Kontrollstrukturen: direkte Rueckgabe ueber verschachtelte Calls
    let src = "fn twice(n: i64) -> i64 { return n * 2 } fn quad(n: i64) -> i64 { return twice(twice(n)) } fn main() -> i64 { return quad(3) }";
    assert_eq!(run(src), Ok(12));
}

#[test]
fn top_level_statements_laufen_in_entry() {
    // nur top-level lets: Entry-Resultat ist der implizite Return 0
    let src = "let a = 1 + 2\nlet b = a * 3";
    assert_eq!(run(src), Ok(0));
}

#[test]
fn dynamic_division_durch_null_ist_laufzeitfehler() {
    let src =
        "fn div(a: i64, b: i64) -> i64 { return a / b } fn main() -> i64 { return div(7, 0) }";
    match run(src) {
        Err(m) if m.contains("DivisionByZero") => {}
        other => panic!("DivisionByZero erwartet, got {other:?}"),
    }
}

#[test]
fn konstante_division_durch_null_wird_bereits_verifizierer_abgelehnt() {
    let src = "fn main() -> i64 { return 1 / 0 }";
    match run(src) {
        Err(m) if m.contains("Verifizierer") => {}
        other => panic!("Verifizierer-Ablehnung erwartet, got {other:?}"),
    }
}

#[test]
fn arithmetic_overflow_ist_fehler_kein_wrap() {
    let src = "fn main() -> i64 { return 9223372036854775807 + 1 }";
    match run(src) {
        Err(m) if m.contains("ArithmeticOverflow") => {}
        other => panic!("ArithmeticOverflow erwartet, got {other:?}"),
    }
}

#[test]
fn unbegrenzte_rekursion_ist_deterministischer_fehler() {
    let src = "fn loop(n: i64) -> i64 { return loop(n) } fn main() -> i64 { return loop(1) }";
    match run(src) {
        Err(m) if m.contains("CallDepthExceeded") => {}
        other => panic!("CallDepthExceeded erwartet, got {other:?}"),
    }
}

#[test]
fn lowering_ist_fail_closed() {
    // unbekannter Bezeichner
    assert!(run("fn main() -> i64 { return unbekannt + 1 }").is_err());
    // unbekannte Funktion
    assert!(run("fn main() -> i64 { return fehlt(1) }").is_err());
    // falsche Argumentzahl
    assert!(run("fn f(a: i64) -> i64 { return a } fn main() -> i64 { return f(1, 2) }").is_err());
    // return auf Programmebene
    assert!(run("return 5").is_err());
    // Operator ausserhalb des Subsets
    assert!(run("fn main() -> i64 { return 1 % 2 }").is_err());
    // doppelte Funktionsdefinition
    assert!(run(
        "fn f() -> i64 { return 1 } fn f() -> i64 { return 2 } fn main() -> i64 { return f() }"
    )
    .is_err());
}
