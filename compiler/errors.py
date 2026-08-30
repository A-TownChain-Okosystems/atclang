# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler Errors
=======================

Zentrales Error-System für den ATCLang Compiler.

Architektur:

    Lexer / Parser
          │
          ▼
       AST
          │
          ▼
    TypeChecker
          │
          ▼
    Compiler Errors
          │
          ├── CompileError
          ├── CompileSyntaxError
          ├── CompileNameError
          ├── CompileTypeError
          ├── CompileControlFlowError
          ├── CompileBytecodeError
          ├── CompileSymbolError
          └── CompileInternalError

Design-Ziele
------------

- Keine Abhängigkeit zu Parser oder VM
- Keine Abhängigkeit zu Compiler-Modulen
- Strukturierte Fehler statt String-only Exceptions
- Source-Location-Unterstützung
- Fehlercodes für Tooling / IDE / CI
- Deterministische Formatierung
- Kompatibel mit Compiler-Pipeline und späterem LSP
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


# ═══════════════════════════════════════════════════════════════════════
# ERROR SEVERITY
# ═══════════════════════════════════════════════════════════════════════


class ErrorSeverity(str, Enum):
    """Severity eines Compiler-Diagnoseeintrags."""

    ERROR = "error"
    WARNING = "warning"
    NOTE = "note"


# ═══════════════════════════════════════════════════════════════════════
# SOURCE LOCATION
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SourceLocation:
    """
    Position innerhalb des ATCLang-Quellcodes.

    line und column sind 1-basiert.
    end_line/end_column sind optional und können einen Bereich markieren.
    """

    line: int = 0
    column: int = 0
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    def __post_init__(self) -> None:
        if self.line < 0:
            raise ValueError("SourceLocation.line darf nicht negativ sein")

        if self.column < 0:
            raise ValueError("SourceLocation.column darf nicht negativ sein")

        if self.end_line is not None and self.end_line < 0:
            raise ValueError("SourceLocation.end_line darf nicht negativ sein")

        if self.end_column is not None and self.end_column < 0:
            raise ValueError("SourceLocation.end_column darf nicht negativ sein")

    @property
    def is_known(self) -> bool:
        """Gibt an, ob eine gültige Source-Position vorhanden ist."""
        return self.line > 0

    def format(self) -> str:
        """Formatiert die Position für Compiler-Meldungen."""
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
    Source-Bereich.

    Unterstützt sowohl einzelne Positionen als auch mehrzeilige Bereiche.
    """

    start: SourceLocation
    end: Optional[SourceLocation] = None

    @classmethod
    def from_node(cls, node: Any) -> "SourceSpan":
        """
        Erstellt einen SourceSpan aus einem AST-Node.

        Erwartete Attribute:
            line
            col / column
            end_line
            end_col / end_column
        """

        line = int(getattr(node, "line", 0) or 0)

        column = getattr(node, "column", None)
        if column is None:
            column = getattr(node, "col", 0)

        end_line = getattr(node, "end_line", None)

        end_column = getattr(node, "end_column", None)
        if end_column is None:
            end_column = getattr(node, "end_col", None)

        start = SourceLocation(
            line=line,
            column=int(column or 0),
            end_line=end_line,
            end_column=end_column,
        )

        end = None

        if end_line is not None or end_column is not None:
            end = SourceLocation(
                line=int(end_line or line),
                column=int(end_column or 0),
            )

        return cls(start=start, end=end)

    @property
    def line(self) -> int:
        return self.start.line

    @property
    def column(self) -> int:
        return self.start.column

    def format(self) -> str:
        if self.end is None:
            return self.start.format()

        start = self.start.format()
        end = self.end.format()

        if start == end:
            return start

        return f"{start}-{end}"


# ═══════════════════════════════════════════════════════════════════════
# COMPILER DIAGNOSTIC
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class CompilerDiagnostic:
    """
    Strukturierte Compiler-Diagnose.

    Diese Struktur kann später direkt von:
        - CLI
        - IDE
        - LSP
        - JSON diagnostics
        - CI
    verwendet werden.
    """

    code: str
    message: str
    severity: ErrorSeverity = ErrorSeverity.ERROR
    span: Optional[SourceSpan] = None
    hint: Optional[str] = None
    note: Optional[str] = None

    def format(self) -> str:
        """Menschenlesbare Compiler-Diagnose."""

        location = ""

        if self.span is not None:
            formatted_span = self.span.format()

            if formatted_span:
                location = f" @ {formatted_span}"

        result = (
            f"[{self.code}] "
            f"{self.severity.value}{location}: "
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
    Zentrale Compiler-Error-Codes.

    Format:

        ATC-Cxxx

    x = Kategorie.
    """

    GENERAL = "ATC-C000"

    SYNTAX = "ATC-C100"
    INVALID_AST = "ATC-C101"

    NAME = "ATC-C200"
    UNDEFINED_SYMBOL = "ATC-C201"
    DUPLICATE_SYMBOL = "ATC-C202"

    TYPE = "ATC-C300"
    TYPE_MISMATCH = "ATC-C301"
    INVALID_CAST = "ATC-C302"
    INVALID_OPERATION = "ATC-C303"

    CONTROL_FLOW = "ATC-C400"
    BREAK_OUTSIDE_LOOP = "ATC-C401"
    CONTINUE_OUTSIDE_LOOP = "ATC-C402"
    INVALID_RETURN = "ATC-C403"

    FUNCTION = "ATC-C500"
    INVALID_CALL = "ATC-C501"
    ARGUMENT_COUNT = "ATC-C502"
    DUPLICATE_PARAMETER = "ATC-C503"

    CONTRACT = "ATC-C600"
    INVALID_CONTRACT = "ATC-C601"
    INVALID_STATE = "ATC-C602"

    BYTECODE = "ATC-C700"
    INVALID_OPCODE = "ATC-C701"
    INVALID_OPERAND = "ATC-C702"
    INVALID_JUMP = "ATC-C703"

    CONSTANT = "ATC-C800"
    CONSTANT_POOL_OVERFLOW = "ATC-C801"

    OPTIMIZATION = "ATC-C900"

    INTERNAL = "ATC-C999"


# ═══════════════════════════════════════════════════════════════════════
# BASE ERROR
# ═══════════════════════════════════════════════════════════════════════


class CompileError(Exception):
    """
    Basisklasse aller ATCLang Compiler-Fehler.

    Beispiel:

        raise CompileError(
            "Symbol konnte nicht aufgelöst werden",
            code=CompileErrorCode.UNDEFINED_SYMBOL,
            node=node,
        )
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
        self.code = code or self.code
        self.severity = self.severity
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

        super().__init__(self.diagnostic.format())

    def format(self) -> str:
        return self.diagnostic.format()

    def __str__(self) -> str:
        return self.format()


# ═══════════════════════════════════════════════════════════════════════
# SPECIALIZED ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileSyntaxError(CompileError):
    """Fehlerhafte AST-/Syntax-Struktur."""

    code = CompileErrorCode.SYNTAX


class InvalidASTError(CompileError):
    """AST entspricht nicht den Compiler-Anforderungen."""

    code = CompileErrorCode.INVALID_AST


class CompileNameError(CompileError):
    """Fehler bei Symbolauflösung."""

    code = CompileErrorCode.NAME


class UndefinedSymbolError(CompileNameError):
    """Symbol ist nicht definiert."""

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


class CompileTypeError(CompileError):
    """Statischer Typfehler."""

    code = CompileErrorCode.TYPE


class TypeMismatchError(CompileTypeError):
    """Zwei inkompatible Typen wurden verwendet."""

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
            f"Type mismatch: expected '{expected}', got '{actual}'",
            node=node,
            hint=hint,
        )


class InvalidCastError(CompileTypeError):
    """Nicht erlaubter Cast."""

    code = CompileErrorCode.INVALID_CAST


class InvalidOperationError(CompileTypeError):
    """Nicht erlaubte Operation für einen Typ."""

    code = CompileErrorCode.INVALID_OPERATION


class CompileControlFlowError(CompileError):
    """Fehler in der Kontrollflussstruktur."""

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
    """Parametername wurde innerhalb einer Funktion doppelt verwendet."""

    code = CompileErrorCode.DUPLICATE_PARAMETER


class CompileContractError(CompileError):
    """Fehler beim Kompilieren eines Contracts."""

    code = CompileErrorCode.CONTRACT


class InvalidContractError(CompileContractError):
    """Ungültige Contract-Struktur."""

    code = CompileErrorCode.INVALID_CONTRACT


class InvalidStateError(CompileContractError):
    """Ungültiges Contract-State-Feld."""

    code = CompileErrorCode.INVALID_STATE


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


class ConstantPoolError(CompileError):
    """Fehler im Constant Pool."""

    code = CompileErrorCode.CONSTANT


class ConstantPoolOverflowError(ConstantPoolError):
    """Constant Pool hat seine maximale Größe überschritten."""

    code = CompileErrorCode.CONSTANT_POOL_OVERFLOW


class OptimizationError(CompileError):
    """Fehler während einer Compiler-Optimierung."""

    code = CompileErrorCode.OPTIMIZATION


class CompileInternalError(CompileError):
    """
    Interner Compilerfehler.

    Diese Fehler sollten im normalen ATCLang-Programmfluss
    nicht auftreten.
    """

    code = CompileErrorCode.INTERNAL


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════


def location_from_node(node: Any) -> Optional[SourceSpan]:
    """
    Sicherer Helper für Compiler-Module.

    Gibt None zurück, wenn kein Node vorhanden ist.
    """

    if node is None:
        return None

    return SourceSpan.from_node(node)


def raise_compile_error(
    message: str,
    *,
    code: str = CompileErrorCode.GENERAL,
    node: Any = None,
    hint: Optional[str] = None,
    note: Optional[str] = None,
) -> None:
    """
    Convenience Helper für Compiler-Module.
    """

    raise CompileError(
        message,
        code=code,
        node=node,
        hint=hint,
        note=note,
    )


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════


__all__ = [
    # Severity
    "ErrorSeverity",

    # Source information
    "SourceLocation",
    "SourceSpan",

    # Diagnostics
    "CompilerDiagnostic",

    # Error codes
    "CompileErrorCode",

    # Base error
    "CompileError",

    # AST / syntax
    "CompileSyntaxError",
    "InvalidASTError",

    # Symbols
    "CompileNameError",
    "UndefinedSymbolError",
    "DuplicateSymbolError",

    # Types
    "CompileTypeError",
    "TypeMismatchError",
    "InvalidCastError",
    "InvalidOperationError",

    # Control flow
    "CompileControlFlowError",
    "BreakOutsideLoopError",
    "ContinueOutsideLoopError",
    "InvalidReturnError",

    # Functions
    "CompileFunctionError",
    "InvalidCallError",
    "ArgumentCountError",
    "DuplicateParameterError",

    # Contracts
    "CompileContractError",
    "InvalidContractError",
    "InvalidStateError",

    # Bytecode
    "CompileBytecodeError",
    "InvalidOpcodeError",
    "InvalidOperandError",
    "InvalidJumpError",

    # Constants
    "ConstantPoolError",
    "ConstantPoolOverflowError",

    # Optimization
    "OptimizationError",

    # Internal
    "CompileInternalError",

    # Helpers
    "location_from_node",
    "raise_compile_error",
]


__version__ = "0.3.0"