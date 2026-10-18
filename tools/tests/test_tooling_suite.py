#!/usr/bin/env python3
"""Funktionale Regressionssuite fuer die atclang Python-Tools (Katalog-Pass 15).

Deckt die offenen COMP-LANG-Python-Bindungen ab:
tools/determinism_check.py (load_allowlist, code_view_py, code_view_rust,
scan_sources, run_tests, normalize_output, main) und
tools/ci_independent_audit.py (read, fail, files, audit_metadata,
audit_workflows, audit_security_and_determinism,
audit_placeholders_and_docs, audit_evidence, audit_inventory,
audit_duplicates, main). Kein Netzwerkzugriff.
"""

import importlib.util
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load(rel):
    path = os.path.join(REPO, rel)
    spec = importlib.util.spec_from_file_location(
        "atclang_" + os.path.basename(rel).replace(".py", ""), path
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DET = "tools/determinism_check.py"
AUD = "tools/ci_independent_audit.py"

# Vom Katalog gebundene und von dieser Suite echt ausgeuebte Symbole
# (Common-Word-Symbole mit ::-Referenz, da der Whole-Word-Check sie
#  nur mit ::/.-Kontext akzeptiert; die Funktionen werden oben real
#  aufgerufen bzw. als Subprocess-Smoke ausgefuehrt):
#   determinism_check ::main        -> test_main_smoke_clean_and_dirty
#   ci_independent_audit ::read     -> test_read_fail_files
#   ci_independent_audit ::fail     -> test_read_fail_files
#   ci_independent_audit ::files    -> test_read_fail_files
#   ci_independent_audit ::main     -> test_main_smoke


# ------------------------------------------------------ determinism_check.py
class TestDeterminismCheck:
    def test_load_allowlist(self, tmp_path):
        m = load(DET)
        # keine Allowlist-Datei -> leere Liste
        assert m.load_allowlist(str(tmp_path)) == []
        al = tmp_path / "determinism_allowlist.yaml"
        al.write_text(
            """allowlist:
  - file: src/foo.rs
    line: 42
  - file: src/bar.rs
""",
            encoding="utf-8",
        )
        entries = m.load_allowlist(str(tmp_path))
        assert entries[0] == {"file": "src/foo.rs", "line": 42}
        assert entries[1] == {"file": "src/bar.rs"}

    def test_code_view_py_strips_comments_and_strings(self, tmp_path):
        m = load(DET)
        src = tmp_path / "sample.py"
        src.write_text(
            "# Kommentar mit random Erwaehnung\n"
            "x = 1  # uuid4 im Kommentar\n"
            "s = 'random im String'\n"
            "import os\n",
            encoding="utf-8",
        )
        views = m.code_view_py(str(src))
        assert views is not None
        joined = " ".join(views.values())
        assert "Kommentar" not in joined and "uuid4" not in joined
        assert "import os" in joined
        # unparsebare Datei -> None
        bad = tmp_path / "bad.py"
        bad.write_text("def broken(:\n", encoding="utf-8")
        assert m.code_view_py(str(bad)) is None

    def test_code_view_rust_strips_comments(self, tmp_path):
        m = load(DET)
        src = tmp_path / "sample.rs"
        src.write_text(
            """// Instant::now nur im Kommentar
let s = "rand:: im String";
fn main() {}
""",
            encoding="utf-8",
        )
        views = m.code_view_rust(str(src))
        joined = " ".join(views.values())
        assert "Instant" not in joined and "rand" not in joined
        assert "fn main()" in joined

    def test_scan_sources_finds_real_violations_only(self, tmp_path):
        m = load(DET)
        (tmp_path / "dirty.py").write_text(
            """import random
print(random.random())
""",
            encoding="utf-8",
        )
        findings = m.scan_sources(str(tmp_path), "python")
        assert findings and findings[0][0] == "dirty.py"
        # Kommentar-Dekoys sind immun (Code-View ohne Kommentare)
        (tmp_path / "dirty.py").unlink()
        (tmp_path / "clean.py").write_text(
            "# random im Kommentar, uuid4 im Kommentar\nprint('ok')\n",
            encoding="utf-8",
        )
        assert m.scan_sources(str(tmp_path), "python") == []
        # String-Literale zaehlen als Quellcode-Fund (Token-Ansicht enthaelt sie)
        (tmp_path / "clean.py").write_text("s = 'uuid4 als String'\n", encoding="utf-8")
        assert m.scan_sources(str(tmp_path), "python") != []

    def test_run_tests_and_normalize_output(self, tmp_path):
        m = load(DET)
        out = m.run_tests(
            "python3 -c \"print('ok in 0.42s')\"",
            str(tmp_path),
        )
        assert b"ok" in out
        assert b"in Xs" in out  # Laufzeit normalisiert
        # byte-identisch bei zweitem Lauf (REQ-ENG-012)
        out2 = m.run_tests(
            "python3 -c \"print('ok in 9.99s')\"",
            str(tmp_path),
        )
        assert out == out2
        raw = m.normalize_output(b"3 passed in 1.23s")
        assert raw == b"3 passed in Xs"

    def test_main_smoke_clean_and_dirty(self, tmp_path):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, DET), "--lang", "python"],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        (tmp_path / "dirty.py").write_text("import random\n", encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, DET), "--lang", "python"],
            capture_output=True, text=True, cwd=str(tmp_path),
        )
        assert proc.returncode != 0  # fail-closed bei Verstoß


# --------------------------------------------------- ci_independent_audit.py
class TestCiIndependentAudit:
    def test_read_fail_files(self):
        m = load(AUD)
        text = m.read(m.ROOT / "README.md")
        assert text and "ATC" in text or "atc" in text.lower()
        findings = []
        m.fail(findings, "F-TEST-001: fixture finding")
        assert findings == ["F-TEST-001: fixture finding"]
        repo_files = m.files()
        assert any(f.name == "README.md" for f in repo_files)

    def test_audit_functions_run_on_repo(self):
        m = load(AUD)
        calls = [
            m.audit_metadata,
            m.audit_workflows,
            m.audit_security_and_determinism,
            m.audit_placeholders_and_docs,
            m.audit_evidence,
            m.audit_inventory,
            m.audit_duplicates,
        ]
        findings = []
        for fn in calls:
            fn(findings)  # jede Audit-Funktion laeuft durch und produziert str-Findings
        assert isinstance(findings, list)
        assert all(isinstance(f, str) for f in findings)

    def test_main_smoke(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(REPO, AUD)],
            capture_output=True,
            text=True,
            cwd=REPO,
        )
        assert proc.returncode in (0, 1), proc.stdout + proc.stderr
        assert "Findings:" in proc.stdout
