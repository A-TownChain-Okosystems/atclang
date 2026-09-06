# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler Errors
=======================

Zentrales, unabhängiges Error- und Diagnostic-System des Compilers.

Dependency Rule
---------------

errors.py ist Layer 0 des Compiler-Subsystems.

    errors.py
        ↑
        ├── source_map.py
        ├── constants.py
        ├── symbols.py
        ├── context.py
        ├── bytecode.py
        ├── expressions.py
        ├── statements.py
        ├── control_flow.py
        ├── functions.py
        ├── contracts.py
        ├── optimizer.py
        └── compiler.py

errors.py darf KEINE Abhängigkeit auf andere Compiler-Module besitzen.

Ziele
-----

- zentrale Compiler-Fehler
- strukturierte Diagnostics
- deterministische Fehlermeldungen
- Source-Location-Unterstützung
- stabile Error-Codes
- CLI/IDE/LSP/CI-Unterstützung
- keine zyklischen Compiler-Imports
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════════
# ERROR SEVERITY
# ═══════════════════════════════════════════════════════════════════════


class ErrorSeverity(str, Enum):
    """Schweregrad einer Compiler-Diagnose."""

    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


# ═══════════════════════════════════════════════════════════════════════
# SOURCE LOCATION
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SourceLocation:
    """
    Einzelne Position im ATCLang-Quelltext.

    line und column sind 1-basiert.

    0 bedeutet:
        Position unbekannt.
    """

    line: int = 0
    column: int = 0

    def __post_init__(self) -> None:
        if self.line < 0:
            raise ValueError(
                "SourceLocation.line darf nicht negativ sein"
            )

        if self.column < 0:
            raise ValueError(
                "SourceLocation.column darf nicht negativ sein"
            )

    @property
    def is_known(self) -> bool:
        """Gibt an, ob die Position bekannt ist."""

        return self.line > 0

    def format(self) -> str:
        """Formatiert die Position für eine Diagnostic."""

        if self.line <= 0:
            return ""

        if self.column > 0:
            return f"{self.line}:{self.column}"

        return str(self.line)


# ═══════════════════════════════════════════════════════════════════════
# SOURCE SPAN
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SourceSpan:
    """
    Bereich im ATCLang-Quelltext.

    Beispiel:

        10:5-10:12
    """

    start: SourceLocation
    end: Optional[SourceLocation] = None

    @classmethod
    def from_node(cls, node: Any) -> "SourceSpan":
        """
        Erstellt einen SourceSpan aus einem AST-Node.

        Unterstützte Attribute:

            line
            col
            column
            end_line
            end_col
            end_column
        """

        if node is None:
            return cls(SourceLocation())

        line = int(
            getattr(node, "line", 0) or 0
        )

        column = getattr(
            node,
            "column",
            None,
        )

        if column is None:
            column = getattr(
                node,
                "col",
                0,
            )

        column = int(column or 0)

        start = SourceLocation(
            line=line,
            column=column,
        )

        end_line = getattr(
            node,
            "end_line",
            None,
        )

        end_column = getattr(
            node,
            "end_column",
            None,
        )

        if end_column is None:
            end_column = getattr(
                node,
                "end_col",
                None,
            )

        if end_line is None and end_column is None:
            return cls(start=start)

        end = SourceLocation(
            line=int(
                end_line
                if end_line is not None
                else line
            ),
            column=int(end_column or 0),
        )

        return cls(
            start=start,
            end=end,
        )

    @property
    def line(self) -> int:
        return self.start.line

    @property
    def column(self) -> int:
        return self.start.column

    @property
    def is_known(self) -> bool:
        return self.start.is_known

    def format(self) -> str:
        """Formatiert den Source-Bereich."""

        start = self.start.format()

        if not start:
            return ""

        if self.end is None:
            return start

        end = self.end.format()

        if not end or end == start:
            return start

        return f"{start}-{end}"


# ═══════════════════════════════════════════════════════════════════════
# COMPILER DIAGNOSTIC
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class CompilerDiagnostic:
    """
    Strukturierte Compiler-Diagnose.

    Verwendbar durch:

        - CLI
        - IDE
        - LSP
        - CI
        - JSON Diagnostics
        - Testsysteme
        - Build-Systeme
    """

    code: str
    message: str

    severity: ErrorSeverity = ErrorSeverity.ERROR

    span: Optional[SourceSpan] = None

    hint: Optional[str] = None
    note: Optional[str] = None

    def format(self) -> str:
        """Erzeugt eine deterministische Textdarstellung."""

        location = ""

        if self.span is not None:
            formatted = self.span.format()

            if formatted:
                location = f" @ {formatted}"

        result = (
            f"[{self.code}] "
            f"{self.severity.value}"
            f"{location}: "
            f"{self.message}"
        )

        if self.hint:
            result += f"\n  hint: {self.hint}"

        if self.note:
            result += f"\n  note: {self.note}"

        return result

    def __str__(self) -> str:
        return self.format()


# ═══════════════════════════════════════════════════════════════════════
# ERROR CODES
# ═══════════════════════════════════════════════════════════════════════


class CompileErrorCode:
    """
    Zentrale ATCLang Compiler Error-Codes.

    Schema:

        ATC-Cxxx

    Kategorien:

        C0xx  General
        C1xx  Syntax / AST
        C2xx  Symbols / Scope
        C3xx  Types
        C4xx  Control Flow
        C5xx  Functions
        C6xx  Contracts
        C7xx  Bytecode
        C8xx  Constants
        C9xx  Optimization
        C999  Internal
    """

    # ───────────────────────────────────────────────────────────────────
    # General
    # ───────────────────────────────────────────────────────────────────

    GENERAL = "ATC-C000"

    # ───────────────────────────────────────────────────────────────────
    # Syntax / AST
    # ───────────────────────────────────────────────────────────────────

    SYNTAX = "ATC-C100"
    INVALID_AST = "ATC-C101"

    # ───────────────────────────────────────────────────────────────────
    # Symbols / Scope
    # ───────────────────────────────────────────────────────────────────

    NAME = "ATC-C200"
    UNDEFINED_SYMBOL = "ATC-C201"
    DUPLICATE_SYMBOL = "ATC-C202"
    INVALID_SCOPE = "ATC-C203"

    # ───────────────────────────────────────────────────────────────────
    # Types
    # ───────────────────────────────────────────────────────────────────

    TYPE = "ATC-C300"
    TYPE_MISMATCH = "ATC-C301"
    INVALID_CAST = "ATC-C302"
    INVALID_OPERATION = "ATC-C303"
    UNKNOWN_TYPE = "ATC-C304"
    INVALID_GENERIC = "ATC-C305"

    # ───────────────────────────────────────────────────────────────────
    # Control Flow
    # ───────────────────────────────────────────────────────────────────

    CONTROL_FLOW = "ATC-C400"
    BREAK_OUTSIDE_LOOP = "ATC-C401"
    CONTINUE_OUTSIDE_LOOP = "ATC-C402"
    INVALID_RETURN = "ATC-C403"
    UNREACHABLE_CODE = "ATC-C404"

    # ───────────────────────────────────────────────────────────────────
    # Functions
    # ───────────────────────────────────────────────────────────────────

    FUNCTION = "ATC-C500"
    INVALID_CALL = "ATC-C501"
    ARGUMENT_COUNT = "ATC-C502"
    DUPLICATE_PARAMETER = "ATC-C503"
    INVALID_FUNCTION = "ATC-C504"

    # ───────────────────────────────────────────────────────────────────
    # Contracts
    # ───────────────────────────────────────────────────────────────────

    CONTRACT = "ATC-C600"
    INVALID_CONTRACT = "ATC-C601"
    INVALID_STATE = "ATC-C602"
    INVALID_EVENT = "ATC-C603"
    INVALID_ERROR = "ATC-C604"
    INVALID_STORAGE = "ATC-C605"

    # ───────────────────────────────────────────────────────────────────
    # Bytecode
    # ───────────────────────────────────────────────────────────────────

    BYTECODE = "ATC-C700"
    INVALID_OPCODE = "ATC-C701"
    INVALID_OPERAND = "ATC-C702"
    INVALID_JUMP = "ATC-C703"
    INVALID_BYTECODE = "ATC-C704"

    # ───────────────────────────────────────────────────────────────────
    # Constant Pool
    # ───────────────────────────────────────────────────────────────────

    CONSTANT = "ATC-C800"
    CONSTANT_POOL_OVERFLOW = "ATC-C801"
    INVALID_CONSTANT = "ATC-C802"

    # ───────────────────────────────────────────────────────────────────
    # Optimizer
    # ───────────────────────────────────────────────────────────────────

    OPTIMIZATION = "ATC-C900"
    INVALID_OPTIMIZATION = "ATC-C901"

    # ───────────────────────────────────────────────────────────────────
    # Internal
    # ───────────────────────────────────────────────────────────────────

    INTERNAL = "ATC-C999"


# ═══════════════════════════════════════════════════════════════════════
# BASE COMPILER ERROR
# ═══════════════════════════════════════════════════════════════════════


class CompileError(Exception):
    """
    Basisklasse aller ATCLang Compiler-Fehler.
    """

    code = CompileErrorCode.GENERAL
    severity = ErrorSeverity.ERROR

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        node: Any = None,
        span: Optional[SourceSpan] = None,
        hint: Optional[str] = None,
        note: Optional[str] = None,
    ) -> None:

        self.message = message

        if code is not None:
            self.code = code

        self.hint = hint
        self.note = note

        if span is not None:
            self.span = span
        elif node is not None:
            self.span = SourceSpan.from_node(node)
        else:
            self.span = None

        self.diagnostic = CompilerDiagnostic(
            code=self.code,
            message=self.message,
            severity=self.severity,
            span=self.span,
            hint=self.hint,
            note=self.note,
        )

        super().__init__(
            self.diagnostic.format()
        )

    def format(self) -> str:
        return self.diagnostic.format()

    def __str__(self) -> str:
        return self.format()


# ═══════════════════════════════════════════════════════════════════════
# SYNTAX / AST ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileSyntaxError(CompileError):
    """Compiler-Syntax-/AST-Fehler."""

    code = CompileErrorCode.SYNTAX


class InvalidASTError(CompileError):
    """AST entspricht nicht den Compiler-Anforderungen."""

    code = CompileErrorCode.INVALID_AST


# ═══════════════════════════════════════════════════════════════════════
# SYMBOL / SCOPE ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileNameError(CompileError):
    """Fehler bei Symbolauflösung."""

    code = CompileErrorCode.NAME


class UndefinedSymbolError(CompileNameError):
    """Symbol wurde nicht gefunden."""

    code = CompileErrorCode.UNDEFINED_SYMBOL

    def __init__(
        self,
        name: str,
        *,
        node: Any = None,
        hint: Optional[str] = None,
    ) -> None:

        self.name = name

        super().__init__(
            f"Undefined symbol: '{name}'",
            node=node,
            hint=hint,
        )


class DuplicateSymbolError(CompileNameError):
    """Symbol wurde mehrfach definiert."""

    code = CompileErrorCode.DUPLICATE_SYMBOL

    def __init__(
        self,
        name: str,
        *,
        node: Any = None,
    ) -> None:

        self.name = name

        super().__init__(
            f"Symbol '{name}' is already defined",
            node=node,
        )


class InvalidScopeError(CompileNameError):
    """Ungültiger Scope-Kontext."""

    code = CompileErrorCode.INVALID_SCOPE


# ═══════════════════════════════════════════════════════════════════════
# TYPE ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileTypeError(CompileError):
    """Statischer Typfehler."""

    code = CompileErrorCode.TYPE


class TypeMismatchError(CompileTypeError):
    """Inkompatible Typen."""

    code = CompileErrorCode.TYPE_MISMATCH

    def __init__(
        self,
        expected: str,
        actual: str,
        *,
        node: Any = None,
        hint: Optional[str] = None,
    ) -> None:

        self.expected = expected
        self.actual = actual

        super().__init__(
            (
                f"Type mismatch: expected "
                f"'{expected}', got '{actual}'"
            ),
            node=node,
            hint=hint,
        )


class InvalidCastError(CompileTypeError):
    """Nicht erlaubter Cast."""

    code = CompileErrorCode.INVALID_CAST


class InvalidOperationError(CompileTypeError):
    """Nicht erlaubte Operation für einen Typ."""

    code = CompileErrorCode.INVALID_OPERATION


class UnknownTypeError(CompileTypeError):
    """Unbekannter Typ."""

    code = CompileErrorCode.UNKNOWN_TYPE


class InvalidGenericError(CompileTypeError):
    """Ungültige generische Typdefinition."""

    code = CompileErrorCode.INVALID_GENERIC


# ═══════════════════════════════════════════════════════════════════════
# CONTROL FLOW ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileControlFlowError(CompileError):
    """Fehler in der Kontrollflussanalyse."""

    code = CompileErrorCode.CONTROL_FLOW


class BreakOutsideLoopError(CompileControlFlowError):
    """break außerhalb einer Schleife."""

    code = CompileErrorCode.BREAK_OUTSIDE_LOOP


class ContinueOutsideLoopError(CompileControlFlowError):
    """continue außerhalb einer Schleife."""

    code = CompileErrorCode.CONTINUE_OUTSIDE_LOOP


class InvalidReturnError(CompileControlFlowError):
    """Ungültiges return."""

    code = CompileErrorCode.INVALID_RETURN


class UnreachableCodeError(CompileControlFlowError):
    """Nicht erreichbarer Code."""

    code = CompileErrorCode.UNREACHABLE_CODE


# ═══════════════════════════════════════════════════════════════════════
# FUNCTION ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileFunctionError(CompileError):
    """Fehler beim Kompilieren einer Funktion."""

    code = CompileErrorCode.FUNCTION


class InvalidCallError(CompileFunctionError):
    """Ungültiger Funktionsaufruf."""

    code = CompileErrorCode.INVALID_CALL


class ArgumentCountError(CompileFunctionError):
    """Falsche Anzahl von Argumenten."""

    code = CompileErrorCode.ARGUMENT_COUNT

    def __init__(
        self,
        function_name: str,
        expected: int,
        actual: int,
        *,
        node: Any = None,
    ) -> None:

        self.function_name = function_name
        self.expected = expected
        self.actual = actual

        super().__init__(
            (
                f"Function '{function_name}' expects "
                f"{expected} argument(s), got {actual}"
            ),
            node=node,
        )


class DuplicateParameterError(CompileFunctionError):
    """Doppelter Funktionsparameter."""

    code = CompileErrorCode.DUPLICATE_PARAMETER


class InvalidFunctionError(CompileFunctionError):
    """Ungültige Funktionsdefinition."""

    code = CompileErrorCode.INVALID_FUNCTION


# ═══════════════════════════════════════════════════════════════════════
# CONTRACT ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileContractError(CompileError):
    """Fehler beim Kompilieren eines Contracts."""

    code = CompileErrorCode.CONTRACT


class InvalidContractError(CompileContractError):
    """Ungültige Contract-Struktur."""

    code = CompileErrorCode.INVALID_CONTRACT


class InvalidStateError(CompileContractError):
    """Ungültiger Contract-State."""

    code = CompileErrorCode.INVALID_STATE


class InvalidEventError(CompileContractError):
    """Ungültige Event-Definition."""

    code = CompileErrorCode.INVALID_EVENT


class InvalidErrorDefinitionError(CompileContractError):
    """Ungültige Contract-Error-Definition."""

    code = CompileErrorCode.INVALID_ERROR


class InvalidStorageError(CompileContractError):
    """Ungültige Storage-Definition."""

    code = CompileErrorCode.INVALID_STORAGE


# ═══════════════════════════════════════════════════════════════════════
# BYTECODE ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileBytecodeError(CompileError):
    """Fehler beim Erzeugen von ATC-Bytecode."""

    code = CompileErrorCode.BYTECODE


class InvalidOpcodeError(CompileBytecodeError):
    """Ungültiger Opcode."""

    code = CompileErrorCode.INVALID_OPCODE


class InvalidOperandError(CompileBytecodeError):
    """Ungültiger Bytecode-Operand."""

    code = CompileErrorCode.INVALID_OPERAND


class InvalidJumpError(CompileBytecodeError):
    """Ungültiges Sprungziel."""

    code = CompileErrorCode.INVALID_JUMP


class InvalidBytecodeError(CompileBytecodeError):
    """Strukturell ungültiger Bytecode."""

    code = CompileErrorCode.INVALID_BYTECODE


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT POOL ERRORS
# ═══════════════════════════════════════════════════════════════════════


class ConstantPoolError(CompileError):
    """Fehler im Constant Pool."""

    code = CompileErrorCode.CONSTANT


class ConstantPoolOverflowError(ConstantPoolError):
    """Constant Pool hat die maximale Größe überschritten."""

    code = CompileErrorCode.CONSTANT_POOL_OVERFLOW


class InvalidConstantError(ConstantPoolError):
    """Ungültiger Constant-Pool-Eintrag."""

    code = CompileErrorCode.INVALID_CONSTANT


# ═══════════════════════════════════════════════════════════════════════
# OPTIMIZER ERRORS
# ═══════════════════════════════════════════════════════════════════════


class OptimizationError(CompileError):
    """Fehler während einer Optimierung."""

    code = CompileErrorCode.OPTIMIZATION


class InvalidOptimizationError(OptimizationError):
    """Optimierung erzeugt einen ungültigen Zustand."""

    code = CompileErrorCode.INVALID_OPTIMIZATION


# ═══════════════════════════════════════════════════════════════════════
# INTERNAL ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileInternalError(CompileError):
    """
    Interner Compilerfehler.

    Sollte im normalen ATCLang-Programmfluss nicht auftreten.
    """

    code = CompileErrorCode.INTERNAL


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════


def location_from_node(
    node: Any,
) -> Optional[SourceSpan]:
    """
    Konvertiert einen AST-Node sicher in einen SourceSpan.
    """

    if node is None:
        return None

    return SourceSpan.from_node(node)


def raise_compile_error(
    message: str,
    *,
    code: str = CompileErrorCode.GENERAL,
    node: Any = None,
    span: Optional[SourceSpan] = None,
    hint: Optional[str] = None,
    note: Optional[str] = None,
) -> None:
    """
    Convenience-Helper zum Werfen eines CompileError.
    """

    raise CompileError(
        message,
        code=code,
        node=node,
        span=span,
        hint=hint,
        note=note,
    )


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════


__all__ = [
    # Severity
    "ErrorSeverity",

    # Source
    "SourceLocation",
    "SourceSpan",

    # Diagnostics
    "CompilerDiagnostic",

    # Codes
    "CompileErrorCode",

    # Base
    "CompileError",

    # Syntax / AST
    "CompileSyntaxError",
    "InvalidASTError",

    # Symbols / Scope
    "CompileNameError",
    "UndefinedSymbolError",
    "DuplicateSymbolError",
    "InvalidScopeError",

    # Types
    "CompileTypeError",
    "TypeMismatchError",
    "InvalidCastError",
    "InvalidOperationError",
    "UnknownTypeError",
    "InvalidGenericError",

    # Control Flow
    "CompileControlFlowError",
    "BreakOutsideLoopError",
    "ContinueOutsideLoopError",
    "InvalidReturnError",
    "UnreachableCodeError",

    # Functions
    "CompileFunctionError",
    "InvalidCallError",
    "ArgumentCountError",
    "DuplicateParameterError",
    "InvalidFunctionError",

    # Contracts
    "CompileContractError",
    "InvalidContractError",
    "InvalidStateError",
    "InvalidEventError",
    "InvalidErrorDefinitionError",
    "InvalidStorageError",

    # Bytecode
    "CompileBytecodeError",
    "InvalidOpcodeError",
    "InvalidOperandError",
    "InvalidJumpError",
    "InvalidBytecodeError",

    # Constant Pool
    "ConstantPoolError",
    "ConstantPoolOverflowError",
    "InvalidConstantError",

    # Optimizer
    "OptimizationError",
    "InvalidOptimizationError",

    # Internal
    "CompileInternalError",

    # Helpers
    "location_from_node",
    "raise_compile_error",
]


__version__ = "0.3.0"