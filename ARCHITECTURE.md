# 🌳 Architektur — atclang

> **Stand:** 2026-08-06 | **Commit:** ceed038
> **Teil von:** [A-TownChain Ökosystem](https://github.com/A-TownChain-Okosystems)

## Statistik

| Metrik | Wert |
|--------|------|
| Dateien | 27 |
| Zeilen | 5,417 |
| .atc | 6 |
| .py | 11 |
| .rs | 0 |
| .ts/.tsx | 0 |
| .md | 7 |

## Verzeichnisstruktur

```
├── atclang/ (1 files, 180 lines)
│   └── main.atc (180 lines)
├── compiler/ (3 files, 1,691 lines)
│   ├── compiler.py (626 lines)
│   ├── optimizer.py (558 lines)
│   └── type_checker.py (507 lines)
├── lexer/ (1 files, 563 lines)
│   └── lexer.py (563 lines)
├── parser/ (2 files, 791 lines)
│   ├── ast_nodes.py (392 lines)
│   └── parser.py (399 lines)
├── programs/ (5 files, 490 lines)
│   ├── atc8300.atc (96 lines)
│   ├── atcos_main.atc (9 lines)
│   ├── event_bus.atc (75 lines)
│   ├── kernel.atc (148 lines)
│   └── shivamon.atc (162 lines)
├── runtime/ (2 files, 1,131 lines)
│   ├── driver_framework.py (506 lines)
│   └── kernel_runtime.py (625 lines)
├── .gitignore
├── ATCLANG_SPEC.md (31 lines)
├── CHANGELOG.md (13 lines)
├── CONTRIBUTING.md (19 lines)
├── FILE_REGISTER.md (39 lines)
├── LICENSE
├── README.md (117 lines)
├── ROADMAP.md (21 lines)
├── STATUS.md (19 lines)
├── compiler.py (102 lines)
├── lexer.py (115 lines)
├── parser.py (95 lines)
└── requirements.txt
```

---
*Auto-generiert 2026-08-06 · Aurora (MasterBrain · Base44)*
