#!/usr/bin/env python3
"""ATC Determinism Gate — ATC-STD-ENG-001 REQ-ENG-002 (D-CRITICAL-Repos).

Prüft zwei Determinismus-Säulen:
  1. VERBOTENE QUELLEN: Wall-Clock / RNG im Quellcode (Sprachmuster je --lang)
  2. REPRODUIERBARE TESTS: Testsuite zweimal, Byte-Vergleich der Ausgaben

Fail-closed: Exit 0 nur wenn BEIDE Säulen grün sind (REQ-ENG-012 — Evidenz
ist der zweimalige identische Testlauf, kein synthetischer Nachweis).

Aufruf: python3 tools/determinism_check.py --lang rust|python [--test-cmd "..."]
"""
import argparse, os, re, subprocess, sys

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
        (r"time\.time\(\)", "Wall-Clock"),
        (r"datetime\.now\b", "Wall-Clock (datetime)"),
        (r"datetime\.utcnow\b", "Wall-Clock (utcnow)"),
        (r"uuid4", "Zufalls-UUIDs"),
    ],
}
EXT = {"rust": ".rs", "python": ".py"}
SKIP_DIRS = {"target", "node_modules", ".git", ".github", "tests", "docs", "examples", "tools/determinism_check.py"}

def scan_sources(root, lang):
    findings = []
    ext = EXT[lang]
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(ext):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        for pat, desc in PATTERNS[lang]:
                            if re.search(pat, line):
                                findings.append(f"{path}:{i}: {desc}: {line.strip()[:80]}")
            except (OSError, UnicodeDecodeError):
                continue
    return findings

def run_tests(cmd, cwd):
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return (r.returncode, (r.stdout or "") + (r.stderr or ""))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["rust", "python"], required=True)
    ap.add_argument("--test-cmd", default=None)
    ap.add_argument("--skip-tests", action="store_true", help="nur Quellcode-Scan (nicht empfohlen)")
    args = ap.parse_args()

    root = os.getcwd()
    ok = True

    print("== Saeule 1: Verbotene Nichtdeterminismus-Quellen ==")
    findings = scan_sources(root, args.lang)
    if findings:
        ok = False
        for f in findings[:20]:
            print(f"  FINDING {f}")
        print(f"  => {len(findings)} Fundstelle(n) — FAIL (REQ-ENG-002)")
    else:
        print("  OK: keine Wall-Clock/RNG-Fundstellen im Quellcode")

    if not args.skip_tests:
        print("== Saeule 2: Reproduzierbare Testlaeufe (2x, Byte-Vergleich) ==")
        cmd = args.test_cmd or ("cargo test --quiet" if args.lang == "rust" else "python3 -m pytest -q 2>/dev/null || python3 -m unittest discover -q")
        rc1, out1 = run_tests(cmd, root)
        rc2, out2 = run_tests(cmd, root)
        if rc1 != 0 or rc2 != 0:
            ok = False
            print(f"  FINDING: Tests schlagen fehl (rc={rc1}/{rc2}) — Determinismus nicht pruefbar (Fail Closed)")
        elif out1 != out2:
            ok = False
            print("  FINDING: Testausgaben unterscheiden sich zwischen Lauf 1 und Lauf 2 — nichtdeterministisch!")
        else:
            print("  OK: zwei identische Testlaeufe (Evidenz per Byte-Vergleich)")

    print("DETERMINISM GATE:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
