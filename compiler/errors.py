# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Error System
================================

Zentrales Fehler-System des ATCLang-Compilers.

Compiler-Pipeline:

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
    ATC Bytecode
      ↓
    ATC VM

Dieses Modul definiert ausschließlich Compiler-Fehler.
Lexer-, Parser- und VM-Fehler bleiben in ihren jeweiligen
Subsystemen.

Designziele:

    - stabile Fehler-Hierarchie
    - strukturierte Source-Location
    - maschinenlesbare Fehlercodes
    - menschenlesbare Fehlermeldungen
    - kompatibel mit CompilerContext
    - keine Abhängigkeit von anderen Compiler-Modulen
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ═════════════════════════════════════════════════════════════
# ERROR PHASE
# ═════════════════════════════════════════════════════════════


class ErrorPhase(str, Enum):
    """Compilerphase, in der ein Fehler entstanden ist."""

    LEXER = "lexer"
    PARSER = "parser"
    TYPE_CHECKER = "type_checker"
    COMPILER = "compiler"
    OPTIMIZER = "optimizer"
    BYTECODE = "bytecode"
    INTERNAL = "internal"


# ═════════════════════════════════════════════════════════════
# SOURCE LOCATION
# ═════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class SourceLocation:
    """
    Position eines Fehlers im ATCLang-Quellcode.

    line/column sind 1-basiert.
    """

    line: int = 0
    column: int = 0

    # Optionales Ende eines Bereichs.
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    def __str__(self) -> str:
        if self.line <= 0:
            return "<unknown>"

        if self.column > 0:
            return f"{self.line}:{self.column}"

        return str(self.line)


# ═════════════════════════════════════════════════════════════
# ERROR CODE
# ═════════════════════════════════════════════════════════════


class CompileErrorCode(str, Enum):
    """Stabile maschinenlesbare Compiler-Fehlercodes."""

    # General
    INTERNAL_ERROR = "ATC-C000"
    INVALID_AST = "ATC-C001"
    UNSUPPORTED_NODE = "ATC-C002"

    # Symbol system
    DUPLICATE_SYMBOL = "ATC-C100"
    UNDEFINED_SYMBOL = "ATC-C101"
    INVALID_SYMBOL = "ATC-C102"

    # Expressions
    INVALID_EXPRESSION = "ATC-C200"
    INVALID_OPERATOR = "ATC-C201"
    INVALID_CALL = "ATC-C202"
    INVALID_ASSIGNMENT = "ATC-C203"

    # Statements
    INVALID_STATEMENT = "ATC-C300"
    INVALID_RETURN = "ATC-C301"
    BREAK_OUTSIDE_LOOP = "ATC-C302"
    CONTINUE_OUTSIDE_LOOP = "ATC-C303"

    # Functions
    DUPLICATE_FUNCTION = "ATC-C400"
    UNKNOWN_FUNCTION = "ATC-C401"
    INVALID_FUNCTION = "ATC-C402"

    # Contracts
    DUPLICATE_CONTRACT = "ATC-C500"
    INVALID_CONTRACT = "ATC-C501"
    INVALID_STATE = "ATC-C502"

    # Bytecode
    INVALID_OPCODE = "ATC-C600"
    INVALID_OPERAND = "ATC-C601"
    INVALID_JUMP = "ATC-C602"
    INVALID_MODULE = "ATC-C603"

    # Optimization
    OPTIMIZATION_ERROR = "ATC-C700"


# ═════════════════════════════════════════════════════════════
# COMPILER ERROR
# ═════════════════════════════════════════════════════════════


class CompileError(Exception):
    """
    Basisklasse für alle ATCLang-Compilerfehler.

    Beispiel:

        raise CompileError(
            "undefined symbol 'wallet'",
            code=CompileErrorCode.UNDEFINED_SYMBOL,
            location=SourceLocation(12, 5),
        )
    """

    def __init__(
        self,
        message: str,
        *,
        code: CompileErrorCode = CompileErrorCode.INTERNAL_ERROR,
        location: Optional[SourceLocation] = None,
        phase: ErrorPhase = ErrorPhase.COMPILER,
        source_name: Optional[str] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.location = location or SourceLocation()
        self.phase = phase
        self.source_name = source_name
        self.cause = cause

        super().__init__(self.format_message())

    def format_message(self) -> str:
        """Erzeugt die standardisierte Fehlermeldung."""

        prefix = f"[{self.code.value}]"

        if self.source_name:
            prefix += f" {self.source_name}"

        if self.location.line > 0:
            prefix += f":{self.location}"

        prefix += f" [{self.phase.value}]"

        return f"{prefix}: {self.message}"

    def __str__(self) -> str:
        return self.format_message()


# ═════════════════════════════════════════════════════════════
# SPECIALIZED ERRORS
# ═════════════════════════════════════════════════════════════


class InternalCompilerError(CompileError):
    """Interner Compilerfehler."""

    def __init__(
        self,
        message: str,
        *,
        location: Optional[SourceLocation] = None,
        cause: Optional[BaseException] = None,
    ) -> None:
        super().__init__(
            message,
            code=CompileErrorCode.INTERNAL_ERROR,
            location=location,
            phase=ErrorPhase.INTERNAL,
            cause=cause,
        )


class InvalidASTError(CompileError):
    """Ungültiger oder inkonsistenter AST."""

    def __init__(
        self,
        message: str,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            message,
            code=CompileErrorCode.INVALID_AST,
            location=location,
            phase=ErrorPhase.COMPILER,
        )


class UnsupportedNodeError(CompileError):
    """AST-Node wird vom Compiler nicht unterstützt."""

    def __init__(
        self,
        node_type: str,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            f"unsupported AST node: {node_type}",
            code=CompileErrorCode.UNSUPPORTED_NODE,
            location=location,
            phase=ErrorPhase.COMPILER,
        )


class DuplicateSymbolError(CompileError):
    """Symbol wurde mehrfach definiert."""

    def __init__(
        self,
        name: str,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            f"duplicate symbol: '{name}'",
            code=CompileErrorCode.DUPLICATE_SYMBOL,
            location=location,
            phase=ErrorPhase.COMPILER,
        )


class UndefinedSymbolError(CompileError):
    """Symbol konnte nicht aufgelöst werden."""

    def __init__(
        self,
        name: str,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            f"undefined symbol: '{name}'",
            code=CompileErrorCode.UNDEFINED_SYMBOL,
            location=location,
            phase=ErrorPhase.COMPILER,
        )


class InvalidExpressionError(CompileError):
    """Ungültiger Ausdruck."""

    def __init__(
        self,
        message: str,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            message,
            code=CompileErrorCode.INVALID_EXPRESSION,
            location=location,
            phase=ErrorPhase.COMPILER,
        )


class InvalidAssignmentError(CompileError):
    """Ungültiges Assignment."""

    def __init__(
        self,
        message: str,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            message,
            code=CompileErrorCode.INVALID_ASSIGNMENT,
            location=location,
            phase=ErrorPhase.COMPILER,
        )


class BreakOutsideLoopError(CompileError):
    """break außerhalb einer Schleife."""

    def __init__(
        self,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            "break outside loop",
            code=CompileErrorCode.BREAK_OUTSIDE_LOOP,
            location=location,
            phase=ErrorPhase.COMPILER,
        )


class ContinueOutsideLoopError(CompileError):
    """continue außerhalb einer Schleife."""

    def __init__(
        self,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            "continue outside loop",
            code=CompileErrorCode.CONTINUE_OUTSIDE_LOOP,
            location=location,
            phase=ErrorPhase.COMPILER,
        )


class InvalidBytecodeError(CompileError):
    """Ungültiges generiertes ATC-Bytecode."""

    def __init__(
        self,
        message: str,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            message,
            code=CompileErrorCode.INVALID_MODULE,
            location=location,
            phase=ErrorPhase.BYTECODE,
        )


class OptimizationError(CompileError):
    """Fehler während der Compileroptimierung."""

    def __init__(
        self,
        message: str,
        *,
        location: Optional[SourceLocation] = None,
    ) -> None:
        super().__init__(
            message,
            code=CompileErrorCode.OPTIMIZATION_ERROR,
            location=location,
            phase=ErrorPhase.OPTIMIZER,
        )


# ═════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════


def location_from_node(node: object) -> SourceLocation:
    """
    Erstellt eine SourceLocation aus einem AST-Node.

    Unterstützt Nodes mit:
        line
        col
        end_line
        end_col
    """

    if node is None:
        return SourceLocation()

    line = getattr(node, "line", 0) or 0
    column = getattr(node, "col", 0) or 0

    end_line = getattr(node, "end_line", None)
    end_column = getattr(node, "end_col", None)

    return SourceLocation(
        line=line,
        column=column,
        end_line=end_line,
        end_column=end_column,
    )


def compiler_error(
    message: str,
    node: object = None,
    *,
    code: CompileErrorCode = CompileErrorCode.INTERNAL_ERROR,
    phase: ErrorPhase = ErrorPhase.COMPILER,
) -> CompileError:
    """
    Convenience Factory für Compilerfehler.

    Beispiel:

        raise compiler_error(
            "unknown operator '+'",
            node,
            code=CompileErrorCode.INVALID_OPERATOR,
        )
    """

    return CompileError(
        message,
        code=code,
        location=location_from_node(node),
        phase=phase,
    )


__all__ = [
    # Enums
    "ErrorPhase",
    "CompileErrorCode",

    # Location
    "SourceLocation",
    "location_from_node",

    # Base errors
    "CompileError",
    "InternalCompilerError",
    "InvalidASTError",
    "UnsupportedNodeError",

    # Symbol errors
    "DuplicateSymbolError",
    "UndefinedSymbolError",

    # Expression errors
    "InvalidExpressionError",
    "InvalidAssignmentError",

    # Control flow errors
    "BreakOutsideLoopError",
    "ContinueOutsideLoopError",

    # Bytecode / optimizer
    "InvalidBytecodeError",
    "OptimizationError",

    # Helpers
    "compiler_error",
]