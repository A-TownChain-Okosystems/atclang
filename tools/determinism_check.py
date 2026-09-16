#!/usr/bin/env python3
"""ATC Determinism Gate — ATC-STD-ENG-001 REQ-ENG-002."""

import argparse
import difflib
import os
import re
import subprocess
import sys

PATTERNS = {
    "rust": [
        (r"SystemTime::now\s*\(", "Wall-Clock im Quellcode"),
        (r"Instant::now\s*\(", "Monotonic-Clock im Quellcode"),
        (r"\brand::thread_rng\s*\(", "thread-local RNG"),
        (r"\brand::random\s*\(", "RNG im Quellcode"),
        (r"OsRng\b|StdRng::from_entropy\s*\(", "entropy-basierte RNG-Seeds"),
    ],
    "python": [
        (r"^\s*(?:import\s+random|from\s+random\s+import)\b", "random-Modul"),
        (r"\brandom\.(?:random|randint|randrange|choice|choices|shuffle|sample)\s*\(", "RNG-Aufruf"),
        (r"\bsecrets\.(?:token_bytes|token_hex|token_urlsafe|randbelow|randbits)\s*\(", "OS-Entropy-RNG"),
        (r"\bos\.urandom\s*\(", "OS-Entropy-RNG"),
        (r"\btime\.time\s*\(\)", "Wall-Clock"),
        (r"\bdatetime\.now\s*\(", "Wall-Clock (datetime)"),
        (r"\bdatetime\.utcnow\s*\(", "Wall-Clock (utcnow)"),
        (r"\buuid\.uuid4\s*\(\)|\buuid4\s*\(", "Zufalls-UUID"),
    ],
}
EXT = {"rust": ".rs", "python": ".py"}
SKIP_DIRS = {"target", "node_modules", ".git", ".github", "tests", "docs", "examples"}
SKIP_FILES = {
    "tools/determinism_check.py",
    "src/atclang/security/static_analysis.py",
}
# Python runtime is an explicit host/integration layer, not consensus execution.
# It is audited separately for its boundary contract; host telemetry may use a
# wall clock but must never be consumed by the canonical Rust execution path.
HOST_ONLY_DIRS = {"src/atclang/runtime"}


def _relative(path: str, root: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def scan_sources(root, lang):
    findings = []
    ext = EXT[lang]
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(ext):
                continue
            path = os.path.join(dirpath, fn)
            relative_path = _relative(path, root)
            if relative_path in SKIP_FILES or any(
                relative_path == directory or relative_path.startswith(directory + "/")
                for directory in HOST_ONLY_DIRS
            ):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    for i, line in enumerate(f, 1):
                        for pat, desc in PATTERNS[lang]:
                            if re.search(pat, line):
                                findings.append(f"{relative_path}:{i}: {desc}: {line.strip()[:120]}")
            except (OSError, UnicodeDecodeError):
                continue
    return findings


def run_tests(cmd, cwd):
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", choices=["rust", "python"], required=True)
    ap.add_argument("--test-cmd", default=None)
    ap.add_argument("--skip-tests", action="store_true", help="nur Quellcode-Scan (nicht empfohlen)")
    args = ap.parse_args()

    root = os.getcwd()
    ok = True

    print("== Saeule 1: Verbotene Host-Nichtdeterminismus-Quellen ==")
    findings = scan_sources(root, args.lang)
    if findings:
        ok = False
        for finding in findings[:20]:
            print(f"  FINDING {finding}")
        print(f"  => {len(findings)} Fundstelle(n) — FAIL (REQ-ENG-002)")
    else:
        print("  OK: keine verbotenen Host-Clock/Entropy-Fundstellen im Consensus-Produktquellcode")

    if not args.skip_tests:
        print("== Saeule 2: Reproduzierbare Testlaeufe (2x, Byte-Vergleich) ==")
        cmd = args.test_cmd or (
            "cargo test --quiet"
            if args.lang == "rust"
            else "python3 -m pytest -q 2>/dev/null || python3 -m unittest discover -q"
        )
        rc1, out1 = run_tests(cmd, root)
        rc2, out2 = run_tests(cmd, root)
        if rc1 != 0 or rc2 != 0:
            ok = False
            print(f"  FINDING: Tests schlagen fehl (rc={rc1}/{rc2}) — Determinismus nicht pruefbar (Fail Closed)")
        elif out1 != out2:
            ok = False
            print("  FINDING: Testausgaben unterscheiden sich zwischen Lauf 1 und Lauf 2 — nichtdeterministisch!")
            diff = list(difflib.unified_diff(out1.splitlines(), out2.splitlines(), fromfile="run-1", tofile="run-2", lineterm=""))
            for line in diff[:40]:
                print(f"  {line}")
        else:
            print("  OK: zwei identische Testlaeufe (Evidenz per Byte-Vergleich)")

    print("DETERMINISM GATE:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
