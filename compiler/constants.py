# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler Constant Pool
==============================

Zentrales Constant-Pool-System des ATCLang Compilers.

Verantwortung
-------------

constants.py verwaltet alle Konstanten, die während der Compilation
in den erzeugten ATC-Bytecode übernommen werden.

Beispiele:

    - Integer
    - Float
    - Boolean
    - String
    - Bytes
    - None / Null
    - weitere immutable Literale

Architektur
-----------

    AST
     │
     ▼
    Expression Lowering
     │
     ▼
    ConstantPool
     │
     ▼
    Bytecode

Dependency Rule
---------------

constants.py darf keine Abhängigkeit auf andere Compiler-Module
besitzen.

Erlaubt:

    constants.py
        ↓
    errors.py

Nicht erlaubt:

    constants.py
        ↓
    bytecode.py
        ↓
    compiler.py

Ziele
-----

- deterministische Constant-Pool-Indizes
- Deduplication identischer Konstanten
- stabile Serialisierung
- definierte maximale Pool-Größe
- sichere Typvalidierung
- Optimizer-kompatible Indizes
- JSON-kompatible Darstellung
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from .errors import (
    CompileErrorCode,
    ConstantPoolError,
    ConstantPoolOverflowError,
)


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT TYPE
# ═══════════════════════════════════════════════════════════════════════


class ConstantType(str, Enum):
    """Kanonische Typen des ATCLang Constant Pools."""

    NULL = "null"
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BYTES = "bytes"


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT VALUE
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class Constant:
    """
    Ein einzelner Eintrag im Constant Pool.

    index
        Deterministischer Pool-Index.

    type
        Kanonischer ATCLang-Konstantentyp.

    value
        Tatsächlicher Konstantenwert.
    """

    index: int
    type: ConstantType
    value: Any

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("Constant.index darf nicht negativ sein")

        _validate_constant_value(self.type, self.value)

    def to_dict(self) -> dict:
        """
        JSON-kompatible Repräsentation.

        Bytes werden als Hex-String serialisiert.
        """

        if self.type is ConstantType.BYTES:
            value = self.value.hex()
        else:
            value = self.value

        return {
            "index": self.index,
            "type": self.type.value,
            "value": value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Constant":
        """Erzeugt eine Constant aus einer serialisierten Struktur."""

        if not isinstance(data, dict):
            raise ConstantPoolError(
                "Constant entry must be a dictionary",
                code=CompileErrorCode.INVALID_CONSTANT,
            )

        try:
            index = int(data["index"])
            constant_type = ConstantType(data["type"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ConstantPoolError(
                "Invalid serialized constant entry",
                code=CompileErrorCode.INVALID_CONSTANT,
            ) from exc

        value = data.get("value")

        if constant_type is ConstantType.BYTES:
            if not isinstance(value, str):
                raise ConstantPoolError(
                    "Serialized bytes constant must be a hex string",
                    code=CompileErrorCode.INVALID_CONSTANT,
                )

            try:
                value = bytes.fromhex(value)
            except ValueError as exc:
                raise ConstantPoolError(
                    "Invalid hexadecimal bytes constant",
                    code=CompileErrorCode.INVALID_CONSTANT,
                ) from exc

        return cls(
            index=index,
            type=constant_type,
            value=value,
        )


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT KEY
# ═══════════════════════════════════════════════════════════════════════


def _constant_key(
    constant_type: ConstantType,
    value: Any,
) -> Tuple[ConstantType, Any]:
    """
    Erzeugt einen stabilen Schlüssel für Deduplication.

    Der Typ ist Bestandteil des Schlüssels.

    Dadurch werden beispielsweise:

        bool(True)

und:

        int(1)

nicht als dieselbe Konstante behandelt.
    """

    if constant_type is ConstantType.BYTES:
        value = bytes(value)

    return constant_type, value


# ═══════════════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════════════


def _validate_constant_value(
    constant_type: ConstantType,
    value: Any,
) -> None:
    """Validiert einen Konstantenwert gegen seinen ConstantType."""

    if constant_type is ConstantType.NULL:
        if value is not None:
            raise ConstantPoolError(
                "NULL constant must contain None",
                code=CompileErrorCode.INVALID_CONSTANT,
            )
        return

    if constant_type is ConstantType.BOOL:
        if type(value) is not bool:
            raise ConstantPoolError(
                "BOOL constant must contain a bool",
                code=CompileErrorCode.INVALID_CONSTANT,
            )
        return

    if constant_type is ConstantType.INT:
        if type(value) is not int:
            raise ConstantPoolError(
                "INT constant must contain an int",
                code=CompileErrorCode.INVALID_CONSTANT,
            )
        return

    if constant_type is ConstantType.FLOAT:
        if type(value) is not float:
            raise ConstantPoolError(
                "FLOAT constant must contain a float",
                code=CompileErrorCode.INVALID_CONSTANT,
            )
        return

    if constant_type is ConstantType.STRING:
        if not isinstance(value, str):
            raise ConstantPoolError(
                "STRING constant must contain a str",
                code=CompileErrorCode.INVALID_CONSTANT,
            )
        return

    if constant_type is ConstantType.BYTES:
        if not isinstance(value, bytes):
            raise ConstantPoolError(
                "BYTES constant must contain bytes",
                code=CompileErrorCode.INVALID_CONSTANT,
            )
        return

    raise ConstantPoolError(
        f"Unsupported constant type: {constant_type!r}",
        code=CompileErrorCode.INVALID_CONSTANT,
    )


# ═══════════════════════════════════════════════════════════════════════
# TYPE INFERENCE
# ═══════════════════════════════════════════════════════════════════════


def infer_constant_type(value: Any) -> ConstantType:
    """
    Ermittelt den kanonischen ConstantType eines Python-Wertes.

    Die Prüfung erfolgt bewusst mit type(...) statt isinstance(...),
    damit bool nicht versehentlich als int behandelt wird.
    """

    if value is None:
        return ConstantType.NULL

    if type(value) is bool:
        return ConstantType.BOOL

    if type(value) is int:
        return ConstantType.INT

    if type(value) is float:
        return ConstantType.FLOAT

    if type(value) is str:
        return ConstantType.STRING

    if type(value) is bytes:
        return ConstantType.BYTES

    raise ConstantPoolError(
        f"Unsupported constant value type: {type(value).__name__}",
        code=CompileErrorCode.INVALID_CONSTANT,
    )


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT POOL
# ═══════════════════════════════════════════════════════════════════════


class ConstantPool:
    """
    Deterministischer Constant Pool.

    Eigenschaften
    -------------

    - insertion-order stabil
    - identische Konstanten werden dedupliziert
    - Index bleibt nach Einfügung stabil
    - optionales Größenlimit
    """

    DEFAULT_MAX_SIZE = 65535

    def __init__(
        self,
        *,
        max_size: int = DEFAULT_MAX_SIZE,
    ) -> None:
        if max_size <= 0:
            raise ValueError(
                "max_size muss größer als 0 sein"
            )

        self.max_size = max_size

        self._constants: List[Constant] = []
        self._index: Dict[
            Tuple[ConstantType, Any],
            int,
        ] = {}

    # ────────────────────────────────────────────────────────────────
    # INSERT
    # ────────────────────────────────────────────────────────────────

    def add(
        self,
        value: Any,
        *,
        constant_type: Optional[ConstantType] = None,
    ) -> int:
        """
        Fügt eine Konstante hinzu und liefert deren Index.

        Existiert die Konstante bereits, wird ihr bestehender Index
        zurückgegeben.
        """

        if constant_type is None:
            constant_type = infer_constant_type(value)

        _validate_constant_value(
            constant_type,
            value,
        )

        key = _constant_key(
            constant_type,
            value,
        )

        existing = self._index.get(key)

        if existing is not None:
            return existing

        if len(self._constants) >= self.max_size:
            raise ConstantPoolOverflowError(
                (
                    "Constant pool overflow: "
                    f"maximum size is {self.max_size}"
                )
            )

        index = len(self._constants)

        constant = Constant(
            index=index,
            type=constant_type,
            value=value,
        )

        self._constants.append(constant)
        self._index[key] = index

        return index

    def add_null(self) -> int:
        """Fügt eine NULL-Konstante hinzu."""

        return self.add(
            None,
            constant_type=ConstantType.NULL,
        )

    def add_bool(self, value: bool) -> int:
        """Fügt eine Boolean-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.BOOL,
        )

    def add_int(self, value: int) -> int:
        """Fügt eine Integer-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.INT,
        )

    def add_float(self, value: float) -> int:
        """Fügt eine Float-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.FLOAT,
        )

    def add_string(self, value: str) -> int:
        """Fügt eine String-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.STRING,
        )

    def add_bytes(self, value: bytes) -> int:
        """Fügt eine Bytes-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.BYTES,
        )

    # ────────────────────────────────────────────────────────────────
    # LOOKUP
    # ────────────────────────────────────────────────────────────────

    def get(self, index: int) -> Constant:
        """
        Liefert eine Konstante anhand ihres Index.
        """

        if index < 0 or index >= len(self._constants):
            raise ConstantPoolError(
                f"Invalid constant index: {index}",
                code=CompileErrorCode.INVALID_CONSTANT,
            )

        return self._constants[index]

    def find(
        self,
        value: Any,
        *,
        constant_type: Optional[ConstantType] = None,
    ) -> Optional[int]:
        """
        Sucht eine Konstante ohne sie hinzuzufügen.

        Gibt None zurück, wenn sie nicht existiert.
        """

        if constant_type is None:
            constant_type = infer_constant_type(value)

        _validate_constant_value(
            constant_type,
            value,
        )

        return self._index.get(
            _constant_key(
                constant_type,
                value,
            )
        )

    def contains(
        self,
        value: Any,
        *,
        constant_type: Optional[ConstantType] = None,
    ) -> bool:
        """Prüft, ob eine Konstante vorhanden ist."""

        return (
            self.find(
                value,
                constant_type=constant_type,
            )
            is not None
        )

    # ────────────────────────────────────────────────────────────────
    # PROPERTIES
    # ────────────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        """Aktuelle Anzahl der Konstanten."""

        return len(self._constants)

    @property
    def is_full(self) -> bool:
        """Gibt an, ob der Constant Pool voll ist."""

        return self.size >= self.max_size

    @property
    def constants(self) -> Tuple[Constant, ...]:
        """Read-only Sicht auf den Constant Pool."""

        return tuple(self._constants)

    # ────────────────────────────────────────────────────────────────
    # ITERATION
    # ────────────────────────────────────────────────────────────────

    def __iter__(self) -> Iterator[Constant]:
        return iter(self._constants)

    def __len__(self) -> int:
        return len(self._constants)

    # ────────────────────────────────────────────────────────────────
    # SERIALIZATION
    # ────────────────────────────────────────────────────────────────

    def to_dict(self) -> List[dict]:
        """Serialisiert den kompletten Constant Pool."""

        return [
            constant.to_dict()
            for constant in self._constants
        ]

    @classmethod
    def from_dict(
        cls,
        data: Iterable[dict],
        *,
        max_size: int = DEFAULT_MAX_SIZE,
    ) -> "ConstantPool":
        """
        Rekonstruiert einen Constant Pool.

        Die serialisierten Indizes müssen exakt der
        Einfügereihenfolge entsprechen.
        """

        pool = cls(max_size=max_size)

        for expected_index, item in enumerate(data):
            constant = Constant.from_dict(item)

            if constant.index != expected_index:
                raise ConstantPoolError(
                    (
                        "Invalid constant pool ordering: "
                        f"expected index {expected_index}, "
                        f"got {constant.index}"
                    ),
                    code=CompileErrorCode.INVALID_CONSTANT,
                )

            actual_index = pool.add(
                constant.value,
                constant_type=constant.type,
            )

            if actual_index != expected_index:
                raise ConstantPoolError(
                    "Constant pool contains duplicate entries",
                    code=CompileErrorCode.INVALID_CONSTANT,
                )

        return pool

    # ────────────────────────────────────────────────────────────────
    # COPY
    # ────────────────────────────────────────────────────────────────

    def copy(self) -> "ConstantPool":
        """Erstellt eine unabhängige Kopie des Constant Pools."""

        result = ConstantPool(
            max_size=self.max_size,
        )

        for constant in self._constants:
            result.add(
                constant.value,
                constant_type=constant.type,
            )

        return result

    # ────────────────────────────────────────────────────────────────
    # CLEAR
    # ────────────────────────────────────────────────────────────────

    def clear(self) -> None:
        """Leert den Constant Pool."""

        self._constants.clear()
        self._index.clear()


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT POOL BUILDER
# ═══════════════════════════════════════════════════════════════════════


class ConstantPoolBuilder:
    """
    Convenience-Builder für Compiler-Komponenten.

    Der Builder kapselt den Pool und bietet eine klar definierte
    API für Expression- und Literal-Lowering.
    """

    def __init__(
        self,
        *,
        max_size: int = ConstantPool.DEFAULT_MAX_SIZE,
    ) -> None:
        self.pool = ConstantPool(
            max_size=max_size,
        )

    def literal(self, value: Any) -> int:
        """Registriert ein Literal."""

        return self.pool.add(value)

    def null(self) -> int:
        return self.pool.add_null()

    def boolean(self, value: bool) -> int:
        return self.pool.add_bool(value)

    def integer(self, value: int) -> int:
        return self.pool.add_int(value)

    def floating(self, value: float) -> int:
        return self.pool.add_float(value)

    def string(self, value: str) -> int:
        return self.pool.add_string(value)

    def bytes(self, value: bytes) -> int:
        return self.pool.add_bytes(value)

    def build(self) -> ConstantPool:
        """Gibt den aufgebauten Constant Pool zurück."""

        return self.pool


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════


__all__ = [
    # Types
    "ConstantType",
    "Constant",

    # Pool
    "ConstantPool",
    "ConstantPoolBuilder",

    # Helpers
    "infer_constant_type",
]


__version__ = "0.3.0"