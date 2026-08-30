# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler Package
========================

Public compiler API for ATCLang.

This package provides:

    - AST → ATC bytecode compilation
    - Static type checking
    - Compiler optimization
    - Symbol and module management

The package intentionally exposes only compiler-level APIs.
Lexer, parser, VM and runtime components remain in their
respective ATCLang packages.
"""

from .compiler import (
    ATCCompiler,
    CompiledModule,
    Symbol,
    SymbolTable,
)

from .type_checker import (
    ATCTypeChecker,
    ATCType,
    ATCGenericType,
    TypeEnvironment,
    TypeError,
)

from .optimizer import Optimizer


__all__ = [
    # Compiler
    "ATCCompiler",
    "CompiledModule",

    # Symbol management
    "Symbol",
    "SymbolTable",

    # Type system
    "ATCTypeChecker",
    "ATCType",
    "ATCGenericType",
    "TypeEnvironment",
    "TypeError",

    # Optimization
    "Optimizer",
]


__version__ = "0.3.0"