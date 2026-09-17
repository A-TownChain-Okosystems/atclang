# tools/ — Governance-Werkzeuge

*3 Dateien, 588 Zeilen — AST-generiert*


## `ci_independent_audit.py`
### `tools/ci_independent_audit.py` (302 Zeilen)

> CI-independent ATCLang repository audit.
> 
> The script is deliberately dependency-light so it can run while GitHub Actions
> is unavailable. It enforces the repository's declared ATC profile and checks

- **`def read(path: Path) -> str`** — 
- **`def fail(findings: list[str], finding: str) -> None`** — 
- **`def files() -> list[Path]`** — 
- **`def audit_metadata(findings: list[str]) -> None`** — 
- **`def audit_workflows(findings: list[str]) -> None`** — 
- **`def audit_security_and_determinism(findings: list[str]) -> None`** — 
- **`def audit_placeholders_and_docs(findings: list[str]) -> None`** — 
- **`def audit_evidence(findings: list[str]) -> None`** — SCR-0086-Bindungspruefung (Revision 2026-09-17).
- **`def audit_inventory(findings: list[str]) -> None`** — 
- **`def audit_duplicates(findings: list[str]) -> None`** — 
- **`def main() -> int`** — 


## `determinism_check.py`
### `tools/determinism_check.py` (185 Zeilen)

> ATC Determinism Gate v2 — ATC-STD-ENG-001 REQ-ENG-002 (D-CRITICAL-Repos).
> 
> v2-Verbesserungen gegenueber v1 (SCR-0126):
>   - Saeule 1 tokenize-basiert: nur echte CODE-Tokens werden geprueft —

- **`def load_allowlist(root)`** — 
- **`def code_view_py(path)`** — Liefert je Zeilennummer die 'Code-Ansicht': Tokens ohne Strings/Kommentare.
- **`def code_view_rust(path)`** — Rust: Zeilenkommentare und String-Literale heuristisch entfernen.
- **`def scan_sources(root, lang)`** — 
- **`def run_tests(cmd, cwd)`** — 
- **`def normalize_output(raw)`** — Normalisiert reine Laufzeit-Angaben (z.B. '4 passed in 0.40s').
- **`def main()`** — 


## `dump_reference.py`
### `tools/differential/dump_reference.py` (101 Zeilen)

> SCR-0084 — Differential-Harness: Python-Referenz -> kanonisches AST-JSON.
> Generiert crates/atc-core/differential/expected/*.json aus dem Reference-
> Parser (frontend). Das Rust-Canonical-Core-Testsuite vergleicht bytgleich.

- **`def node_to_obj(n)`** — 
- **`def dump(corpus_dir, expected_dir)`** — 
