# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Constants
============================

Zentrale Konstanten und Compiler-Konfiguration für ATCLang.

Verantwortlichkeiten:
    - Compiler-Version
    - Bytecode-Format
    - Magic Bytes
    - Sprach-/ABI-Version
    - Compiler Limits
    - Reserved Names
    - interne Symbolpräfixe
    - Optimierungslevel
    - Source-Map-Konstanten

Diese Datei enthält keine Compilerlogik.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Final


# ══════════════════════════════════════════════════════════════════════════════
# VERSIONING
# ══════════════════════════════════════════════════════════════════════════════

ATCLANG_VERSION: Final[str] = "0.3.0"
ATCLANG_VERSION_MAJOR: Final[int] = 0
ATCLANG_VERSION_MINOR: Final[int] = 3
ATCLANG_VERSION_PATCH: Final[int] = 0

# Compiler/Language compatibility identifier.
LANGUAGE_VERSION: Final[str] = "0.3"

# ATC-92 compiler/VM bytecode family.
BYTECODE_VERSION_MAJOR: Final[int] = 1
BYTECODE_VERSION_MINOR: Final[int] = 0


# ══════════════════════════════════════════════════════════════════════════════
# BYTECODE FORMAT
# ══════════════════════════════════════════════════════════════════════════════

BYTECODE_MAGIC: Final[bytes] = b"ATCB"

# Compatibility aliases for older compiler code.
MAGIC: Final[bytes] = BYTECODE_MAGIC
VERSION: Final[bytes] = bytes(
    (BYTECODE_VERSION_MAJOR, BYTECODE_VERSION_MINOR)
)

BYTECODE_EXTENSION: Final[str] = ".atcb"
SOURCE_EXTENSION: Final[str] = ".atc"


# ══════════════════════════════════════════════════════════════════════════════
# COMPILER IDENTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

COMPILER_NAME: Final[str] = "ATCLang Compiler"
COMPILER_ID: Final[str] = "atclang"
COMPILER_VENDOR: Final[str] = "ShivaCore / A-TownChain-Okosystems"

# Standards reference.
COMPILER_STANDARD: Final[str] = "ATC-92"


# ══════════════════════════════════════════════════════════════════════════════
# OPTIMIZATION
# ══════════════════════════════════════════════════════════════════════════════

class OptimizationLevel(IntEnum):
    """
    Compiler optimization levels.

    O0:
        Keine Optimierung.

    O1:
        Sichere lokale Optimierungen:
            - Constant Folding
            - Dead Code Elimination
            - Jump Threading
            - einfache Peephole-Regeln

    O2:
        Erweiterte Optimierungen:
            - Constant Propagation
            - Algebraic Simplification
            - zusätzliche lokale Optimierungen
    """

    O0 = 0
    O1 = 1
    O2 = 2


DEFAULT_OPTIMIZATION_LEVEL: Final[int] = OptimizationLevel.O1


# ══════════════════════════════════════════════════════════════════════════════
# COMPILER LIMITS
# ══════════════════════════════════════════════════════════════════════════════

# Defensive limits. These prevent malformed programs from creating
# unbounded compiler state.

MAX_CONSTANTS: Final[int] = 1_000_000
MAX_FUNCTIONS: Final[int] = 100_000
MAX_GLOBAL_SYMBOLS: Final[int] = 1_000_000
MAX_LOCAL_SYMBOLS: Final[int] = 65_535

MAX_PARAMETERS: Final[int] = 255
MAX_NESTING_DEPTH: Final[int] = 1_024
MAX_BASIC_BLOCKS: Final[int] = 1_000_000
MAX_INSTRUCTIONS: Final[int] = 10_000_000

MAX_IDENTIFIER_LENGTH: Final[int] = 256
MAX_STRING_LITERAL_LENGTH: Final[int] = 16 * 1024 * 1024

MAX_MODULE_NAME_LENGTH: Final[int] = 256
MAX_EXPORTS: Final[int] = 65_535


# ══════════════════════════════════════════════════════════════════════════════
# SYMBOL KINDS
# ══════════════════════════════════════════════════════════════════════════════

SYMBOL_LOCAL: Final[str] = "local"
SYMBOL_GLOBAL: Final[str] = "global"
SYMBOL_FUNCTION: Final[str] = "function"
SYMBOL_CONTRACT: Final[str] = "contract"
SYMBOL_STATE: Final[str] = "state"
SYMBOL_PARAMETER: Final[str] = "parameter"
SYMBOL_TYPE: Final[str] = "type"
SYMBOL_ENUM: Final[str] = "enum"
SYMBOL_CONSTANT: Final[str] = "constant"
SYMBOL_IMPORT: Final[str] = "import"


SYMBOL_KINDS: Final[frozenset[str]] = frozenset(
    {
        SYMBOL_LOCAL,
        SYMBOL_GLOBAL,
        SYMBOL_FUNCTION,
        SYMBOL_CONTRACT,
        SYMBOL_STATE,
        SYMBOL_PARAMETER,
        SYMBOL_TYPE,
        SYMBOL_ENUM,
        SYMBOL_CONSTANT,
        SYMBOL_IMPORT,
    }
)


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL SYMBOL PREFIXES
# ══════════════════════════════════════════════════════════════════════════════

INTERNAL_PREFIX: Final[str] = "__atc_"

ITERATOR_PREFIX: Final[str] = "__atc_iter_"
LOOP_INDEX_PREFIX: Final[str] = "__atc_i_"
TEMP_PREFIX: Final[str] = "__atc_tmp_"
RETURN_PREFIX: Final[str] = "__atc_return_"
PARAM_PREFIX: Final[str] = "__atc_param_"


# ══════════════════════════════════════════════════════════════════════════════
# NAMESPACE
# ══════════════════════════════════════════════════════════════════════════════

NAMESPACE_SEPARATOR: Final[str] = "::"

ATC_NAMESPACE: Final[str] = "ATC"

STANDARD_NAMESPACE: Final[str] = "ATC::Std"

IMPORT_NAMESPACE: Final[str] = "ATC::Import"

SYSTEM_NAMESPACE: Final[str] = "ATC::System"

VM_NAMESPACE: Final[str] = "ATC::VM"


# ══════════════════════════════════════════════════════════════════════════════
# BUILTIN FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

BUILTIN_PRINT: Final[str] = "print"
BUILTIN_LEN: Final[str] = "len"

BUILTIN_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {
        BUILTIN_PRINT,
        BUILTIN_LEN,
    }
)


# ══════════════════════════════════════════════════════════════════════════════
# SPECIAL COMPILER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

DYNAMIC_CALL_NAME: Final[str] = "__dynamic__"

STD_LEN_FUNCTION: Final[str] = "ATC::Std::len"

IMPORT_FUNCTION_PREFIX: Final[str] = "ATC::Import::"


# ══════════════════════════════════════════════════════════════════════════════
# RESERVED IDENTIFIERS
# ══════════════════════════════════════════════════════════════════════════════

RESERVED_IDENTIFIERS: Final[frozenset[str]] = frozenset(
    {
        # Language/runtime
        "self",
        "super",
        "this",

        # Compiler/runtime internals
        "__dynamic__",
        "__atc_return__",
        "__atc_tmp__",

        # Builtins
        "print",
        "len",

        # ATC namespaces
        "ATC",
        "Std",
        "System",
        "VM",
    }
)


# ══════════════════════════════════════════════════════════════════════════════
# CONTROL FLOW
# ══════════════════════════════════════════════════════════════════════════════

# Maximum number of nested loops/branches tracked by compiler context.
MAX_CONTROL_FLOW_DEPTH: Final[int] = 1_024

# Sentinel used by control-flow analysis.
NO_TARGET: Final[int] = -1


# ══════════════════════════════════════════════════════════════════════════════
# SOURCE MAP
# ══════════════════════════════════════════════════════════════════════════════

# Source map entry:
#
#     instruction_index, source_line, source_column
#
SOURCE_MAP_ENTRY_SIZE: Final[int] = 3

UNKNOWN_SOURCE_LINE: Final[int] = 0
UNKNOWN_SOURCE_COLUMN: Final[int] = 0

SOURCE_MAP_VERSION: Final[int] = 1


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANT POOL
# ══════════════════════════════════════════════════════════════════════════════

class ConstantKind(IntEnum):
    """Canonical constant-pool categories."""

    NULL = 0
    BOOL = 1
    INT = 2
    FLOAT = 3
    STRING = 4
    BYTES = 5


# ══════════════════════════════════════════════════════════════════════════════
# TYPE SYSTEM
# ══════════════════════════════════════════════════════════════════════════════

TYPE_ANY: Final[str] = "Any"
TYPE_NULL: Final[str] = "Null"
TYPE_BOOL: Final[str] = "Bool"
TYPE_INT: Final[str] = "Int"
TYPE_FLOAT: Final[str] = "Float"
TYPE_STRING: Final[str] = "String"
TYPE_BYTES: Final[str] = "Bytes"

TYPE_LIST: Final[str] = "List"
TYPE_MAP: Final[str] = "Map"
TYPE_TUPLE: Final[str] = "Tuple"

TYPE_ADDRESS: Final[str] = "Address"
TYPE_ATC_WALLET: Final[str] = "ATCWallet"

PRIMITIVE_TYPES: Final[frozenset[str]] = frozenset(
    {
        TYPE_NULL,
        TYPE_BOOL,
        TYPE_INT,
        TYPE_FLOAT,
        TYPE_STRING,
        TYPE_BYTES,
    }
)


# ══════════════════════════════════════════════════════════════════════════════
# OPERATOR SET
# ══════════════════════════════════════════════════════════════════════════════

ARITHMETIC_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "+",
        "-",
        "*",
        "/",
        "%",
        "**",
    }
)

COMPARISON_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "==",
        "!=",
        "<",
        ">",
        "<=",
        ">=",
    }
)

LOGICAL_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "&&",
        "||",
        "and",
        "or",
    }
)

BITWISE_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "&",
        "|",
        "^",
        "<<",
        ">>",
    }
)

UNARY_OPERATORS: Final[frozenset[str]] = frozenset(
    {
        "-",
        "!",
        "~",
    }
)

ALL_BINARY_OPERATORS: Final[frozenset[str]] = (
    ARITHMETIC_OPERATORS
    | COMPARISON_OPERATORS
    | LOGICAL_OPERATORS
    | BITWISE_OPERATORS
)


# ══════════════════════════════════════════════════════════════════════════════
# FUNCTION CALL CONVENTION
# ══════════════════════════════════════════════════════════════════════════════

MAX_CALL_ARGUMENTS: Final[int] = 255

# Arguments are evaluated left-to-right.
ARGUMENT_EVALUATION_ORDER: Final[str] = "left-to-right"

# Current compiler ABI convention.
CALL_ABI_VERSION: Final[int] = 1


# ══════════════════════════════════════════════════════════════════════════════
# CONTRACT / SMART-CONTRACT CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

STATE_NAMESPACE_SEPARATOR: Final[str] = "."

CONTRACT_FUNCTION_SEPARATOR: Final[str] = "."

MAX_CONTRACT_STATES: Final[int] = 65_535
MAX_CONTRACT_FUNCTIONS: Final[int] = 65_535
MAX_CONTRACT_EVENTS: Final[int] = 65_535


# ══════════════════════════════════════════════════════════════════════════════
# EXPORTS
# ══════════════════════════════════════════════════════════════════════════════

# Public API names that can be emitted by compiler modules.
EXPORT_NAME_SEPARATOR: Final[str] = "::"


# ══════════════════════════════════════════════════════════════════════════════
# ERROR CODES
# ══════════════════════════════════════════════════════════════════════════════

ERROR_PREFIX: Final[str] = "ATC"

ERR_INVALID_AST: Final[str] = "ATC-C001"
ERR_UNKNOWN_NODE: Final[str] = "ATC-C002"
ERR_UNKNOWN_OPERATOR: Final[str] = "ATC-C003"
ERR_UNDEFINED_SYMBOL: Final[str] = "ATC-C004"
ERR_DUPLICATE_SYMBOL: Final[str] = "ATC-C005"
ERR_INVALID_CONTROL_FLOW: Final[str] = "ATC-C006"
ERR_INVALID_FUNCTION: Final[str] = "ATC-C007"
ERR_INVALID_CONTRACT: Final[str] = "ATC-C008"
ERR_BYTECODE_LIMIT: Final[str] = "ATC-C009"
ERR_CONSTANT_LIMIT: Final[str] = "ATC-C010"
ERR_INVALID_TARGET: Final[str] = "ATC-C011"


# ══════════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def is_reserved_identifier(name: str) -> bool:
    """Return True if ``name`` is reserved by the language/compiler."""
    return name in RESERVED_IDENTIFIERS or name.startswith(INTERNAL_PREFIX)


def is_valid_identifier_length(name: str) -> bool:
    """Validate identifier length against compiler limits."""
    return 0 < len(name) <= MAX_IDENTIFIER_LENGTH


def is_valid_module_name(name: str) -> bool:
    """Validate module name length."""
    return 0 < len(name) <= MAX_MODULE_NAME_LENGTH


def validate_optimization_level(level: int) -> int:
    """
    Validate and normalize an optimization level.

    Raises:
        ValueError: if the level is outside O0..O2.
    """
    try:
        value = int(level)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Invalid optimization level: {level!r}"
        ) from exc

    if value not in (
        OptimizationLevel.O0,
        OptimizationLevel.O1,
        OptimizationLevel.O2,
    ):
        raise ValueError(
            f"Invalid optimization level {value}; "
            f"expected 0, 1 or 2."
        )

    return value


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Version
    "ATCLANG_VERSION",
    "ATCLANG_VERSION_MAJOR",
    "ATCLANG_VERSION_MINOR",
    "ATCLANG_VERSION_PATCH",
    "LANGUAGE_VERSION",

    # Bytecode
    "BYTECODE_MAGIC",
    "BYTECODE_VERSION_MAJOR",
    "BYTECODE_VERSION_MINOR",
    "BYTECODE_EXTENSION",
    "SOURCE_EXTENSION",
    "MAGIC",
    "VERSION",

    # Compiler
    "COMPILER_NAME",
    "COMPILER_ID",
    "COMPILER_VENDOR",
    "COMPILER_STANDARD",

    # Optimization
    "OptimizationLevel",
    "DEFAULT_OPTIMIZATION_LEVEL",

    # Limits
    "MAX_CONSTANTS",
    "MAX_FUNCTIONS",
    "MAX_GLOBAL_SYMBOLS",
    "MAX_LOCAL_SYMBOLS",
    "MAX_PARAMETERS",
    "MAX_NESTING_DEPTH",
    "MAX_BASIC_BLOCKS",
    "MAX_INSTRUCTIONS",
    "MAX_IDENTIFIER_LENGTH",
    "MAX_STRING_LITERAL_LENGTH",
    "MAX_MODULE_NAME_LENGTH",
    "MAX_EXPORTS",

    # Symbols
    "SYMBOL_LOCAL",
    "SYMBOL_GLOBAL",
    "SYMBOL_FUNCTION",
    "SYMBOL_CONTRACT",
    "SYMBOL_STATE",
    "SYMBOL_PARAMETER",
    "SYMBOL_TYPE",
    "SYMBOL_ENUM",
    "SYMBOL_CONSTANT",
    "SYMBOL_IMPORT",
    "SYMBOL_KINDS",

    # Internal symbols
    "INTERNAL_PREFIX",
    "ITERATOR_PREFIX",
    "LOOP_INDEX_PREFIX",
    "TEMP_PREFIX",
    "RETURN_PREFIX",
    "PARAM_PREFIX",

    # Namespaces
    "NAMESPACE_SEPARATOR",
    "ATC_NAMESPACE",
    "STANDARD_NAMESPACE",
    "IMPORT_NAMESPACE",
    "SYSTEM_NAMESPACE",
    "VM_NAMESPACE",

    # Builtins
    "BUILTIN_PRINT",
    "BUILTIN_LEN",
    "BUILTIN_FUNCTIONS",
    "DYNAMIC_CALL_NAME",
    "STD_LEN_FUNCTION",
    "IMPORT_FUNCTION_PREFIX",

    # Reserved
    "RESERVED_IDENTIFIERS",

    # Control flow
    "MAX_CONTROL_FLOW_DEPTH",
    "NO_TARGET",

    # Source maps
    "SOURCE_MAP_ENTRY_SIZE",
    "UNKNOWN_SOURCE_LINE",
    "UNKNOWN_SOURCE_COLUMN",
    "SOURCE_MAP_VERSION",

    # Constants
    "ConstantKind",

    # Types
    "TYPE_ANY",
    "TYPE_NULL",
    "TYPE_BOOL",
    "TYPE_INT",
    "TYPE_FLOAT",
    "TYPE_STRING",
    "TYPE_BYTES",
    "TYPE_LIST",
    "TYPE_MAP",
    "TYPE_TUPLE",
    "TYPE_ADDRESS",
    "TYPE_ATC_WALLET",
    "PRIMITIVE_TYPES",

    # Operators
    "ARITHMETIC_OPERATORS",
    "COMPARISON_OPERATORS",
    "LOGICAL_OPERATORS",
    "BITWISE_OPERATORS",
    "UNARY_OPERATORS",
    "ALL_BINARY_OPERATORS",

    # Calls / ABI
    "MAX_CALL_ARGUMENTS",
    "ARGUMENT_EVALUATION_ORDER",
    "CALL_ABI_VERSION",

    # Contracts
    "STATE_NAMESPACE_SEPARATOR",
    "CONTRACT_FUNCTION_SEPARATOR",
    "MAX_CONTRACT_STATES",
    "MAX_CONTRACT_FUNCTIONS",
    "MAX_CONTRACT_EVENTS",

    # Exports
    "EXPORT_NAME_SEPARATOR",

    # Errors
    "ERROR_PREFIX",
    "ERR_INVALID_AST",
    "ERR_UNKNOWN_NODE",
    "ERR_UNKNOWN_OPERATOR",
    "ERR_UNDEFINED_SYMBOL",
    "ERR_DUPLICATE_SYMBOL",
    "ERR_INVALID_CONTROL_FLOW",
    "ERR_INVALID_FUNCTION",
    "ERR_INVALID_CONTRACT",
    "ERR_BYTECODE_LIMIT",
    "ERR_CONSTANT_LIMIT",
    "ERR_INVALID_TARGET",

    # Helpers
    "is_reserved_identifier",
    "is_valid_identifier_length",
    "is_valid_module_name",
    "validate_optimization_level",
]