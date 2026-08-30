# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler Constant Pool
==============================

Zentrales Constant-Pool-System des ATCLang Compilers.

Verantwortung
-------------

constants.py verwaltet alle immutable Konstanten, die während der
Compilation in ein ATC-Bytecode-Modul übernommen werden.

Unterstützte Konstantentypen:

    - null
    - bool
    - int
    - float
    - string
    - bytes

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

Design Guarantees
-----------------

- deterministische Insertion-Order
- stabile Constant-Pool-Indizes
- typbewusste Deduplication
- strikte Typvalidierung
- keine implizite bool → int Konvertierung
- endliche IEEE-754 Float-Werte
- kanonische Behandlung von -0.0 / +0.0
- definierte maximale Pool-Größe
- definierte maximale String-/Bytes-Größe
- definierte maximale Pool-Nutzlast
- stabile Serialisierung
- sichere Rekonstruktion
- Freeze-Semantik
- Optimizer-kompatible Indizes
- keine Abhängigkeit auf Parser, AST oder VM
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple

from .errors import (
    CompileErrorCode,
    ConstantPoolError,
    ConstantPoolOverflowError,
)


# ═══════════════════════════════════════════════════════════════════════
# VERSION
# ═══════════════════════════════════════════════════════════════════════

__version__ = "0.3.1"


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT TYPE
# ═══════════════════════════════════════════════════════════════════════


class ConstantType(str, Enum):
    """Kanonische Konstantentypen des ATCLang Constant Pools."""

    NULL = "null"
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BYTES = "bytes"


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT POOL LIMITS
# ═══════════════════════════════════════════════════════════════════════


class ConstantPoolLimits:
    """
    Normative Limits für den Constant Pool.

    Die Werte sind bewusst zentralisiert, damit Compiler, Optimizer
    und Bytecode-Emitter dieselben Grenzen verwenden können.
    """

    # u16 Constant-Pool-Index.
    MAX_ENTRIES = 65535

    # Maximale Größe einer einzelnen String-Konstante in UTF-8-Bytes.
    MAX_STRING_BYTES = 16 * 1024 * 1024

    # Maximale Größe einer einzelnen Bytes-Konstante.
    MAX_BYTES_SIZE = 16 * 1024 * 1024

    # Maximale Summe der Nutzdaten aller Konstanten.
    MAX_TOTAL_PAYLOAD_BYTES = 64 * 1024 * 1024


# ═══════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════


def _constant_error(message: str) -> ConstantPoolError:
    """Erzeugt einen standardisierten ConstantPoolError."""

    return ConstantPoolError(
        message,
        code=CompileErrorCode.INVALID_CONSTANT,
    )


def _require_exact_int(
    value: Any,
    *,
    name: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> None:
    """Validiert einen echten Python-int ohne bool-Konvertierung."""

    if type(value) is not int:
        raise ValueError(f"{name} muss ein int sein")

    if minimum is not None and value < minimum:
        raise ValueError(
            f"{name} muss >= {minimum} sein"
        )

    if maximum is not None and value > maximum:
        raise ValueError(
            f"{name} darf maximal {maximum} sein"
        )


def _payload_size(
    constant_type: ConstantType,
    value: Any,
) -> int:
    """
    Berechnet die Payload-Größe einer Konstanten.

    Die Größe wird für Quota-/DoS-Schutz verwendet.
    """

    if constant_type is ConstantType.NULL:
        return 0

    if constant_type is ConstantType.BOOL:
        return 1

    if constant_type is ConstantType.INT:
        # Python-Integer ist unbeschränkt groß.
        # Die exakte ABI-Breite wird hier bewusst nicht vorweggenommen.
        return max(1, (abs(value).bit_length() + 7) // 8)

    if constant_type is ConstantType.FLOAT:
        return 8

    if constant_type is ConstantType.STRING:
        return len(value.encode("utf-8"))

    if constant_type is ConstantType.BYTES:
        return len(value)

    raise _constant_error(
        f"Unsupported constant type: {constant_type!r}"
    )


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT VALIDATION
# ═══════════════════════════════════════════════════════════════════════


def _validate_constant_value(
    constant_type: ConstantType,
    value: Any,
) -> None:
    """
    Validiert einen Konstantenwert gegen seinen ConstantType.

    Die Prüfung verwendet bewusst type(...), damit bool nicht
    versehentlich als int akzeptiert wird.
    """

    if not isinstance(constant_type, ConstantType):
        raise _constant_error(
            f"Unsupported constant type: {constant_type!r}"
        )

    if constant_type is ConstantType.NULL:
        if value is not None:
            raise _constant_error(
                "NULL constant must contain None"
            )
        return

    if constant_type is ConstantType.BOOL:
        if type(value) is not bool:
            raise _constant_error(
                "BOOL constant must contain a bool"
            )
        return

    if constant_type is ConstantType.INT:
        if type(value) is not int:
            raise _constant_error(
                "INT constant must contain an int"
            )
        return

    if constant_type is ConstantType.FLOAT:
        if type(value) is not float:
            raise _constant_error(
                "FLOAT constant must contain a float"
            )

        if not math.isfinite(value):
            raise _constant_error(
                "FLOAT constant must be finite"
            )

        return

    if constant_type is ConstantType.STRING:
        if type(value) is not str:
            raise _constant_error(
                "STRING constant must contain a str"
            )

        encoded_size = len(value.encode("utf-8"))

        if encoded_size > ConstantPoolLimits.MAX_STRING_BYTES:
            raise _constant_error(
                "STRING constant exceeds maximum size: "
                f"{ConstantPoolLimits.MAX_STRING_BYTES} bytes"
            )

        return

    if constant_type is ConstantType.BYTES:
        if type(value) is not bytes:
            raise _constant_error(
                "BYTES constant must contain bytes"
            )

        if len(value) > ConstantPoolLimits.MAX_BYTES_SIZE:
            raise _constant_error(
                "BYTES constant exceeds maximum size: "
                f"{ConstantPoolLimits.MAX_BYTES_SIZE} bytes"
            )

        return

    raise _constant_error(
        f"Unsupported constant type: {constant_type!r}"
    )


# ═══════════════════════════════════════════════════════════════════════
# TYPE INFERENCE
# ═══════════════════════════════════════════════════════════════════════


def infer_constant_type(value: Any) -> ConstantType:
    """
    Ermittelt den kanonischen ConstantType eines Python-Wertes.

    Die Prüfung erfolgt bewusst mit type(...), damit:

        True

nicht als:

        1

interpretiert wird.
    """

    if value is None:
        return ConstantType.NULL

    if type(value) is bool:
        return ConstantType.BOOL

    if type(value) is int:
        return ConstantType.INT

    if type(value) is float:
        if not math.isfinite(value):
            raise _constant_error(
                "FLOAT constant must be finite"
            )

        return ConstantType.FLOAT

    if type(value) is str:
        return ConstantType.STRING

    if type(value) is bytes:
        return ConstantType.BYTES

    raise _constant_error(
        "Unsupported constant value type: "
        f"{type(value).__name__}"
    )


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT KEY
# ═══════════════════════════════════════════════════════════════════════


def _constant_key(
    constant_type: ConstantType,
    value: Any,
) -> Tuple[ConstantType, Any]:
    """
    Erzeugt einen stabilen Deduplication-Key.

    Der ConstantType ist immer Bestandteil des Keys.

    Dadurch sind:

        bool(True)

und:

        int(1)

unterschiedliche Konstanten.

    Float Policy
    ------------

    - NaN ist nicht erlaubt.
    - +/-Infinity ist nicht erlaubt.
    - -0.0 und +0.0 werden als dieselbe mathematische Konstante
      behandelt.
    """

    if constant_type is ConstantType.BYTES:
        value = bytes(value)

    elif constant_type is ConstantType.FLOAT:
        if value == 0.0:
            value = 0.0

    return constant_type, value


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class Constant:
    """
    Ein einzelner Eintrag im Constant Pool.

    Attributes
    ----------

    index:
        Stabiler Pool-Index.

    type:
        Kanonischer ATCLang-Konstantentyp.

    value:
        Immutable Konstantenwert.
    """

    index: int
    type: ConstantType
    value: Any

    def __post_init__(self) -> None:
        _require_exact_int(
            self.index,
            name="Constant.index",
            minimum=0,
            maximum=ConstantPoolLimits.MAX_ENTRIES - 1,
        )

        _validate_constant_value(
            self.type,
            self.value,
        )

    def to_dict(self) -> dict:
        """
        Erstellt eine JSON-kompatible Repräsentation.

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
    def from_dict(
        cls,
        data: dict,
    ) -> "Constant":
        """
        Rekonstruiert eine Constant aus einer serialisierten Struktur.
        """

        if not isinstance(data, dict):
            raise _constant_error(
                "Constant entry must be a dictionary"
            )

        try:
            raw_index = data["index"]
            raw_type = data["type"]
        except KeyError as exc:
            raise _constant_error(
                "Serialized constant entry is missing "
                "required fields"
            ) from exc

        if type(raw_index) is not int:
            raise _constant_error(
                "Serialized constant index must be an integer"
            )

        try:
            constant_type = ConstantType(raw_type)
        except (TypeError, ValueError) as exc:
            raise _constant_error(
                f"Invalid serialized constant type: {raw_type!r}"
            ) from exc

        value = data.get("value")

        if constant_type is ConstantType.BYTES:
            if type(value) is not str:
                raise _constant_error(
                    "Serialized bytes constant must be "
                    "a hexadecimal string"
                )

            try:
                value = bytes.fromhex(value)
            except ValueError as exc:
                raise _constant_error(
                    "Invalid hexadecimal bytes constant"
                ) from exc

        return cls(
            index=raw_index,
            type=constant_type,
            value=value,
        )


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT POOL
# ═══════════════════════════════════════════════════════════════════════


class ConstantPool:
    """
    Deterministischer ATCLang Constant Pool.

    Eigenschaften
    -------------

    - stabile Insertion-Order
    - stabile Indizes
    - typbewusste Deduplication
    - Größenlimits
    - Serialisierung
    - Rekonstruktion
    - Freeze-Semantik
    - unabhängige Kopierbarkeit

    Lifecycle
    ---------

        BUILDING
            │
            │ freeze()
            ▼
        FROZEN

    Ein gefrorener Constant Pool darf nicht mehr verändert werden.
    """

    DEFAULT_MAX_SIZE = ConstantPoolLimits.MAX_ENTRIES

    def __init__(
        self,
        *,
        max_size: int = DEFAULT_MAX_SIZE,
        max_total_payload_bytes: int = (
            ConstantPoolLimits.MAX_TOTAL_PAYLOAD_BYTES
        ),
    ) -> None:
        _require_exact_int(
            max_size,
            name="max_size",
            minimum=1,
            maximum=ConstantPoolLimits.MAX_ENTRIES,
        )

        _require_exact_int(
            max_total_payload_bytes,
            name="max_total_payload_bytes",
            minimum=1,
            maximum=ConstantPoolLimits.MAX_TOTAL_PAYLOAD_BYTES,
        )

        self.max_size = max_size
        self.max_total_payload_bytes = max_total_payload_bytes

        self._constants: List[Constant] = []

        self._index: Dict[
            Tuple[ConstantType, Any],
            int,
        ] = {}

        self._total_payload_bytes = 0
        self._frozen = False

    # ═══════════════════════════════════════════════════════════════
    # STATE
    # ═══════════════════════════════════════════════════════════════

    @property
    def is_frozen(self) -> bool:
        """Gibt an, ob der Constant Pool eingefroren wurde."""

        return self._frozen

    def freeze(self) -> None:
        """
        Friert den Constant Pool ein.

        Nach dem Freeze sind strukturelle Änderungen verboten.
        """

        self._frozen = True

    def _ensure_mutable(self) -> None:
        """Stellt sicher, dass der Pool verändert werden darf."""

        if self._frozen:
            raise ConstantPoolError(
                "Constant pool is frozen",
                code=CompileErrorCode.INVALID_CONSTANT,
            )

    # ═══════════════════════════════════════════════════════════════
    # INSERT
    # ═══════════════════════════════════════════════════════════════

    def add(
        self,
        value: Any,
        *,
        constant_type: Optional[ConstantType] = None,
    ) -> int:
        """
        Fügt eine Konstante hinzu und gibt ihren Index zurück.

        Existiert die Konstante bereits, wird der bestehende Index
        zurückgegeben.

        Bereits vorhandene Konstanten dürfen auch in einem gefrorenen
        Pool abgefragt werden. Neue Einträge sind im Frozen State
        verboten.
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

        self._ensure_mutable()

        if len(self._constants) >= self.max_size:
            raise ConstantPoolOverflowError(
                "Constant pool overflow: "
                f"maximum size is {self.max_size}"
            )

        payload_size = _payload_size(
            constant_type,
            value,
        )

        if (
            self._total_payload_bytes + payload_size
            > self.max_total_payload_bytes
        ):
            raise ConstantPoolOverflowError(
                "Constant pool payload overflow: "
                f"maximum payload is "
                f"{self.max_total_payload_bytes} bytes"
            )

        index = len(self._constants)

        constant = Constant(
            index=index,
            type=constant_type,
            value=value,
        )

        self._constants.append(constant)
        self._index[key] = index
        self._total_payload_bytes += payload_size

        return index

    # ═══════════════════════════════════════════════════════════════
    # TYPED INSERT HELPERS
    # ═══════════════════════════════════════════════════════════════

    def add_null(self) -> int:
        """Fügt eine NULL-Konstante hinzu."""

        return self.add(
            None,
            constant_type=ConstantType.NULL,
        )

    def add_bool(
        self,
        value: bool,
    ) -> int:
        """Fügt eine Boolean-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.BOOL,
        )

    def add_int(
        self,
        value: int,
    ) -> int:
        """Fügt eine Integer-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.INT,
        )

    def add_float(
        self,
        value: float,
    ) -> int:
        """Fügt eine Float-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.FLOAT,
        )

    def add_string(
        self,
        value: str,
    ) -> int:
        """Fügt eine String-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.STRING,
        )

    def add_bytes(
        self,
        value: bytes,
    ) -> int:
        """Fügt eine Bytes-Konstante hinzu."""

        return self.add(
            value,
            constant_type=ConstantType.BYTES,
        )

    # ═══════════════════════════════════════════════════════════════
    # LOOKUP
    # ═══════════════════════════════════════════════════════════════

    def get(
        self,
        index: int,
    ) -> Constant:
        """
        Liefert eine Konstante anhand ihres Index.
        """

        if type(index) is not int:
            raise _constant_error(
                "Constant index must be an integer"
            )

        if index < 0 or index >= len(self._constants):
            raise _constant_error(
                f"Invalid constant index: {index}"
            )

        return self._constants[index]

    def find(
        self,
        value: Any,
        *,
        constant_type: Optional[ConstantType] = None,
    ) -> Optional[int]:
        """
        Sucht eine Konstante, ohne sie hinzuzufügen.

        Gibt None zurück, wenn sie nicht vorhanden ist.
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

    # ═══════════════════════════════════════════════════════════════
    # PROPERTIES
    # ═══════════════════════════════════════════════════════════════

    @property
    def size(self) -> int:
        """Aktuelle Anzahl der Konstanten."""

        return len(self._constants)

    @property
    def is_full(self) -> bool:
        """Gibt an, ob der Constant Pool voll ist."""

        return self.size >= self.max_size

    @property
    def total_payload_bytes(self) -> int:
        """Aktuelle Summe der Constant-Payload-Größen."""

        return self._total_payload_bytes

    @property
    def constants(self) -> Tuple[Constant, ...]:
        """Read-only Sicht auf den Constant Pool."""

        return tuple(self._constants)

    # ═══════════════════════════════════════════════════════════════
    # ITERATION
    # ═══════════════════════════════════════════════════════════════

    def __iter__(self) -> Iterator[Constant]:
        return iter(self._constants)

    def __len__(self) -> int:
        return len(self._constants)

    # ═══════════════════════════════════════════════════════════════
    # SERIALIZATION
    # ═══════════════════════════════════════════════════════════════

    def to_dict(self) -> List[dict]:
        """
        Serialisiert den vollständigen Constant Pool.

        Die Reihenfolge der Liste ist normativ und entspricht exakt
        der Constant-Pool-Indexierung.
        """

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
        max_total_payload_bytes: int = (
            ConstantPoolLimits.MAX_TOTAL_PAYLOAD_BYTES
        ),
    ) -> "ConstantPool":
        """
        Rekonstruiert einen Constant Pool.

        Anforderungen
        -------------

        - Indizes müssen bei 0 beginnen.
        - Indizes müssen lückenlos sein.
        - Einträge dürfen nicht dupliziert sein.
        - Typ und Wert müssen valide sein.
        - Pool- und Payload-Limits gelten auch bei Deserialisierung.
        """

        if isinstance(data, (str, bytes, dict)):
            raise _constant_error(
                "Serialized constant pool must be an iterable "
                "of constant dictionaries"
            )

        pool = cls(
            max_size=max_size,
            max_total_payload_bytes=max_total_payload_bytes,
        )

        try:
            iterator = iter(data)
        except TypeError as exc:
            raise _constant_error(
                "Serialized constant pool is not iterable"
            ) from exc

        for expected_index, item in enumerate(iterator):
            constant = Constant.from_dict(item)

            if constant.index != expected_index:
                raise _constant_error(
                    "Invalid constant pool ordering: "
                    f"expected index {expected_index}, "
                    f"got {constant.index}"
                )

            actual_index = pool.add(
                constant.value,
                constant_type=constant.type,
            )

            if actual_index != expected_index:
                raise _constant_error(
                    "Constant pool contains duplicate entries"
                )

        return pool

    # ═══════════════════════════════════════════════════════════════
    # COPY
    # ═══════════════════════════════════════════════════════════════

    def copy(self) -> "ConstantPool":
        """
        Erstellt eine unabhängige Kopie des Constant Pools.

        Der Frozen-State wird übernommen.
        """

        result = ConstantPool(
            max_size=self.max_size,
            max_total_payload_bytes=self.max_total_payload_bytes,
        )

        for constant in self._constants:
            result.add(
                constant.value,
                constant_type=constant.type,
            )

        if self._frozen:
            result.freeze()

        return result

    # ═══════════════════════════════════════════════════════════════
    # CLEAR
    # ═══════════════════════════════════════════════════════════════

    def clear(self) -> None:
        """
        Leert den Constant Pool.

        Ein gefrorener Pool darf nicht geleert werden.
        """

        self._ensure_mutable()

        self._constants.clear()
        self._index.clear()
        self._total_payload_bytes = 0


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT POOL BUILDER
# ═══════════════════════════════════════════════════════════════════════


class ConstantPoolBuilder:
    """
    Convenience-Builder für Compiler-Komponenten.

    Der Builder kapselt den ConstantPool und stellt eine einfache
    API für Literal-Lowering bereit.
    """

    def __init__(
        self,
        *,
        max_size: int = ConstantPool.DEFAULT_MAX_SIZE,
        max_total_payload_bytes: int = (
            ConstantPoolLimits.MAX_TOTAL_PAYLOAD_BYTES
        ),
    ) -> None:
        self.pool = ConstantPool(
            max_size=max_size,
            max_total_payload_bytes=max_total_payload_bytes,
        )

    def literal(
        self,
        value: Any,
    ) -> int:
        """Registriert ein Literal."""

        return self.pool.add(value)

    def null(self) -> int:
        return self.pool.add_null()

    def boolean(
        self,
        value: bool,
    ) -> int:
        return self.pool.add_bool(value)

    def integer(
        self,
        value: int,
    ) -> int:
        return self.pool.add_int(value)

    def floating(
        self,
        value: float,
    ) -> int:
        return self.pool.add_float(value)

    def string(
        self,
        value: str,
    ) -> int:
        return self.pool.add_string(value)

    def bytes(
        self,
        value: bytes,
    ) -> int:
        return self.pool.add_bytes(value)

    def freeze(self) -> None:
        """Friert den zugrunde liegenden Pool ein."""

        self.pool.freeze()

    def build(self) -> ConstantPool:
        """
        Gibt den aufgebauten Constant Pool zurück.
        """

        return self.pool


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════


__all__ = [
    "ConstantType",
    "Constant",
    "ConstantPoolLimits",
    "ConstantPool",
    "ConstantPoolBuilder",
    "infer_constant_type",
]


__version__ = "0.3.1"