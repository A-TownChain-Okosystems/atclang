// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! CLI-Integrationstests: `atc compile` / `atc check` gegen den
//! Differential-Korpus (gueltige Programme) und einen invaliden Eingabefall.

use std::path::Path;
use std::process::Command;

#[test]
fn cli_compile_und_check_ueber_differential_korpus() {
    let exe = env!("CARGO_BIN_EXE_atc");
    let corpus = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("differential")
        .join("corpus");
    let mut entries: Vec<std::path::PathBuf> = std::fs::read_dir(&corpus)
        .expect("corpus-Verzeichnis fehlt")
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.extension().is_some_and(|x| x.to_string_lossy() == "atc"))
        .collect();
    entries.sort();
    assert!(!entries.is_empty(), "Korpus leer — CLI-Test ungueltig");
    for path in entries {
        let out = Command::new(exe)
            .arg("compile")
            .arg(&path)
            .output()
            .unwrap();
        assert!(
            out.status.success(),
            "compile fehlgeschlagen fuer {:?}: {}",
            path,
            String::from_utf8_lossy(&out.stderr)
        );
        assert!(
            !out.stdout.is_empty(),
            "compile: leere JSON-Ausgabe fuer {:?}",
            path
        );
        let out = Command::new(exe).arg("check").arg(&path).output().unwrap();
        assert!(out.status.success(), "check fehlgeschlagen fuer {:?}", path);
    }
}

#[test]
fn cli_lehnt_ungueltiges_programm_und_aufrufe_ab() {
    let exe = env!("CARGO_BIN_EXE_atc");
    let bad = std::env::temp_dir().join("atc_cli_invalid.atc");
    std::fs::write(&bad, "fn 5() { return }").unwrap();
    let out = Command::new(exe).arg("compile").arg(&bad).output().unwrap();
    assert!(
        !out.status.success(),
        "invalides Programm muss fehlschlagen"
    );
    assert!(
        String::from_utf8_lossy(&out.stderr).contains("Kompilierfehler"),
        "Fehlermeldung fehlt: {}",
        String::from_utf8_lossy(&out.stderr)
    );
    let out = Command::new(exe).arg("compile").output().unwrap();
    assert_eq!(
        out.status.code(),
        Some(2),
        "Aufruffehler muss Exit-Code 2 geben"
    );
    let out = Command::new(exe)
        .arg("compile")
        .arg("/nicht/vorhanden.atc")
        .output()
        .unwrap();
    assert_eq!(
        out.status.code(),
        Some(2),
        "unlesbare Datei muss Exit-Code 2 geben"
    );
}
