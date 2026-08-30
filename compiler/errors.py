# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Error Model
==============================

ATC-92 | Compiler Infrastructure

Zentrale Fehlerklassen für die Compiler-Pipeline:

    Source
      ↓
    Lexer
      ↓
    Parser
      ↓
    AST
      ↓
    TypeChecker
      ↓
    Compiler
      ↓
    Bytecode

Dieses Modul enthält ausschließlich Compiler-Fehler und deren
strukturierte Source-Location-Informationen.

Designziele:
    - stabile öffentliche Error-API
    - maschinenlesbare Fehler
    - präzise Source Locations
    - kompatibel mit CLI / IDE / LSP / Tests
    - keine Abhängigkeit vom VM-Runtime-Code
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Optional, Sequence


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE LOCATION
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """
    Position innerhalb einer ATCLang-Quelldatei.

    line/column sind 1-basiert.
    offset ist 0-basiert und optional.
    """

    line: int = 1
    column: int = 1
    offset: Optional[int] = None

    def __post_init__(self) -> None:
        if self.line < 1:
            raise ValueError("SourceLocation.line must be >= 1")

        if self.column < 1:
            raise ValueError("SourceLocation.column must be >= 1")

        if self.offset is not None and self.offset < 0:
            raise ValueError("SourceLocation.offset must be >= 0")

    def __str__(self) -> str:
        return f"{self.line}:{self.column}"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """
    Bereich innerhalb einer ATCLang-Quelldatei.

    end_line/end_column sind inklusive der konzeptionellen
    Endposition und werden für Diagnostics verwendet.
    """

    start: SourceLocation
    end: Optional[SourceLocation] = None
    filename: Optional[str] = None

    @classmethod
    def from_node(cls, node: Any) -> "SourceSpan":
        """
        Erstellt einen SourceSpan aus einem AST-/Token-ähnlichen Objekt.

        Unterstützt typische Attribute:
            line
            col
            column
            end_line
            end_col
            end_column
            filename
        """

        line = getattr(node, "line", 1)
        column = getattr(
            node,
            "column",
            getattr(node, "col", 1),
        )

        end_line = getattr(node, "end_line", None)
        end_column = getattr(
            node,
            "end_column",
            getattr(node, "end_col", None),
        )

        filename = getattr(node, "filename", None)

        start = SourceLocation(
            line=max(1, int(line)),
            column=max(1, int(column)),
        )

        end = None

        if end_line is not None or end_column is not None:
            end = SourceLocation(
                line=max(1, int(end_line if end_line is not None else line)),
                column=max(
                    1,
                    int(
                        end_column
                        if end_column is not None
                        else column
                    ),
                ),
            )

        return cls(
            start=start,
            end=end,
            filename=filename,
        )

    def format(self) -> str:
        location = str(self.start)

        if self.filename:
            return f"{self.filename}:{location}"

        return location

    def __str__(self) -> str:
        return self.format()


# ══════════════════════════════════════════════════════════════════════════════
# ERROR SEVERITY
# ══════════════════════════════════════════════════════════════════════════════


class ErrorSeverity(str, Enum):
    """Severity einer Compiler-Diagnostic."""

    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


# ══════════════════════════════════════════════════════════════════════════════
# ERROR CODES
# ══════════════════════════════════════════════════════════════════════════════


class CompilerErrorCode(str, Enum):
    """
    Stabile ATCLang Compiler Error Codes.

    Die Codes sind absichtlich unabhängig von konkreten Python-Exceptions.
    """

    # General
    INTERNAL_ERROR = "ATC-C000"
    INVALID_STATE = "ATC-C001"
    UNSUPPORTED_FEATURE = "ATC-C002"

    # Symbols
    UNDEFINED_SYMBOL = "ATC-C100"
    DUPLICATE_SYMBOL = "ATC-C101"
    INVALID_SYMBOL = "ATC-C102"
    INVALID_SCOPE = "ATC-C103"

    # Expressions
    INVALID_EXPRESSION = "ATC-C200"
    INVALID_OPERATOR = "ATC-C201"
    INVALID_ASSIGNMENT = "ATC-C202"
    INVALID_CALL = "ATC-C203"

    # Statements
    INVALID_STATEMENT = "ATC-C300"
    BREAK_OUTSIDE_LOOP = "ATC-C301"
    CONTINUE_OUTSIDE_LOOP = "ATC-C302"
    RETURN_OUTSIDE_FUNCTION = "ATC-C303"

    # Functions
    FUNCTION_NOT_FOUND = "ATC-C400"
    DUPLICATE_FUNCTION = "ATC-C401"
    INVALID_FUNCTION = "ATC-C402"
    INVALID_ARGUMENT_COUNT = "ATC-C403"

    # Contracts
    INVALID_CONTRACT = "ATC-C500"
    DUPLICATE_CONTRACT = "ATC-C501"
    INVALID_STATE_FIELD = "ATC-C502"
    INVALID_EVENT = "ATC-C503"

    # Bytecode
    INVALID_OPCODE = "ATC-C600"
    INVALID_OPERAND = "ATC-C601"
    INVALID_JUMP = "ATC-C602"
    BYTECODE_GENERATION_FAILED = "ATC-C603"

    # Types
    TYPE_ERROR = "ATC-C700"
    TYPE_MISMATCH = "ATC-C701"
    INVALID_CAST = "ATC-C702"

    # Imports / modules
    IMPORT_ERROR = "ATC-C800"
    MODULE_NOT_FOUND = "ATC-C801"

    # Optimization
    OPTIMIZATION_ERROR = "ATC-C900"


# ══════════════════════════════════════════════════════════════════════════════
# DIAGNOSTIC
# ══════════════════════════════════════════════════════════════════════════════


@dataclass(slots=True)
class Diagnostic:
    """
    Strukturierte Compiler-Diagnostic.

    Diagnostics können von CLI, IDE, LSP oder Testsystemen
    direkt verarbeitet werden.
    """

    message: str
    severity: ErrorSeverity = ErrorSeverity.ERROR
    code: Optional[CompilerErrorCode | str] = None
    span: Optional[SourceSpan] = None

    hint: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    details: dict[str, Any] = field(default_factory=dict)

    def formatted(self) -> str:
        """
        Menschenlesbare Darstellung.
        """

        prefix = self.severity.value

        if self.code is not None:
            code = (
                self.code.value
                if isinstance(self.code, Enum)
                else str(self.code)
            )
            prefix = f"{prefix}[{code}]"

        if self.span:
            return f"{self.span}: {prefix}: {self.message}"

        return f"{prefix}: {self.message}"

    def __str__(self) -> str:
        return self.formatted()


# ══════════════════════════════════════════════════════════════════════════════
# BASE COMPILER ERROR
# ══════════════════════════════════════════════════════════════════════════════


class ATCCompilerError(Exception):
    """
    Basisklasse für alle ATCLang Compiler-Fehler.
    """

    default_code = CompilerErrorCode.INTERNAL_ERROR

    def __init__(
        self,
        message: str,
        *,
        code: CompilerErrorCode | str | None = None,
        node: Any = None,
        span: Optional[SourceSpan] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        filename: Optional[str] = None,
        hint: Optional[str] = None,
        notes: Optional[Iterable[str]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:

        if span is None and node is not None:
            span = SourceSpan.from_node(node)

        if span is None and line is not None:
            span = SourceSpan(
                start=SourceLocation(
                    line=max(1, line),
                    column=max(1, column or 1),
                ),
                filename=filename,
            )

        self.message = message
        self.code = code or self.default_code
        self.span = span
        self.hint = hint
        self.notes = list(notes or [])
        self.details = dict(details or {})

        self.diagnostic = Diagnostic(
            message=message,
            severity=ErrorSeverity.ERROR,
            code=self.code,
            span=self.span,
            hint=self.hint,
            notes=self.notes,
            details=self.details,
        )

        super().__init__(self.diagnostic.formatted())

    def formatted(self) -> str:
        return self.diagnostic.formatted()


# ══════════════════════════════════════════════════════════════════════════════
# SPECIALIZED ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class CompileError(ATCCompilerError):
    """Generischer Compilerfehler."""

    default_code = CompilerErrorCode.BYTECODE_GENERATION_FAILED


class SymbolError(ATCCompilerError):
    """Fehler in Symbolauflösung oder Symbolverwaltung."""

    default_code = CompilerErrorCode.INVALID_SYMBOL


class UndefinedSymbolError(SymbolError):
    """Symbol konnte nicht aufgelöst werden."""

    default_code = CompilerErrorCode.UNDEFINED_SYMBOL

    def __init__(
        self,
        name: str,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Undefined symbol '{name}'",
            code=self.default_code,
            node=node,
            span=span,
            details={"symbol": name},
        )


class DuplicateSymbolError(SymbolError):
    """Symbol wurde innerhalb desselben Scopes doppelt definiert."""

    default_code = CompilerErrorCode.DUPLICATE_SYMBOL

    def __init__(
        self,
        name: str,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Duplicate symbol '{name}'",
            code=self.default_code,
            node=node,
            span=span,
            details={"symbol": name},
        )


# ══════════════════════════════════════════════════════════════════════════════
# EXPRESSION ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class ExpressionError(ATCCompilerError):
    """Fehler beim Kompilieren eines Ausdrucks."""

    default_code = CompilerErrorCode.INVALID_EXPRESSION


class InvalidOperatorError(ExpressionError):
    """Unbekannter oder nicht unterstützter Operator."""

    default_code = CompilerErrorCode.INVALID_OPERATOR

    def __init__(
        self,
        operator: str,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Unsupported operator '{operator}'",
            code=self.default_code,
            node=node,
            span=span,
            details={"operator": operator},
        )


class InvalidAssignmentError(ExpressionError):
    """Ungültiges Assignment-Ziel."""

    default_code = CompilerErrorCode.INVALID_ASSIGNMENT


class InvalidCallError(ExpressionError):
    """Ungültiger Funktionsaufruf."""

    default_code = CompilerErrorCode.INVALID_CALL


# ══════════════════════════════════════════════════════════════════════════════
# STATEMENT ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class StatementError(ATCCompilerError):
    """Fehler beim Kompilieren eines Statements."""

    default_code = CompilerErrorCode.INVALID_STATEMENT


class BreakOutsideLoopError(StatementError):
    """break wurde außerhalb einer Schleife verwendet."""

    default_code = CompilerErrorCode.BREAK_OUTSIDE_LOOP

    def __init__(
        self,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            "'break' used outside of a loop",
            code=self.default_code,
            node=node,
            span=span,
        )


class ContinueOutsideLoopError(StatementError):
    """continue wurde außerhalb einer Schleife verwendet."""

    default_code = CompilerErrorCode.CONTINUE_OUTSIDE_LOOP

    def __init__(
        self,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            "'continue' used outside of a loop",
            code=self.default_code,
            node=node,
            span=span,
        )


class ReturnOutsideFunctionError(StatementError):
    """return wurde außerhalb einer Funktion verwendet."""

    default_code = CompilerErrorCode.RETURN_OUTSIDE_FUNCTION

    def __init__(
        self,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            "'return' used outside of a function",
            code=self.default_code,
            node=node,
            span=span,
        )


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class FunctionError(ATCCompilerError):
    """Fehler bei Funktionen."""

    default_code = CompilerErrorCode.INVALID_FUNCTION


class FunctionNotFoundError(FunctionError):
    """Aufgerufene Funktion existiert nicht."""

    default_code = CompilerErrorCode.FUNCTION_NOT_FOUND

    def __init__(
        self,
        name: str,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Function '{name}' not found",
            code=self.default_code,
            node=node,
            span=span,
            details={"function": name},
        )


class DuplicateFunctionError(FunctionError):
    """Funktion wurde doppelt definiert."""

    default_code = CompilerErrorCode.DUPLICATE_FUNCTION

    def __init__(
        self,
        name: str,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Duplicate function '{name}'",
            code=self.default_code,
            node=node,
            span=span,
            details={"function": name},
        )


class InvalidArgumentCountError(FunctionError):
    """Falsche Anzahl von Funktionsargumenten."""

    default_code = CompilerErrorCode.INVALID_ARGUMENT_COUNT

    def __init__(
        self,
        function: str,
        expected: int,
        actual: int,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            (
                f"Function '{function}' expects "
                f"{expected} argument(s), got {actual}"
            ),
            code=self.default_code,
            node=node,
            span=span,
            details={
                "function": function,
                "expected": expected,
                "actual": actual,
            },
        )


# ══════════════════════════════════════════════════════════════════════════════
# CONTRACT ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class ContractError(ATCCompilerError):
    """Fehler bei Contract-Kompilierung."""

    default_code = CompilerErrorCode.INVALID_CONTRACT


class DuplicateContractError(ContractError):
    """Contract wurde doppelt definiert."""

    default_code = CompilerErrorCode.DUPLICATE_CONTRACT

    def __init__(
        self,
        name: str,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Duplicate contract '{name}'",
            code=self.default_code,
            node=node,
            span=span,
            details={"contract": name},
        )


class InvalidStateFieldError(ContractError):
    """Ungültiges Contract-State-Feld."""

    default_code = CompilerErrorCode.INVALID_STATE_FIELD


class InvalidEventError(ContractError):
    """Ungültiges Event."""

    default_code = CompilerErrorCode.INVALID_EVENT


# ══════════════════════════════════════════════════════════════════════════════
# BYTECODE ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class BytecodeError(ATCCompilerError):
    """Fehler bei Bytecode-Erzeugung."""

    default_code = CompilerErrorCode.BYTECODE_GENERATION_FAILED


class InvalidOpcodeError(BytecodeError):
    """Opcode ist ungültig oder unbekannt."""

    default_code = CompilerErrorCode.INVALID_OPCODE

    def __init__(
        self,
        opcode: Any,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Invalid opcode: {opcode!r}",
            code=self.default_code,
            node=node,
            span=span,
            details={"opcode": repr(opcode)},
        )


class InvalidOperandError(BytecodeError):
    """Opcode-Operand ist ungültig."""

    default_code = CompilerErrorCode.INVALID_OPERAND


class InvalidJumpError(BytecodeError):
    """Ungültiges Jump-Ziel."""

    default_code = CompilerErrorCode.INVALID_JUMP

    def __init__(
        self,
        target: Any,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Invalid jump target: {target!r}",
            code=self.default_code,
            node=node,
            span=span,
            details={"target": target},
        )


# ══════════════════════════════════════════════════════════════════════════════
# TYPE ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class CompilerTypeError(ATCCompilerError):
    """Compiler-seitiger Type Error."""

    default_code = CompilerErrorCode.TYPE_ERROR


class TypeMismatchError(CompilerTypeError):
    """Zwei inkompatible Typen wurden kombiniert."""

    default_code = CompilerErrorCode.TYPE_MISMATCH

    def __init__(
        self,
        expected: str,
        actual: str,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Type mismatch: expected '{expected}', got '{actual}'",
            code=self.default_code,
            node=node,
            span=span,
            details={
                "expected": expected,
                "actual": actual,
            },
        )


class InvalidCastError(CompilerTypeError):
    """Ungültiger Cast."""

    default_code = CompilerErrorCode.INVALID_CAST


# ══════════════════════════════════════════════════════════════════════════════
# MODULE / IMPORT ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class ModuleError(ATCCompilerError):
    """Fehler bei Modulen und Imports."""

    default_code = CompilerErrorCode.IMPORT_ERROR


class ModuleNotFoundError(ModuleError):
    """Importiertes Modul konnte nicht gefunden werden."""

    default_code = CompilerErrorCode.MODULE_NOT_FOUND

    def __init__(
        self,
        module: str,
        *,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> None:
        super().__init__(
            f"Module '{module}' not found",
            code=self.default_code,
            node=node,
            span=span,
            details={"module": module},
        )


# ══════════════════════════════════════════════════════════════════════════════
# OPTIMIZER ERRORS
# ══════════════════════════════════════════════════════════════════════════════


class OptimizerError(ATCCompilerError):
    """Fehler innerhalb des Optimizers."""

    default_code = CompilerErrorCode.OPTIMIZATION_ERROR


# ══════════════════════════════════════════════════════════════════════════════
# ERROR COLLECTION
# ══════════════════════════════════════════════════════════════════════════════


class DiagnosticBag:
    """
    Sammlung von Compiler-Diagnostics.

    Ermöglicht Fehlerakkumulation ohne sofortigen Abbruch.

    Verwendung:

        diagnostics = DiagnosticBag()

        diagnostics.error(...)
        diagnostics.warning(...)

        if diagnostics.has_errors:
            diagnostics.raise_if_errors()
    """

    def __init__(self) -> None:
        self._items: list[Diagnostic] = []

    @property
    def diagnostics(self) -> list[Diagnostic]:
        return list(self._items)

    @property
    def errors(self) -> list[Diagnostic]:
        return [
            item
            for item in self._items
            if item.severity == ErrorSeverity.ERROR
        ]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [
            item
            for item in self._items
            if item.severity == ErrorSeverity.WARNING
        ]

    @property
    def has_errors(self) -> bool:
        return any(
            item.severity == ErrorSeverity.ERROR
            for item in self._items
        )

    @property
    def has_warnings(self) -> bool:
        return any(
            item.severity == ErrorSeverity.WARNING
            for item in self._items
        )

    def add(self, diagnostic: Diagnostic) -> Diagnostic:
        self._items.append(diagnostic)
        return diagnostic

    def error(
        self,
        message: str,
        *,
        code: CompilerErrorCode | str | None = None,
        node: Any = None,
        span: Optional[SourceSpan] = None,
        hint: Optional[str] = None,
        notes: Optional[Iterable[str]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> Diagnostic:

        if span is None and node is not None:
            span = SourceSpan.from_node(node)

        diagnostic = Diagnostic(
            message=message,
            severity=ErrorSeverity.ERROR,
            code=code,
            span=span,
            hint=hint,
            notes=list(notes or []),
            details=dict(details or {}),
        )

        return self.add(diagnostic)

    def warning(
        self,
        message: str,
        *,
        code: CompilerErrorCode | str | None = None,
        node: Any = None,
        span: Optional[SourceSpan] = None,
        hint: Optional[str] = None,
        notes: Optional[Iterable[str]] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> Diagnostic:

        if span is None and node is not None:
            span = SourceSpan.from_node(node)

        diagnostic = Diagnostic(
            message=message,
            severity=ErrorSeverity.WARNING,
            code=code,
            span=span,
            hint=hint,
            notes=list(notes or []),
            details=dict(details or {}),
        )

        return self.add(diagnostic)

    def note(
        self,
        message: str,
        *,
        code: CompilerErrorCode | str | None = None,
        node: Any = None,
        span: Optional[SourceSpan] = None,
    ) -> Diagnostic:

        if span is None and node is not None:
            span = SourceSpan.from_node(node)

        diagnostic = Diagnostic(
            message=message,
            severity=ErrorSeverity.NOTE,
            code=code,
            span=span,
        )

        return self.add(diagnostic)

    def extend(self, diagnostics: Iterable[Diagnostic]) -> None:
        self._items.extend(diagnostics)

    def clear(self) -> None:
        self._items.clear()

    def raise_if_errors(self) -> None:
        """
        Bricht mit dem ersten Fehler ab.

        Für Multi-Error-Ausgabe kann der Aufrufer zuerst
        diagnostics.errors auswerten.
        """

        if self.has_errors:
            first = self.errors[0]
            raise ATCCompilerError(
                first.message,
                code=first.code,
                span=first.span,
                hint=first.hint,
                notes=first.notes,
                details=first.details,
            )


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def error_from_node(
    message: str,
    node: Any,
    *,
    code: CompilerErrorCode | str = CompilerErrorCode.INTERNAL_ERROR,
    exc_type: type[ATCCompilerError] = ATCCompilerError,
) -> ATCCompilerError:
    """
    Komfortfunktion für Compiler-Module.

    Beispiel:

        raise error_from_node(
            "Unknown expression",
            node,
            code=CompilerErrorCode.INVALID_EXPRESSION,
        )
    """

    return exc_type(
        message,
        code=code,
        node=node,
    )


def format_error(error: BaseException) -> str:
    """
    Formatiert Compilerfehler einheitlich.

    Nicht-Compiler-Exceptions werden ebenfalls sicher dargestellt.
    """

    if isinstance(error, ATCCompilerError):
        return error.formatted()

    return f"internal error: {error}"


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════


__all__ = [
    # Source
    "SourceLocation",
    "SourceSpan",

    # Diagnostics
    "ErrorSeverity",
    "Diagnostic",
    "DiagnosticBag",

    # Codes
    "CompilerErrorCode",

    # Base errors
    "ATCCompilerError",
    "CompileError",

    # Symbols
    "SymbolError",
    "UndefinedSymbolError",
    "DuplicateSymbolError",

    # Expressions
    "ExpressionError",
    "InvalidOperatorError",
    "InvalidAssignmentError",
    "InvalidCallError",

    # Statements
    "StatementError",
    "BreakOutsideLoopError",
    "ContinueOutsideLoopError",
    "ReturnOutsideFunctionError",

    # Functions
    "FunctionError",
    "FunctionNotFoundError",
    "DuplicateFunctionError",
    "InvalidArgumentCountError",

    # Contracts
    "ContractError",
    "DuplicateContractError",
    "InvalidStateFieldError",
    "InvalidEventError",

    # Bytecode
    "BytecodeError",
    "InvalidOpcodeError",
    "InvalidOperandError",
    "InvalidJumpError",

    # Types
    "CompilerTypeError",
    "TypeMismatchError",
    "InvalidCastError",

    # Modules
    "ModuleError",
    "ModuleNotFoundError",

    # Optimizer
    "OptimizerError",

    # Helpers
    "error_from_node",
    "format_error",
]