# Contributing to ATCLang

Bitte zuerst [A-TownChain CONTRIBUTING.md](https://github.com/A-TownChain-Okosystems/a-townchain-os/blob/main/docs/CONTRIBUTING.md) lesen.

## ATCLang-spezifisch
- Neue Opcodes: in `atclang/vm/atcvm.py` + Tests in `tests/`
- Neue Token-Typen: in `atclang/lexer/lexer.py` + AST-Nodes
- Neue Stdlib-Funktionen: in `atclang/stdlib/atc_stdlib.py`
- Security-Regeln: in `atclang/security/analyzer.py`

## Security Analyzer erweitern
```python
# Neue Regel in _check_line() einfügen:
if re.search(r'mein_pattern', stripped):
    self._add(SecurityIssue(
        HIGH, "ATC-SEC-016", lineno, 0,
        "Titel", "Beschreibung", "Fix-Empfehlung", stripped
    ))
```
