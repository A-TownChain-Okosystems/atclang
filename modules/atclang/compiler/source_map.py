# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler Source Map
===========================

Source-Mapping-System des ATCLang Compilers.

Verantwortung
-------------

source_map.py verbindet erzeugten Compiler-/Bytecode-Code mit
Positionen im ursprünglichen ATCLang-Quelltext.

Dependency Rule
---------------

    source_map.py
        ↓
    errors.py

source_map.py darf keine Abhängigkeit auf Compiler-Orchestrator,
Parser, VM oder Optimizer besitzen.

Kanonische Source-Typen
-----------------------

SourceLocation
SourceSpan
CompilerDiagnostic

werden ausschließlich aus errors.py importiert.

Ziele
-----

- Bytecode → Source Mapping
- Instruction → Source Mapping
- Source → Bytecode Lookup
- Debugger-Unterstützung
- Stacktrace-Unterstützung
- LSP/IDE-Unterstützung
- deterministische Serialisierung
- Optimizer-kompatibles Mapping
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

from .errors import (
    CompilerDiagnostic,
    ErrorSeverity,
    SourceLocation,
    SourceSpan,
)


# ═══════════════════════════════════════════════════════════════════════
# SOURCE MAP ENTRY
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SourceMapEntry:
    """
    Mapping eines Bytecode-Bereichs auf einen Source-Bereich.

    bytecode_start:
        Erste Instruction des Mappings.

    bytecode_end:
        Exklusives Ende des Bytecode-Bereichs.

    span:
        Zugehöriger Bereich im ATCLang-Quelltext.

    Beispiel:

        Bytecode [10, 14)
            ↓
        Source line 8, columns 5-17
    """

    bytecode_start: int
    bytecode_end: int
    span: SourceSpan

    def __post_init__(self) -> None:
        if self.bytecode_start < 0:
            raise ValueError(
                "bytecode_start darf nicht negativ sein"
            )

        if self.bytecode_end < self.bytecode_start:
            raise ValueError(
                "bytecode_end darf nicht kleiner als bytecode_start sein"
            )

    @property
    def length(self) -> int:
        """Anzahl der gemappten Bytecode-Instructions."""

        return self.bytecode_end - self.bytecode_start

    def contains_bytecode(self, offset: int) -> bool:
        """Prüft, ob ein Bytecode-Offset im Mapping liegt."""

        return (
            self.bytecode_start
            <= offset
            < self.bytecode_end
        )


# ═══════════════════════════════════════════════════════════════════════
# SOURCE MAP
# ═══════════════════════════════════════════════════════════════════════


class SourceMap:
    """
    Zentrale Source-Map eines kompilierten Moduls.

    Unterstützte Richtungen:

        Bytecode → Source
        Source → Bytecode

    Die Einträge werden bei der Ausgabe deterministisch
    nach Bytecode-Offset sortiert.
    """

    def __init__(self) -> None:
        self._entries: List[SourceMapEntry] = []

    # ────────────────────────────────────────────────────────────────
    # INSERT
    # ────────────────────────────────────────────────────────────────

    def add(
        self,
        bytecode_start: int,
        bytecode_end: int,
        span: SourceSpan,
    ) -> SourceMapEntry:
        """
        Fügt einen Source-Map-Eintrag hinzu.
        """

        entry = SourceMapEntry(
            bytecode_start=bytecode_start,
            bytecode_end=bytecode_end,
            span=span,
        )

        self._entries.append(entry)

        return entry

    def add_instruction(
        self,
        instruction_offset: int,
        span: SourceSpan,
    ) -> SourceMapEntry:
        """
        Fügt ein Mapping für genau eine Instruction hinzu.
        """

        return self.add(
            instruction_offset,
            instruction_offset + 1,
            span,
        )

    # ────────────────────────────────────────────────────────────────
    # LOOKUP: BYTECODE → SOURCE
    # ────────────────────────────────────────────────────────────────

    def lookup(
        self,
        bytecode_offset: int,
    ) -> Optional[SourceMapEntry]:
        """
        Liefert den Source-Map-Eintrag für einen Bytecode-Offset.

        Die Suche erfolgt von hinten, da neu erzeugte Einträge
        typischerweise die aktuellsten Informationen enthalten.
        """

        if bytecode_offset < 0:
            return None

        for entry in reversed(self._entries):
            if entry.contains_bytecode(bytecode_offset):
                return entry

        return None

    def lookup_span(
        self,
        bytecode_offset: int,
    ) -> Optional[SourceSpan]:
        """
        Liefert direkt den SourceSpan eines Bytecode-Offsets.
        """

        entry = self.lookup(bytecode_offset)

        if entry is None:
            return None

        return entry.span

    def lookup_location(
        self,
        bytecode_offset: int,
    ) -> Optional[SourceLocation]:
        """
        Liefert die Startposition des zugehörigen Source-Bereichs.
        """

        span = self.lookup_span(bytecode_offset)

        if span is None:
            return None

        return span.start

    # ────────────────────────────────────────────────────────────────
    # LOOKUP: SOURCE → BYTECODE
    # ────────────────────────────────────────────────────────────────

    def lookup_source(
        self,
        line: int,
        column: int = 0,
    ) -> List[SourceMapEntry]:
        """
        Liefert alle Bytecode-Einträge, die zu einer Source-Position
        gehören.

        Unbekannte Spaltenpositionen (column == 0) werden tolerant
        behandelt.
        """

        if line < 0 or column < 0:
            return []

        result: List[SourceMapEntry] = []

        for entry in self._entries:
            span = entry.span
            start = span.start
            end = span.end

            if start.line == 0:
                continue

            if end is None:
                if start.line == line:
                    result.append(entry)

                continue

            if self._position_in_span(
                line,
                column,
                span,
            ):
                result.append(entry)

        return result

    def lookup_line(
        self,
        line: int,
    ) -> List[SourceMapEntry]:
        """
        Liefert alle Mappings für eine Source-Zeile.
        """

        return self.lookup_source(line)

    # ────────────────────────────────────────────────────────────────
    # POSITION TEST
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _position_in_span(
        line: int,
        column: int,
        span: SourceSpan,
    ) -> bool:
        """
        Prüft, ob eine Source-Position innerhalb eines SourceSpans liegt.

        Die Grenzen werden inklusiv behandelt.
        """

        start = span.start
        end = span.end

        if line < start.line:
            return False

        if end is not None and line > end.line:
            return False

        # Startposition.
        if line == start.line:
            if (
                column > 0
                and start.column > 0
                and column < start.column
            ):
                return False

        # Endposition.
        if end is not None and line == end.line:
            if (
                column > 0
                and end.column > 0
                and column > end.column
            ):
                return False

        return True

    # ═══════════════════════════════════════════════════════════════
    # NORMALIZATION
    # ═══════════════════════════════════════════════════════════════

    def normalize(self) -> None:
        """
        Sortiert und konsolidiert die Source Map.

        Direkt angrenzende Einträge mit identischem SourceSpan
        werden zusammengeführt.
        """

        if not self._entries:
            return

        entries = sorted(
            self._entries,
            key=lambda entry: (
                entry.bytecode_start,
                entry.bytecode_end,
            ),
        )

        merged: List[SourceMapEntry] = []

        for entry in entries:
            if not merged:
                merged.append(entry)
                continue

            previous = merged[-1]

            if (
                previous.bytecode_end
                == entry.bytecode_start
                and previous.span == entry.span
            ):
                merged[-1] = SourceMapEntry(
                    bytecode_start=previous.bytecode_start,
                    bytecode_end=entry.bytecode_end,
                    span=previous.span,
                )
            else:
                merged.append(entry)

        self._entries = merged

    # ═══════════════════════════════════════════════════════════════
    # BYTECODE REINDEXING
    # ═══════════════════════════════════════════════════════════════

    def remap_offsets(
        self,
        old_to_new: Dict[int, int],
    ) -> None:
        """
        Aktualisiert Bytecode-Offsets nach einer Transformation.

        old_to_new:

            alter Offset → neuer Offset

        Einträge, deren Startposition nicht mehr existiert,
        werden verworfen.
        """

        new_entries: List[SourceMapEntry] = []

        for entry in self._entries:
            if entry.bytecode_start not in old_to_new:
                continue

            new_start = old_to_new[entry.bytecode_start]

            if entry.bytecode_end > entry.bytecode_start:
                last_old = entry.bytecode_end - 1

                if last_old in old_to_new:
                    new_end = old_to_new[last_old] + 1
                else:
                    new_end = new_start + 1
            else:
                new_end = new_start

            if new_end < new_start:
                new_end = new_start

            new_entries.append(
                SourceMapEntry(
                    bytecode_start=new_start,
                    bytecode_end=new_end,
                    span=entry.span,
                )
            )

        self._entries = new_entries
        self.normalize()

    # ═══════════════════════════════════════════════════════════════
    # ITERATION
    # ═══════════════════════════════════════════════════════════════

    @property
    def entries(self) -> Tuple[SourceMapEntry, ...]:
        """
        Read-only Sicht auf die Source-Map-Einträge.

        Die Einträge sind deterministisch nach Startoffset sortiert.
        """

        return tuple(
            sorted(
                self._entries,
                key=lambda entry: (
                    entry.bytecode_start,
                    entry.bytecode_end,
                ),
            )
        )

    def __iter__(self) -> Iterable[SourceMapEntry]:
        return iter(self.entries)

    def __len__(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        """Entfernt alle Source-Map-Einträge."""

        self._entries.clear()

    # ═══════════════════════════════════════════════════════════════
    # DIAGNOSTICS
    # ═══════════════════════════════════════════════════════════════

    def diagnostic(
        self,
        code: str,
        message: str,
        *,
        bytecode_offset: Optional[int] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        hint: Optional[str] = None,
        note: Optional[str] = None,
    ) -> CompilerDiagnostic:
        """
        Erstellt eine CompilerDiagnostic mit Source-Mapping.

        Wenn bytecode_offset angegeben ist, wird automatisch
        der zugehörige SourceSpan verwendet.
        """

        span: Optional[SourceSpan] = None

        if bytecode_offset is not None:
            span = self.lookup_span(bytecode_offset)

        return CompilerDiagnostic(
            code=code,
            message=message,
            severity=severity,
            span=span,
            hint=hint,
            note=note,
        )

    # ═══════════════════════════════════════════════════════════════
    # SERIALIZATION
    # ═══════════════════════════════════════════════════════════════

    def to_dict(self) -> List[dict]:
        """
        Serialisiert die Source Map in eine JSON-kompatible Struktur.
        """

        result: List[dict] = []

        for entry in self.entries:
            start = entry.span.start
            end = entry.span.end

            item = {
                "bytecode_start": entry.bytecode_start,
                "bytecode_end": entry.bytecode_end,
                "start": {
                    "line": start.line,
                    "column": start.column,
                },
            }

            if end is not None:
                item["end"] = {
                    "line": end.line,
                    "column": end.column,
                }

            result.append(item)

        return result

    @classmethod
    def from_dict(
        cls,
        data: Iterable[dict],
    ) -> "SourceMap":
        """
        Erstellt eine SourceMap aus einer JSON-kompatiblen Struktur.
        """

        source_map = cls()

        for item in data:
            start_data = item.get("start", {})

            start = SourceLocation(
                line=int(start_data.get("line", 0)),
                column=int(start_data.get("column", 0)),
            )

            end_data = item.get("end")

            end: Optional[SourceLocation] = None

            if end_data is not None:
                end = SourceLocation(
                    line=int(
                        end_data.get(
                            "line",
                            start.line,
                        )
                    ),
                    column=int(
                        end_data.get(
                            "column",
                            0,
                        )
                    ),
                )

            span = SourceSpan(
                start=start,
                end=end,
            )

            source_map.add(
                int(item.get("bytecode_start", 0)),
                int(item.get("bytecode_end", 0)),
                span,
            )

        source_map.normalize()

        return source_map


# ═══════════════════════════════════════════════════════════════════════
# SOURCE MAP BUILDER
# ═══════════════════════════════════════════════════════════════════════


class SourceMapBuilder:
    """
    Convenience-Builder für den Compiler.

    Der Builder ermöglicht es Compiler-Komponenten, während des
    Lowerings Source-Mappings aufzubauen.
    """

    def __init__(self) -> None:
        self._map = SourceMap()

    def mark(
        self,
        bytecode_offset: int,
        span: SourceSpan,
    ) -> None:
        """
        Markiert eine einzelne Instruction.
        """

        self._map.add_instruction(
            bytecode_offset,
            span,
        )

    def mark_range(
        self,
        bytecode_start: int,
        bytecode_end: int,
        span: SourceSpan,
    ) -> None:
        """
        Markiert einen Bytecode-Bereich.
        """

        self._map.add(
            bytecode_start,
            bytecode_end,
            span,
        )

    def mark_node(
        self,
        bytecode_offset: int,
        node: object,
    ) -> None:
        """
        Markiert eine Instruction anhand eines AST-Nodes.

        Der Node muss line/column bzw. line/col bereitstellen.
        """

        span = SourceSpan.from_node(node)

        self.mark(
            bytecode_offset,
            span,
        )

    def build(self) -> SourceMap:
        """
        Erstellt die finale SourceMap.

        Die Map wird vor der Rückgabe normalisiert.
        """

        self._map.normalize()

        return self._map


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════


__all__ = [
    "SourceMapEntry",
    "SourceMap",
    "SourceMapBuilder",
]


__version__ = "0.3.0"