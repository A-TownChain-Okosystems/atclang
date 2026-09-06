# ATCLang — A-TownChain Systemsprache (1.0 REBUILD)

ATCLang ist die proprietäre System- und Contract-Sprache der A-TownChain: Lexer, Parser, Type-Checker, Compiler, Bytecode, ATVM, Runtime, ABI, Stdlib — von Grund auf eigenständig, kein POSIX-Klon.

**Rebuild-Status (06.09.2026, AD-019):** Phase-1-Konsolidierung abgeschlossen — eine Implementierung je Verantwortlichkeit unter src/atclang/ (Frontend, Compiler, VM, Runtime, Stdlib verifiziert; 22.617 LOC). Zielarchitektur 1.0: docs/ATCLANG_1.0_ARCHITECTURE.md (ARCHITECTURE FREEZE: GO). Subsystem-Implementierungen und Conformance: Phase 2.

    pip install -e . && python -m pytest    # Pipeline-Check
    python -c "from atclang.compiler.compiler import compile_source; compile_source('let x = 1;')"

Architekturzentren: src/ (Implementierung) · specs/ (normativ) · docs/ (erklärend) · tests/ (mit Fixtures) · examples/ · tools/. Keine zweite VM, keine zweite Stdlib, kein zweiter Parser.
