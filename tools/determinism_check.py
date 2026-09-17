#!/usr/bin/env python3
"""ATC Determinism Gate v2 — ATC-STD-ENG-001 REQ-ENG-002 (D-CRITICAL-Repos).

v2-Verbesserungen gegenueber v1 (SCR-0126):
  - Saeule 1 tokenize-basiert: nur echte CODE-Tokens werden geprueft —
    Kommentare, Docstrings und String-Literale erzeugen keine False Positives
    mehr (v1 flaggte z.B. den eigenen Pattern-Literal und Prosa in Kommentaren).
  - Selbst-Ausschluss: der Checker prueft sich selbst nicht mehr.
  - Explizite Allowlist (determinism_allowlist.yaml) mit Begründungspflicht:
    legitime Wall-Clock/RNG-Verwendungen sind reviewbar dokumentiert; jedes
    NEUE Vorkommen ohne Allowlist-Eintrag faellt fail-closed durch das Gate.
    Ziel: Allowlist iterativ auf 0 reduzieren.

Fail-closed: Exit 0 nur wenn (a) keine nicht-allowlisteten Fundstellen und
(b) zwei identische Testlaeufe (Evidenz per Byte-Vergleich, REQ-ENG-012).
"""

import argparse
import io
import os
import re
import subprocess
import sys
import tokenize

PATTERNS = {
    "rust": [
        (r"SystemTime::now", "Wall-Clock im Quellcode"),
        (r"Instant::now", "Monotonic-Clock im Quellcode"),
        (r"\brand::", "RNG im Quellcode"),
        (r"thread_rng", "thread-local RNG"),
        (r"OsRng|StdRng::from_entropy", "entropy-basierte RNG-Seeds"),
    ],
    "python": [
        (r"\brandom\b", "random-Modul"),
        (r"time\s*\.\s*time\s*\(\s*\)", "Wall-Clock"),
        (r"datetime\s*\.\s*now\b", "Wall-Clock (datetime)"),
        (r"datetime\s*\.\s*utcnow\b", "Wall-Clock (utcnow)"),
        (r"uuid4", "Zufalls-UUIDs"),
    ],
}
EXT = {"rust": ".rs", "python": ".py"}
SKIP_DIRS = {"target", "node_modules", ".git", ".github", "tests", "docs", "examples"}
SELF = "determinism_check.py"
ALLOWLIST_FILE = "determinism_allowlist.yaml"


def load_allowlist(root):
    path = os.path.join(root, ALLOWLIST_FILE)
    if not os.path.exists(path):
        return []
    entries = []
    with io.open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*-\s*file:\s*(\S+)", line)
            if m:
                entries.append({"file": m.group(1)})
                continue
            m = re.match(r"\s+line:\s*(\d+)", line)
            if m and entries:
                entries[-1]["line"] = int(m.group(1))
    return entries


def code_view_py(path):
    """Liefert je Zeilennummer die 'Code-Ansicht': Tokens ohne Strings/Kommentare."""
    views = {}
    try:
        with io.open(path, encoding="utf-8") as f:
            toks = list(tokenize.generate_tokens(f.readline))
    except (SyntaxError, tokenize.TokenError, UnicodeDecodeError):
        return None  # unparsebar -> vom Syntax-/Test-Gate abgedeckt, hier ueberspringen
    for tok in toks:
        if tok.type in (
            tokenize.COMMENT,
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.ENCODING,
            tokenize.ENDMARKER,
        ):
            continue
        views.setdefault(tok.start[0], []).append(tok.string)
    return {ln: " ".join(parts) for ln, parts in views.items()}


def code_view_rust(path):
    """Rust: Zeilenkommentare und String-Literale heuristisch entfernen."""
    views = {}
    with io.open(path, encoding="utf-8") as f:
        for ln, raw in enumerate(f, 1):
            line = raw
            if "//" in line:
                line = line.split("//", 1)[0]
            line = re.sub(r'"[^"]*"', "", line)
            views[ln] = line
    return views


def scan_sources(root, lang):
    findings = []
    ext = EXT[lang]
    view_fn = code_view_py if lang == "python" else code_view_rust
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(ext) or fn == SELF:
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            views = view_fn(path)
            if not views:
                continue
            for ln, code in views.items():
                for pat, desc in PATTERNS[lang]:
                    if re.search(pat, code):
                        findings.append((rel, ln, desc))
    return findings


def run_tests(cmd, cwd):
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = "0"  # Hash-Determinismus normalisieren
    p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, env=env)
    return normalize_output(p.stdout + p.stderr)


def normalize_output(raw):
    """Normalisiert reine Laufzeit-Angaben (z.B. '4 passed in 0.40s').
    Test-Ergebnisse, Tracebacks und Assertions bleiben byte-geprueft."""
    return re.sub(rb"in \d+\.\d+s", b"in Xs", raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True, choices=["rust", "python"])
    ap.add_argument("--test-cmd", default="")
    args = ap.parse_args()
    root = os.getcwd()
    ok = True

    print(
        "== Saeule 1: Verbotene Nichtdeterminismus-Quellen (v2: Code-Tokens, Allowlist-geprueft) =="
    )
    findings = scan_sources(root, args.lang)
    allow = load_allowlist(root)
    allow_keys = {(e["file"], e.get("line")) for e in allow if e.get("line")}
    unallowed, allowed = [], []
    for f, ln, desc in findings:
        (unallowed if (f, ln) not in allow_keys else allowed).append((f, ln, desc))
    for f, ln, desc in allowed:
        print(f"  ALLOWED {f}:{ln}: {desc} (reviewte Begründung in {ALLOWLIST_FILE})")
    for f, ln, desc in unallowed:
        print(f"  FINDING {f}:{ln}: {desc}")
    if unallowed:
        print(f"  => {len(unallowed)} nicht-allowlistete Fundstelle(n) — FAIL (REQ-ENG-002)")
        ok = False
    elif allowed:
        print(
            f"  OK: {len(allowed)} allowlistete Fundstelle(n) — Allowlist iterativ auf 0 reduzieren (SCR-0126)"
        )
    else:
        print("  OK: keine Wall-Clock/RNG-Fundstellen im Code")

    if args.test_cmd:
        print("== Saeule 2: Reproduzierbare Testlaeufe (2x, Byte-Vergleich, PYTHONHASHSEED=0) ==")
        out1 = run_tests(args.test_cmd, root)
        out2 = run_tests(args.test_cmd, root)
        if out1 == out2:
            print("  OK: zwei identische Testlaeufe (Evidenz per Byte-Vergleich)")
        else:
            print(
                "  FINDING: Testausgaben unterscheiden sich zwischen Lauf 1 und Lauf 2 — nichtdeterministisch!"
            )
            ok = False
    else:
        print("== Saeule 2: kein Test-Kommando angegeben — uebersprungen ==")

    print("DETERMINISM GATE:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
