# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler Package
========================

Public compiler API for ATCLang.

Pipeline:

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
    ATC Bytecode
      ↓
    ATC VM

This package exposes compiler-level APIs only.
Lexer, parser, VM and runtime components remain
in their respective ATCLang packages.
"""

from .compiler import (
    ATCCompiler,
    CompiledModule,
    compile_source,
    disassemble,
)

from .symbols import (
    Symbol,
    SymbolTable,
)

from .type_checker import (
    ATCTypeChecker,
    ATCType,
    ATCGenericType,
    TypeEnvironment,
    TypeError as ATCTypeError,
)

from .optimizer import (
    ATCOptimizer,
    OptimizerConfig,
    OptimizationStats,
)

from .errors import (
    CompileError,
)

__all__ = [
    # Compiler
    "ATCCompiler",
    "CompiledModule",
    "compile_source",
    "disassemble",

    # Symbols
    "Symbol",
    "SymbolTable",

    # Type system
    "ATCTypeChecker",
    "ATCType",
    "ATCGenericType",
    "TypeEnvironment",
    "ATCTypeError",

    # Optimizer
    "ATCOptimizer",
    "OptimizerConfig",
    "OptimizationStats",

    # Errors
    "CompileError",
]

__version__ = "0.3.0"