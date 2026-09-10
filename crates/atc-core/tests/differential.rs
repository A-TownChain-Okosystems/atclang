// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Differential-Tests: Rust-Canonical-Core vs. Python-Referenz (SCR-0084).
//! differential/expected/*.json wurde von tools/differential/dump_reference.py
//! aus dem Python-Referenz-Parser generiert. Dieser Test prueft, dass der
//! Rust-Parser BYTGLEICHE kanonische JSON-Serialisierung erzeugt.

use atc_core::parser::parse_program;
use std::fs;
use std::path::Path;

#[test]
fn differential_gemeinsamer_subset() {
    let root = Path::new(env!("CARGO_MANIFEST_DIR")).join("differential");
    let corpus = root.join("corpus");
    let expected = root.join("expected");
    let mut entries: Vec<std::path::PathBuf> = fs::read_dir(&corpus)
        .expect("corpus-Verzeichnis fehlt")
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| {
            p.extension().map_or(false, |x| x.to_string_lossy() == "atc")
        })
        .collect();
    entries.sort();
    assert!(!entries.is_empty(), "Corpus leer — Differential-Test ungueltig");
    let mut n = 0;
    for path in entries {
        let src = fs::read_to_string(&path).unwrap();
        let stem = path.file_stem().unwrap().to_string_lossy().to_string();
        let exp_path = expected.join(format!("{}.json", stem));
        let exp = fs::read_to_string(&exp_path)
            .unwrap_or_else(|_| panic!("expected/{}.json fehlt", stem));
        let prog = parse_program(&src)
            .unwrap_or_else(|e| panic!("{}: Parse-Fehler: {:?}", stem, e));
        let got = prog.to_json();
        assert_eq!(exp.trim(), got, "DIVERGENZ in {}", stem);
        n += 1;
    }
    println!("Differential: {} Corpus-Dateien bytgleich mit Python-Referenz", n);
}
