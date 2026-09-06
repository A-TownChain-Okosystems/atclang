# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Symbol System
================================

ATC-92 | ATCLang Compiler v0.3.0

Verantwortlichkeit
------------------
Dieses Modul implementiert die statische Symbolverwaltung des Compilers.

Es enthält:

    - Symbol
    - SymbolKind
    - SymbolTable
    - Scope
    - Symbol resolution
    - Child scopes
    - Shadowing detection
    - Duplicate-definition detection

Architektur
-----------

    Parser / AST
          │
          ▼
    TypeChecker
          │
          ▼
    CompilerContext
          │
          ▼
       SymbolTable
          │
          ├── Module scope
          ├── Function scope
          ├── Block scope
          └── Contract scope

Keine Verantwortung für:

    - AST Parsing
    - Type Checking
    - Bytecode Generation
    - VM Execution
    - Runtime Objects
    - Capability Validation

Designziel
----------
Deterministische und typsichere Symbolauflösung ohne implizite globale
Zustände.

Symbol-Indizes sind innerhalb eines Scopes monoton und deterministisch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, Iterator, Optional


# ═══════════════════════════════════════════════════════════════════════
# SYMBOL KIND
# ═══════════════════════════════════════════════════════════════════════

class SymbolKind(str, Enum):
    """
    Semantische Kategorie eines Symbols.

    Die Enum-Werte bleiben kompatibel mit der bisherigen String-basierten
    Compiler-Implementierung.
    """

    LOCAL = "local"
    GLOBAL = "global"
    PARAMETER = "parameter"

    FUNCTION = "function"
    CONTRACT = "contract"
    STATE = "state"

    CONSTANT = "constant"
    TYPE = "type"
    ENUM = "enum"
    ENUM_VARIANT = "enum_variant"
    STRUCT = "struct"

    IMPORT = "import"
    MODULE = "module"

    BUILTIN = "builtin"


# ═══════════════════════════════════════════════════════════════════════
# SYMBOL
# ═══════════════════════════════════════════════════════════════════════

@dataclass(slots=True)
class Symbol:
    """
    Einzelnes Compiler-Symbol.

    Attributes
    ----------
    name:
        Quelltextname des Symbols.

    kind:
        SymbolKind des Symbols.

    index:
        Deterministischer Slot-/Registerindex innerhalb des Definitions-
        Scopes.

    typ:
        Optionaler Typname. Der TypeChecker kann hier entweder einen
        kanonischen String oder einen Type-Identifier hinterlegen.

    mutable:
        Gibt an, ob das Symbol nach seiner Initialisierung verändert
        werden darf.

    exported:
        Gibt an, ob das Symbol Bestandteil der öffentlichen Modul-API ist.

    scope_id:
        Eindeutige ID des Scopes, in dem das Symbol definiert wurde.

    metadata:
        Erweiterbare Compiler-Metadaten.
    """

    name: str
    kind: SymbolKind | str
    index: int

    typ: str = ""
    mutable: bool = True
    exported: bool = False

    scope_id: int = 0
    metadata: Dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.kind, str):
            try:
                self.kind = SymbolKind(self.kind)
            except ValueError:
                # Forward compatibility für neue Compiler-Kategorien.
                pass

    @property
    def is_local(self) -> bool:
        return self.kind in (
            SymbolKind.LOCAL,
            SymbolKind.PARAMETER,
        )

    @property
    def is_global(self) -> bool:
        return self.kind == SymbolKind.GLOBAL

    @property
    def is_function(self) -> bool:
        return self.kind == SymbolKind.FUNCTION

    @property
    def is_state(self) -> bool:
        return self.kind == SymbolKind.STATE

    @property
    def is_constant(self) -> bool:
        return self.kind == SymbolKind.CONSTANT

    def __repr__(self) -> str:
        return (
            f"Symbol("
            f"name={self.name!r}, "
            f"kind={self.kind!r}, "
            f"index={self.index}, "
            f"type={self.typ!r}, "
            f"scope={self.scope_id}"
            f")"
        )


# ═══════════════════════════════════════════════════════════════════════
# SYMBOL ERRORS
# ═══════════════════════════════════════════════════════════════════════

class SymbolError(Exception):
    """Basisfehler der Symbolverwaltung."""


class DuplicateSymbolError(SymbolError):
    """Ein Symbol wurde innerhalb desselben Scopes doppelt definiert."""


class SymbolNotFoundError(SymbolError):
    """Ein Symbol konnte nicht aufgelöst werden."""


class InvalidSymbolNameError(SymbolError):
    """Ungültiger Symbolname."""


# ═══════════════════════════════════════════════════════════════════════
# SCOPE
# ═══════════════════════════════════════════════════════════════════════

class Scope:
    """
    Lexikalischer Compiler-Scope.

    Jeder Scope besitzt eine eigene Symboltabelle und optional einen
    Parent-Scope.

    Beispiel:

        global
          │
          └── function
                │
                └── if-block

    `resolve()` traversiert standardmäßig vom innersten Scope nach außen.
    """

    _next_scope_id = 0

    @classmethod
    def _allocate_scope_id(cls) -> int:
        scope_id = cls._next_scope_id
        cls._next_scope_id += 1
        return scope_id

    def __init__(
        self,
        parent: Optional["Scope"] = None,
        *,
        name: str = "",
        kind: str = "block",
    ) -> None:
        self.parent = parent
        self.name = name
        self.kind = kind

        self.scope_id = self._allocate_scope_id()

        self.symbols: Dict[str, Symbol] = {}
        self._next_index = 0

    # ─────────────────────────────────────────────────────────────────
    # Definition
    # ─────────────────────────────────────────────────────────────────

    def define(
        self,
        name: str,
        kind: SymbolKind | str,
        typ: str = "",
        *,
        mutable: bool = True,
        exported: bool = False,
        metadata: Optional[Dict[str, object]] = None,
        allow_replace: bool = False,
    ) -> Symbol:
        """
        Definiert ein Symbol im aktuellen Scope.

        Wichtig:
            Ein Symbol aus einem Parent-Scope gilt NICHT als Duplikat.
            Dadurch bleibt Shadowing möglich.

        Doppelte Definitionen innerhalb desselben Scopes sind dagegen
        standardmäßig verboten.
        """

        self._validate_name(name)

        if name in self.symbols and not allow_replace:
            previous = self.symbols[name]
            raise DuplicateSymbolError(
                f"Symbol '{name}' bereits definiert "
                f"in Scope '{self.display_name}'. "
                f"Vorherige Definition: {previous}"
            )

        if allow_replace and name in self.symbols:
            index = self.symbols[name].index
        else:
            index = self._next_index
            self._next_index += 1

        symbol = Symbol(
            name=name,
            kind=kind,
            index=index,
            typ=typ,
            mutable=mutable,
            exported=exported,
            scope_id=self.scope_id,
            metadata=dict(metadata or {}),
        )

        self.symbols[name] = symbol
        return symbol

    def define_local(
        self,
        name: str,
        typ: str = "",
        *,
        mutable: bool = True,
    ) -> Symbol:
        return self.define(
            name,
            SymbolKind.LOCAL,
            typ,
            mutable=mutable,
        )

    def define_parameter(
        self,
        name: str,
        typ: str = "",
    ) -> Symbol:
        return self.define(
            name,
            SymbolKind.PARAMETER,
            typ,
            mutable=True,
        )

    def define_global(
        self,
        name: str,
        typ: str = "",
        *,
        mutable: bool = True,
        exported: bool = False,
    ) -> Symbol:
        return self.define(
            name,
            SymbolKind.GLOBAL,
            typ,
            mutable=mutable,
            exported=exported,
        )

    def define_constant(
        self,
        name: str,
        typ: str = "",
        *,
        exported: bool = False,
    ) -> Symbol:
        return self.define(
            name,
            SymbolKind.CONSTANT,
            typ,
            mutable=False,
            exported=exported,
        )

    def define_function(
        self,
        name: str,
        typ: str = "",
        *,
        exported: bool = False,
    ) -> Symbol:
        return self.define(
            name,
            SymbolKind.FUNCTION,
            typ,
            mutable=False,
            exported=exported,
        )

    def define_state(
        self,
        name: str,
        typ: str = "",
        *,
        mutable: bool = True,
    ) -> Symbol:
        return self.define(
            name,
            SymbolKind.STATE,
            typ,
            mutable=mutable,
        )

    # ─────────────────────────────────────────────────────────────────
    # Resolution
    # ─────────────────────────────────────────────────────────────────

    def resolve_local(self, name: str) -> Optional[Symbol]:
        """
        Sucht ausschließlich im aktuellen Scope.
        """
        return self.symbols.get(name)

    def resolve(self, name: str) -> Optional[Symbol]:
        """
        Lexikalische Symbolauflösung.

        Suchreihenfolge:

            current scope
                ↓
            parent
                ↓
            grandparent
                ↓
            ...

        """

        symbol = self.symbols.get(name)

        if symbol is not None:
            return symbol

        if self.parent is not None:
            return self.parent.resolve(name)

        return None

    def require(self, name: str) -> Symbol:
        """
        Resolve mit Exception bei fehlendem Symbol.
        """

        symbol = self.resolve(name)

        if symbol is None:
            raise SymbolNotFoundError(
                f"Symbol '{name}' konnte nicht aufgelöst werden "
                f"in Scope '{self.display_name}'."
            )

        return symbol

    # ─────────────────────────────────────────────────────────────────
    # Scope hierarchy
    # ─────────────────────────────────────────────────────────────────

    def child(
        self,
        *,
        name: str = "",
        kind: str = "block",
    ) -> "Scope":
        return Scope(
            parent=self,
            name=name,
            kind=kind,
        )

    def function_scope(self, name: str) -> "Scope":
        return self.child(
            name=name,
            kind="function",
        )

    def contract_scope(self, name: str) -> "Scope":
        return self.child(
            name=name,
            kind="contract",
        )

    # ─────────────────────────────────────────────────────────────────
    # Inspection
    # ─────────────────────────────────────────────────────────────────

    @property
    def display_name(self) -> str:
        if self.name:
            return self.name
        return f"{self.kind}#{self.scope_id}"

    @property
    def depth(self) -> int:
        depth = 0
        current = self.parent

        while current is not None:
            depth += 1
            current = current.parent

        return depth

    def contains(self, name: str) -> bool:
        return name in self.symbols

    def shadows(self, name: str) -> bool:
        """
        Prüft, ob eine lokale Definition ein Parent-Symbol überschattet.
        """

        if name not in self.symbols:
            return False

        if self.parent is None:
            return False

        return self.parent.resolve(name) is not None

    def iter_local(self) -> Iterator[Symbol]:
        return iter(self.symbols.values())

    def all_visible(self) -> Dict[str, Symbol]:
        """
        Liefert alle aktuell sichtbaren Symbole.

        Lokale Definitionen überschreiben Parent-Definitionen.
        """

        result: Dict[str, Symbol] = {}

        if self.parent is not None:
            result.update(self.parent.all_visible())

        result.update(self.symbols)

        return result

    def __contains__(self, name: str) -> bool:
        return self.resolve(name) is not None

    def __iter__(self) -> Iterator[Symbol]:
        return self.iter_local()

    def __len__(self) -> int:
        return len(self.symbols)

    @staticmethod
    def _validate_name(name: str) -> None:
        if not isinstance(name, str):
            raise InvalidSymbolNameError(
                "Symbolname muss ein String sein."
            )

        if not name:
            raise InvalidSymbolNameError(
                "Symbolname darf nicht leer sein."
            )

    def __repr__(self) -> str:
        return (
            f"Scope("
            f"id={self.scope_id}, "
            f"name={self.display_name!r}, "
            f"kind={self.kind!r}, "
            f"symbols={len(self.symbols)}"
            f")"
        )


# ═══════════════════════════════════════════════════════════════════════
# SYMBOL TABLE
# ═══════════════════════════════════════════════════════════════════════

class SymbolTable:
    """
    Kompatibilitäts- und High-Level-Wrapper um Scope.

    Diese Klasse ersetzt die bisherige einfache Implementierung:

        SymbolTable(parent=None)
        define(...)
        resolve(...)
        child()

    Dadurch bleibt bestehender Compiler-Code weitgehend kompatibel,
    während intern eine sauber definierte Scope-Abstraktion verwendet
    wird.
    """

    def __init__(
        self,
        parent: Optional["SymbolTable"] = None,
        *,
        scope: Optional[Scope] = None,
        name: str = "",
        kind: str = "block",
    ) -> None:

        if scope is not None:
            self.scope = scope
        elif parent is not None:
            self.scope = parent.scope.child(
                name=name,
                kind=kind,
            )
        else:
            self.scope = Scope(
                name=name,
                kind=kind,
            )

    @property
    def symbols(self) -> Dict[str, Symbol]:
        return self.scope.symbols

    @property
    def parent(self) -> Optional["SymbolTable"]:
        if self.scope.parent is None:
            return None

        return SymbolTable(scope=self.scope.parent)

    @property
    def next_index(self) -> int:
        return self.scope._next_index

    def define(
        self,
        name: str,
        kind: SymbolKind | str,
        typ: str = "",
        **kwargs,
    ) -> Symbol:
        return self.scope.define(
            name,
            kind,
            typ,
            **kwargs,
        )

    def resolve(self, name: str) -> Optional[Symbol]:
        return self.scope.resolve(name)

    def resolve_local(self, name: str) -> Optional[Symbol]:
        return self.scope.resolve_local(name)

    def require(self, name: str) -> Symbol:
        return self.scope.require(name)

    def child(self) -> "SymbolTable":
        return SymbolTable(
            scope=self.scope.child(),
        )

    def function_scope(self, name: str) -> "SymbolTable":
        return SymbolTable(
            scope=self.scope.function_scope(name),
        )

    def contract_scope(self, name: str) -> "SymbolTable":
        return SymbolTable(
            scope=self.scope.contract_scope(name),
        )

    def contains(self, name: str) -> bool:
        return name in self.scope

    def __contains__(self, name: str) -> bool:
        return name in self.scope

    def __iter__(self) -> Iterator[Symbol]:
        return iter(self.scope)

    def __len__(self) -> int:
        return len(self.scope)

    def __repr__(self) -> str:
        return repr(self.scope)


# ═══════════════════════════════════════════════════════════════════════
# BUILTIN SYMBOL REGISTRATION
# ═══════════════════════════════════════════════════════════════════════

def create_global_scope() -> Scope:
    """
    Erstellt den Root-Scope des Compilers.

    Builtins werden bewusst nur als Metadaten registriert. Ihre Runtime-
    Implementierung gehört nicht in das Symbolsystem.
    """

    scope = Scope(
        name="global",
        kind="module",
    )

    builtins = (
        "print",
        "len",
        "assert",
        "panic",
    )

    for name in builtins:
        scope.define(
            name,
            SymbolKind.BUILTIN,
            typ="builtin",
            mutable=False,
        )

    return scope


def register_builtin(
    scope: Scope,
    name: str,
    typ: str = "builtin",
) -> Symbol:
    """
    Registriert ein einzelnes Builtin.

    Bereits vorhandene Symbole werden nicht überschrieben.
    """

    if scope.resolve_local(name) is not None:
        return scope.resolve_local(name)  # type: ignore[return-value]

    return scope.define(
        name,
        SymbolKind.BUILTIN,
        typ=typ,
        mutable=False,
    )


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    "SymbolKind",
    "Symbol",
    "Scope",
    "SymbolTable",
    "SymbolError",
    "DuplicateSymbolError",
    "SymbolNotFoundError",
    "InvalidSymbolNameError",
    "create_global_scope",
    "register_builtin",
]