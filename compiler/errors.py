# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler Errors
=======================

Zentrales, unabhängiges Error- und Diagnostic-System des Compilers.

Dependency Rule
---------------

errors.py darf KEINE Abhängigkeit auf andere Compiler-Module besitzen.

Erlaubt:

    source_map.py
        ↓
    errors.py

    constants.py
        ↓
    errors.py

    symbols.py
        ↓
    errors.py

    context.py
        ↓
    errors.py

    ...

Nicht erlaubt:

    errors.py
        ↓
    source_map.py

oder:

    errors.py
        ↓
    compiler.py

Dadurch bleibt errors.py die unterste Compiler-Schicht
und verhindert zyklische Imports.
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

    Beispiel:

        line=12
        column=7
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
        """Gibt an, ob eine gültige Source-Position vorhanden ist."""

        return self.line > 0

    def format(self) -> str:
        """Formatiert die Position für Diagnostics."""

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

        line = int(getattr(node, "line", 0) or 0)

        column = getattr(node, "column", None)

        if column is None:
            column = getattr(node, "col", 0)

        column = int(column or 0)

        start = SourceLocation(
            line=line,
            column=column,
        )

        end_line = getattr(node, "end_line", None)

        end_column = getattr(node, "end_column", None)

        if end_column is None:
            end_column = getattr(node, "end_col", None)

        if end_line is None and end_column is None:
            return cls(start=start)

        end = SourceLocation(
            line=int(end_line if end_line is not None else line),
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

    Diese Struktur kann direkt von folgenden Systemen
    verwendet werden:

        - CLI
        - IDE
        - LSP
        - CI
        - JSON Diagnostics
        - Testsystem
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
    Zentrale ATCLang Compiler Error Codes.

    ATC-Cxxx

    Kategorien:

        C0xx  General
        C1xx  Syntax / AST
        C2xx  Symbols
        C3xx  Types
        C4xx  Control Flow
        C5xx  Functions
        C6xx  Contracts
        C7xx  Bytecode
        C8xx  Constants
        C9xx  Optimization
        C999  Internal
    """

    # General
    GENERAL = "ATC-C000"

    # Syntax / AST
    SYNTAX = "ATC-C100"
    INVALID_AST = "ATC-C101"

    # Symbols
    NAME = "ATC-C200"
    UNDEFINED_SYMBOL = "ATC-C201"
    DUPLICATE_SYMBOL = "ATC-C202"

    # Types
    TYPE = "ATC-C300"
    TYPE_MISMATCH = "ATC-C301"
    INVALID_CAST = "ATC-C302"
    INVALID_OPERATION = "ATC-C303"

    # Control Flow
    CONTROL_FLOW = "ATC-C400"
    BREAK_OUTSIDE_LOOP = "ATC-C401"
    CONTINUE_OUTSIDE_LOOP = "ATC-C402"
    INVALID_RETURN = "ATC-C403"

    # Functions
    FUNCTION = "ATC-C500"
    INVALID_CALL = "ATC-C501"
    ARGUMENT_COUNT = "ATC-C502"
    DUPLICATE_PARAMETER = "ATC-C503"

    # Contracts
    CONTRACT = "ATC-C600"
    INVALID_CONTRACT = "ATC-C601"
    INVALID_STATE = "ATC-C602"

    # Bytecode
    BYTECODE = "ATC-C700"
    INVALID_OPCODE = "ATC-C701"
    INVALID_OPERAND = "ATC-C702"
    INVALID_JUMP = "ATC-C703"

    # Constant Pool
    CONSTANT = "ATC-C800"
    CONSTANT_POOL_OVERFLOW = "ATC-C801"

    # Optimizer
    OPTIMIZATION = "ATC-C900"

    # Internal
    INTERNAL = "ATC-C999"


# ═══════════════════════════════════════════════════════════════════════
# BASE COMPILER ERROR
# ═══════════════════════════════════════════════════════════════════════


class CompileError(Exception):
    """
    Basisklasse aller ATCLang Compiler-Fehler.

    Compiler-Module sollten bevorzugt strukturierte
    Subklassen verwenden.
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
# SYNTAX / AST
# ═══════════════════════════════════════════════════════════════════════


class CompileSyntaxError(CompileError):
    code = CompileErrorCode.SYNTAX


class InvalidASTError(CompileError):
    code = CompileErrorCode.INVALID_AST


# ═══════════════════════════════════════════════════════════════════════
# SYMBOL ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileNameError(CompileError):
    code = CompileErrorCode.NAME


class UndefinedSymbolError(CompileNameError):
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


# ═══════════════════════════════════════════════════════════════════════
# TYPE ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileTypeError(CompileError):
    code = CompileErrorCode.TYPE


class TypeMismatchError(CompileTypeError):
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
    code = CompileErrorCode.INVALID_CAST


class InvalidOperationError(CompileTypeError):
    code = CompileErrorCode.INVALID_OPERATION


# ═══════════════════════════════════════════════════════════════════════
# CONTROL FLOW
# ═══════════════════════════════════════════════════════════════════════


class CompileControlFlowError(CompileError):
    code = CompileErrorCode.CONTROL_FLOW


class BreakOutsideLoopError(CompileControlFlowError):
    code = CompileErrorCode.BREAK_OUTSIDE_LOOP


class ContinueOutsideLoopError(CompileControlFlowError):
    code = CompileErrorCode.CONTINUE_OUTSIDE_LOOP


class InvalidReturnError(CompileControlFlowError):
    code = CompileErrorCode.INVALID_RETURN


# ═══════════════════════════════════════════════════════════════════════
# FUNCTION ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileFunctionError(CompileError):
    code = CompileErrorCode.FUNCTION


class InvalidCallError(CompileFunctionError):
    code = CompileErrorCode.INVALID_CALL


class ArgumentCountError(CompileFunctionError):
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
    code = CompileErrorCode.DUPLICATE_PARAMETER


# ═══════════════════════════════════════════════════════════════════════
# CONTRACT ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileContractError(CompileError):
    code = CompileErrorCode.CONTRACT


class InvalidContractError(CompileContractError):
    code = CompileErrorCode.INVALID_CONTRACT


class InvalidStateError(CompileContractError):
    code = CompileErrorCode.INVALID_STATE


# ═══════════════════════════════════════════════════════════════════════
# BYTECODE ERRORS
# ═══════════════════════════════════════════════════════════════════════


class CompileBytecodeError(CompileError):
    code = CompileErrorCode.BYTECODE


class InvalidOpcodeError(CompileBytecodeError):
    code = CompileErrorCode.INVALID_OPCODE


class InvalidOperandError(CompileBytecodeError):
    code = CompileErrorCode.INVALID_OPERAND


class InvalidJumpError(CompileBytecodeError):
    code = CompileErrorCode.INVALID_JUMP


# ═══════════════════════════════════════════════════════════════════════
# CONSTANT POOL ERRORS
# ═══════════════════════════════════════════════════════════════════════


class ConstantPoolError(CompileError):
    code = CompileErrorCode.CONSTANT


class ConstantPoolOverflowError(ConstantPoolError):
    code = CompileErrorCode.CONSTANT_POOL_OVERFLOW


# ═══════════════════════════════════════════════════════════════════════
# OPTIMIZER ERRORS
# ═══════════════════════════════════════════════════════════════════════


class OptimizationError(CompileError):
    code = CompileErrorCode.OPTIMIZATION


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
    Konvertiert sicher einen AST-Node in einen SourceSpan.
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
    Convenience Helper zum Werfen eines CompileError.
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

    # Symbols
    "CompileNameError",
    "UndefinedSymbolError",
    "DuplicateSymbolError",

    # Types
    "CompileTypeError",
    "TypeMismatchError",
    "InvalidCastError",
    "InvalidOperationError",

    # Control Flow
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

    # Optimizer
    "OptimizationError",

    # Internal
    "CompileInternalError",

    # Helpers
    "location_from_node",
    "raise_compile_error",
]


__version__ = "0.3.0"