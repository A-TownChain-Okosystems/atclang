---
document_id: ATC-DOC-LANG-002
title: ATCLang Contributing Guidelines
version: 1.0.0
status: active
owner: A-TownChain-Okosystems
created: 2026-09-07
updated: 2026-09-07
standard: ATC-STD-MD-001
---

## Contributing to ATCLang

Beiträge zur ATCLang-Entwicklung folgen den Richtlinien des A-TownChain-Ökosystems.

## Entwicklungsrichtlinien

- **Erweiterungen:** Die aktive Produktionsimplementierung liegt in `crates/atc-core/`. Lexer, Parser, Lowering, Bytecode, Artefakte und Laufzeit sind anhand des aktuellen Rust-Codes zu ändern. Keine neue Produktions-VM neben `a-townchain/components/vm` einführen. Historische Python-Pfade sind keine gültigen Implementierungsziele.
- **Tests:** Jede Änderung erfordert passende Rust-Unit- und Integrationstests unter `crates/atc-core/`; bei Sprach-/Bytecode-Änderungen sind Differential-Korpus, Negativtests und kanonische Conformance-Vektoren zu prüfen.
- **Commits:** Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`).
- **Katalog:** `docs/COMPONENT_FUNCTION_CATALOG.md` ist der Einstiegspunkt für Komponenten, öffentliche Funktionen, Testflächen und offene Vollständigkeitslücken. Vor Änderungen Quelle und aktuelle SHA prüfen; Implementierung und Verifikation getrennt dokumentieren.
- **Standards:** Code und Dokumentation müssen allen anwendbaren ATC-Standards entsprechen.
