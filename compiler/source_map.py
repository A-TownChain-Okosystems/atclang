atclang/compiler/source_map.py

Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.

All Rights Reserved.

"""
ATCLang Source Map

Mapping zwischen ATCLang-Quellcode und generiertem ATC-Bytecode.

Verantwortlichkeiten:
- Bytecode-IP → Source Location
- Source Location → Bytecode-IP
- effiziente Lookup-Operationen
- Fehler-/Runtime-Diagnostik
- Serialisierung für Debugger und Tooling

Das Modul enthält bewusst keine Compilerlogik.

Format einer Source Location:
file_id
line
column
optional end_line / end_column

ATC-92 / ATCLang Compiler
"""

from future import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

══════════════════════════════════════════════════════════════════════════════

SOURCE LOCATION

══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class SourceLocation:
"""Position eines AST-/Bytecode-Elements im Quelltext."""

file_id: str = "<memory>"
line: int = 0
column: int = 0
end_line: Optional[int] = None
end_column: Optional[int] = None

def __post_init__(self) -> None:
    if self.line < 0:
        raise ValueError("line must be >= 0")
    if self.column < 0:
        raise ValueError("column must be >= 0")

    if self.end_line is not None and self.end_line < self.line:
        raise ValueError("end_line must be >= line")

    if (
        self.end_line is not None
        and self.end_line == self.line
        and self.end_column is not None
        and self.end_column < self.column
    ):
        raise ValueError("end_column must be >= column")

def as_tuple(self) -> Tuple[str, int, int]:
    """Legacy-kompatible Darstellung."""
    return self.file_id, self.line, self.column

def to_dict(self) -> Dict[str, Any]:
    return {
        "file_id": self.file_id,
        "line": self.line,
        "column": self.column,
        "end_line": self.end_line,
        "end_column": self.end_column,
    }

@classmethod
def from_dict(cls, data: Mapping[str, Any]) -> "SourceLocation":
    return cls(
        file_id=str(data.get("file_id", "<memory>")),
        line=int(data.get("line", 0)),
        column=int(data.get("column", 0)),
        end_line=(
            None
            if data.get("end_line") is None
            else int(data["end_line"])
        ),
        end_column=(
            None
            if data.get("end_column") is None
            else int(data["end_column"])
        ),
    )

def __str__(self) -> str:
    return f"{self.file_id}:{self.line}:{self.column}"

══════════════════════════════════════════════════════════════════════════════

SOURCE MAP ENTRY

══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class SourceMapEntry:
"""Eine Zuordnung von Bytecode-IP zu Source Location."""

ip: int
location: SourceLocation

# Optionaler semantischer Kontext.
# Beispiele:
#   expression
#   statement
#   function
#   contract
#   call
kind: str = ""

# Optionales Symbol, z. B. Funktionsname.
symbol: Optional[str] = None

def __post_init__(self) -> None:
    if self.ip < 0:
        raise ValueError("instruction pointer must be >= 0")

def to_dict(self) -> Dict[str, Any]:
    return {
        "ip": self.ip,
        "location": self.location.to_dict(),
        "kind": self.kind,
        "symbol": self.symbol,
    }

@classmethod
def from_dict(cls, data: Mapping[str, Any]) -> "SourceMapEntry":
    return cls(
        ip=int(data["ip"]),
        location=SourceLocation.from_dict(data["location"]),
        kind=str(data.get("kind", "")),
        symbol=data.get("symbol"),
    )

══════════════════════════════════════════════════════════════════════════════

SOURCE MAP

══════════════════════════════════════════════════════════════════════════════

class SourceMap:
"""
Bidirektionale Source-Map für ATC-Bytecode.

Beispiel:

    source_map.add(0, line=1, column=1)
    source_map.add(1, line=1, column=7)
    source_map.add(2, line=2, column=5)

    loc = source_map.lookup_ip(1)

Die Implementierung hält die Einträge nach IP sortiert und verwendet
binäre Suche für schnelle Runtime-/Debugger-Lookups.
"""

def __init__(
    self,
    entries: Optional[Iterable[SourceMapEntry]] = None,
    *,
    file_id: str = "<memory>",
) -> None:
    self.file_id = file_id
    self._entries: List[SourceMapEntry] = []
    self._ips: List[int] = []

    if entries:
        self.extend(entries)

# ──────────────────────────────────────────────────────────────────────
# Properties
# ──────────────────────────────────────────────────────────────────────

@property
def entries(self) -> Sequence[SourceMapEntry]:
    """Read-only Sicht auf die Source-Map."""
    return tuple(self._entries)

def __len__(self) -> int:
    return len(self._entries)

def __bool__(self) -> bool:
    return bool(self._entries)

def __iter__(self) -> Iterator[SourceMapEntry]:
    return iter(self._entries)

# ──────────────────────────────────────────────────────────────────────
# Add / Build
# ──────────────────────────────────────────────────────────────────────

def add(
    self,
    ip: int,
    line: int,
    column: int = 0,
    *,
    file_id: Optional[str] = None,
    end_line: Optional[int] = None,
    end_column: Optional[int] = None,
    kind: str = "",
    symbol: Optional[str] = None,
) -> SourceMapEntry:
    """
    Fügt eine Source-Map-Zuordnung hinzu.

    Existiert bereits ein Eintrag für dieselbe IP, wird dieser ersetzt.
    """

    location = SourceLocation(
        file_id=file_id if file_id is not None else self.file_id,
        line=line,
        column=column,
        end_line=end_line,
        end_column=end_column,
    )

    entry = SourceMapEntry(
        ip=ip,
        location=location,
        kind=kind,
        symbol=symbol,
    )

    self._insert_or_replace(entry)
    return entry

def add_location(
    self,
    ip: int,
    location: SourceLocation,
    *,
    kind: str = "",
    symbol: Optional[str] = None,
) -> SourceMapEntry:
    """Fügt eine vorhandene SourceLocation hinzu."""

    entry = SourceMapEntry(
        ip=ip,
        location=location,
        kind=kind,
        symbol=symbol,
    )

    self._insert_or_replace(entry)
    return entry

def extend(self, entries: Iterable[SourceMapEntry]) -> None:
    """Fügt mehrere Entries hinzu und sortiert sie anschließend."""

    for entry in entries:
        if not isinstance(entry, SourceMapEntry):
            raise TypeError(
                "SourceMap entries must be SourceMapEntry instances"
            )

        self._insert_or_replace(entry)

def _insert_or_replace(self, entry: SourceMapEntry) -> None:
    pos = bisect_right(self._ips, entry.ip)

    # Existing IP.
    if pos > 0 and self._ips[pos - 1] == entry.ip:
        self._entries[pos - 1] = entry
        return

    self._ips.insert(pos, entry.ip)
    self._entries.insert(pos, entry)

# ──────────────────────────────────────────────────────────────────────
# Lookup
# ──────────────────────────────────────────────────────────────────────

def lookup_ip(
    self,
    ip: int,
    *,
    exact: bool = False,
) -> Optional[SourceMapEntry]:
    """
    Ermittelt die Source-Position für eine Bytecode-IP.

    exact=False:
        Liefert den letzten bekannten Mapping-Eintrag <= IP.

    exact=True:
        Liefert nur einen exakten Treffer.
    """

    if not self._entries:
        return None

    pos = bisect_right(self._ips, ip)

    if pos == 0:
        return None

    entry = self._entries[pos - 1]

    if exact and entry.ip != ip:
        return None

    return entry

def location_for_ip(
    self,
    ip: int,
    *,
    exact: bool = False,
) -> Optional[SourceLocation]:
    """Convenience-Lookup: IP → SourceLocation."""

    entry = self.lookup_ip(ip, exact=exact)
    return entry.location if entry else None

def ips_for_location(
    self,
    line: int,
    column: Optional[int] = None,
    *,
    file_id: Optional[str] = None,
) -> List[int]:
    """
    Source → Bytecode.

    Liefert alle Bytecode-IPs, die zur angegebenen Source-Position
    gehören.
    """

    result: List[int] = []

    for entry in self._entries:
        loc = entry.location

        if file_id is not None and loc.file_id != file_id:
            continue

        if loc.line != line:
            continue

        if column is not None and loc.column != column:
            continue

        result.append(entry.ip)

    return result

def entries_for_line(
    self,
    line: int,
    *,
    file_id: Optional[str] = None,
) -> List[SourceMapEntry]:
    """Alle Mapping-Einträge einer Source-Zeile."""

    return [
        entry
        for entry in self._entries
        if entry.location.line == line
        and (
            file_id is None
            or entry.location.file_id == file_id
        )
    ]

# ──────────────────────────────────────────────────────────────────────
# Compiler compatibility
# ──────────────────────────────────────────────────────────────────────

def append_legacy(
    self,
    ip: int,
    line: int,
    column: int = 0,
) -> None:
    """
    Kompatibilität für das bisherige Compilerformat:

        List[Tuple[int, int, int]]

    entspricht:

        (instruction_index, line, column)
    """

    self.add(ip, line, column)

def to_legacy(self) -> List[Tuple[int, int, int]]:
    """Konvertiert die Source-Map in das bisherige Tuple-Format."""

    return [
        (
            entry.ip,
            entry.location.line,
            entry.location.column,
        )
        for entry in self._entries
    ]

# ──────────────────────────────────────────────────────────────────────
# Transformations
# ──────────────────────────────────────────────────────────────────────

def remap(
    self,
    old_to_new: Mapping[int, int],
) -> "SourceMap":
    """
    Erzeugt eine neue Source-Map nach Bytecode-Reindexierung.

    Wichtig für Optimizer-Pässe, die Instructions entfernen oder
    verschieben.
    """

    result = SourceMap(file_id=self.file_id)

    for entry in self._entries:
        new_ip = old_to_new.get(entry.ip)

        if new_ip is None:
            continue

        result.add_location(
            new_ip,
            entry.location,
            kind=entry.kind,
            symbol=entry.symbol,
        )

    return result

def merge(
    self,
    other: "SourceMap",
    *,
    ip_offset: int = 0,
) -> "SourceMap":
    """
    Kombiniert zwei Source Maps.

    Wird insbesondere für Function-/Module-Code hilfreich.
    """

    result = SourceMap(file_id=self.file_id)

    result.extend(self._entries)

    for entry in other:
        result.add_location(
            entry.ip + ip_offset,
            entry.location,
            kind=entry.kind,
            symbol=entry.symbol,
        )

    return result

# ──────────────────────────────────────────────────────────────────────
# Serialization
# ──────────────────────────────────────────────────────────────────────

def to_list(self) -> List[Dict[str, Any]]:
    """JSON-kompatible Darstellung."""

    return [entry.to_dict() for entry in self._entries]

def to_dict(self) -> Dict[str, Any]:
    return {
        "version": 1,
        "file_id": self.file_id,
        "entries": self.to_list(),
    }

@classmethod
def from_list(
    cls,
    data: Iterable[Mapping[str, Any]],
    *,
    file_id: str = "<memory>",
) -> "SourceMap":
    result = cls(file_id=file_id)

    for item in data:
        result.add_location(
            int(item["ip"]),
            SourceLocation.from_dict(item["location"]),
            kind=str(item.get("kind", "")),
            symbol=item.get("symbol"),
        )

    return result

@classmethod
def from_dict(cls, data: Mapping[str, Any]) -> "SourceMap":
    return cls.from_list(
        data.get("entries", []),
        file_id=str(data.get("file_id", "<memory>")),
    )

# ──────────────────────────────────────────────────────────────────────
# Debugging
# ──────────────────────────────────────────────────────────────────────

def format_ip(self, ip: int) -> str:
    """Menschenlesbare Darstellung einer Bytecode-IP."""

    entry = self.lookup_ip(ip)

    if entry is None:
        return f"<unknown>@ip={ip}"

    suffix = ""

    if entry.symbol:
        suffix = f" [{entry.symbol}]"

    if entry.kind:
        suffix += f" <{entry.kind}>"

    return f"{entry.location}{suffix}"

def dump(self) -> str:
    """Debug-Ausgabe der vollständigen Source-Map."""

    lines = ["=== ATC Source Map ==="]

    for entry in self._entries:
        symbol = f" [{entry.symbol}]" if entry.symbol else ""
        kind = f" <{entry.kind}>" if entry.kind else ""

        lines.append(
            f"  {entry.ip:04d} → "
            f"{entry.location}{kind}{symbol}"
        )

    return "\n".join(lines)

══════════════════════════════════════════════════════════════════════════════

COMPILER HELPER

══════════════════════════════════════════════════════════════════════════════

def build_source_map(
entries: Iterable[Tuple[int, int, int]],
*,
file_id: str = "<memory>",
) -> SourceMap:
"""
Erstellt eine SourceMap aus dem bisherigen Compilerformat.

Beispiel:

    [
        (0, 1, 0),
        (1, 1, 5),
        (2, 2, 0),
    ]
"""

source_map = SourceMap(file_id=file_id)

for ip, line, column in entries:
    source_map.add(
        ip,
        line,
        column,
    )

return source_map

══════════════════════════════════════════════════════════════════════════════

PUBLIC API

══════════════════════════════════════════════════════════════════════════════

all = [
"SourceLocation",
"SourceMapEntry",
"SourceMap",
"build_source_map",
]