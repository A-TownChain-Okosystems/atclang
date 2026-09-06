# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Type Checker — Statische Typ-Prüfung zur Compile-Zeit.
ATC-92 | Sprint 2.1
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from atclang.parser.ast_nodes import (
    ASTNode, Program, IntLiteral, FloatLiteral, StringLiteral, BoolLiteral,
    NullLiteral, Identifier, BinaryOp, UnaryOp, Assignment, IndexAccess,
    DotAccess, NamespaceAccess, FunctionCall, TypeAnnotation,
    LetStatement, ReturnStatement, EmitStatement, RequireStatement,
    IfStatement, ForStatement, WhileStatement, BreakStatement,
    ContinueStatement, ExprStatement,
    Parameter, FunctionDef, StateField, EventDef, ErrorDef,
    ContractDef, WalletDef, ImportStatement, StructDef, EnumDef,
)


# ── ATCLang Type System ───────────────────────────────────

class ATCType:
    """Base type class."""
    def __init__(self, name: str, nullable: bool = False):
        self.name = name
        self.nullable = nullable
    def __eq__(self, other):
        if not isinstance(other, ATCType): return False
        return self.name == other.name
    def __repr__(self): return f"ATCType({self.name})"
    def __hash__(self): return hash(self.name)

# Primitive types
T_INT     = ATCType("Int")
T_FLOAT   = ATCType("Float")
T_STRING  = ATCType("String")
T_BOOL    = ATCType("Bool")
T_NULL    = ATCType("Null")
T_BYTES   = ATCType("Bytes")
T_VOID    = ATCType("Void")
T_UNKNOWN = ATCType("Unknown")
T_ANY     = ATCType("Any")

# ATC blockchain types
T_ADDRESS  = ATCType("Address")
T_HASH     = ATCType("Hash")
T_UINT256  = ATCType("UInt256")
T_SIGNATURE = ATCType("Signature")

# Collection types (parameterized)
class ATCGenericType(ATCType):
    def __init__(self, name: str, elem_type: ATCType = T_ANY):
        super().__init__(name)
        self.elem_type = elem_type
    def __repr__(self): return f"ATCGenericType({self.name}<{self.elem_type}>)"

T_MAP  = ATCGenericType("Map")
T_LIST = ATCGenericType("List")
T_SET  = ATCGenericType("Set")

# Type registry for ATCLang types
ATC_TYPE_REGISTRY = {
    "Int": T_INT, "UInt": T_INT, "UInt8": T_INT, "UInt16": T_INT,
    "UInt32": T_INT, "UInt64": T_INT, "UInt128": T_INT, "UInt256": T_UINT256,
    "Int8": T_INT, "Int16": T_INT, "Int32": T_INT, "Int64": T_INT,
    "Int128": T_INT, "Int256": T_INT,
    "Float": T_FLOAT, "Float32": T_FLOAT, "Float64": T_FLOAT, "Float128": T_FLOAT,
    "String": T_STRING, "Str": T_STRING,
    "Bool": T_BOOL,
    "Bytes": T_BYTES,
    "Address": T_ADDRESS, "Hash": T_HASH, "Hash256": T_HASH, "Hash512": T_HASH,
    "Signature": T_SIGNATURE, "PubKey": T_ANY, "PrivKey": T_ANY,
    "Void": T_VOID, "None": T_NULL, "Null": T_NULL,
    "Map": T_MAP, "List": T_LIST, "Set": T_SET, "Array": T_LIST, "Vec": T_LIST,
    "TxHash": T_HASH, "BlockHash": T_HASH, "CID": T_STRING,
}


@dataclass
class TypeError:
    message: str
    line: int = 0
    col: int = 0
    def __repr__(self): return f"TypeError at {self.line}:{self.col}: {self.message}"


class TypeEnvironment:
    """Scope for type tracking."""
    def __init__(self, parent: Optional['TypeEnvironment'] = None):
        self.vars: Dict[str, ATCType] = {}
        self.functions: Dict[str, Tuple[List[ATCType], ATCType]] = {}
        self.parent = parent

    def define_var(self, name: str, t: ATCType):
        self.vars[name] = t

    def lookup_var(self, name: str) -> Optional[ATCType]:
        if name in self.vars: return self.vars[name]
        if self.parent: return self.parent.lookup_var(name)
        return None

    def define_function(self, name: str, params: List[ATCType], ret: ATCType):
        self.functions[name] = (params, ret)

    def lookup_function(self, name: str) -> Optional[Tuple[List[ATCType], ATCType]]:
        if name in self.functions: return self.functions[name]
        if self.parent: return self.parent.lookup_function(name)
        return None

    def child(self) -> 'TypeEnvironment':
        return TypeEnvironment(parent=self)


class ATCTypeChecker:
    """Statische Typ-Prüfung für ATCLang ASTs."""

    def __init__(self):
        self.errors: List[TypeError] = []
        self.warnings: List[TypeError] = []
        self.global_env = TypeEnvironment()
        self._init_builtins()

    def _init_builtins(self):
        """Register built-in functions."""
        builtins = {
            "print":   ([T_ANY], T_VOID),
            "len":     ([T_ANY], T_INT),
            "range":   ([T_INT], T_LIST),
            "sha256":  ([T_ANY], T_STRING),
            "int":     ([T_ANY], T_INT),
            "float":   ([T_ANY], T_FLOAT),
            "str":     ([T_ANY], T_STRING),
            "bool":    ([T_ANY], T_BOOL),
            "abs":     ([T_INT], T_INT),
            "min":     ([T_INT, T_INT], T_INT),
            "max":     ([T_INT, T_INT], T_INT),
            "push":    ([T_LIST, T_ANY], T_VOID),
            "pop":     ([T_LIST], T_ANY),
        }
        for name, sig in builtins.items():
            self.global_env.define_function(name, sig[0], sig[1])

    # ── Public API ───────────────────────────────

    def check(self, program: Program) -> List[TypeError]:
        """Type-check a full program. Returns list of errors."""
        self.errors = []
        self.warnings = []
        self._check_program(program, self.global_env)
        return self.errors

    def check_and_report(self, program: Program) -> bool:
        """Type-check and print errors. Returns True if no errors."""
        errors = self.check(program)
        for e in errors:
            print(f"❌ {e}")
        for w in self.warnings:
            print(f"⚠️ {w}")
        return len(errors) == 0

    # ── Program Level ────────────────────────────

    def _check_program(self, prog: Program, env: TypeEnvironment):
        # First pass: collect function signatures
        for stmt in prog.statements:
            if isinstance(stmt, FunctionDef):
                param_types = [self._resolve_type(p.type_hint) for p in stmt.params]
                ret_type = self._resolve_type(stmt.return_type) if stmt.return_type else T_VOID
                env.define_function(stmt.name, param_types, ret_type)

        # Second pass: check bodies
        for stmt in prog.statements:
            self._check_stmt(stmt, env)

    # ── Statements ───────────────────────────────

    def _check_stmt(self, node: ASTNode, env: TypeEnvironment):
        if isinstance(node, LetStatement):
            self._check_let(node, env)
        elif isinstance(node, ReturnStatement):
            self._check_return(node, env)
        elif isinstance(node, IfStatement):
            self._check_if(node, env)
        elif isinstance(node, ForStatement):
            self._check_for(node, env)
        elif isinstance(node, WhileStatement):
            cond_type = self._infer(node.condition, env)
            if not self._is_compatible(cond_type, T_BOOL):
                self._error(f"while condition must be Bool, got {cond_type}", node)
            for s in node.body:
                self._check_stmt(s, env)
        elif isinstance(node, EmitStatement):
            for arg in node.args:
                self._infer(arg, env)  # just infer, no strict check
        elif isinstance(node, RequireStatement):
            cond_type = self._infer(node.condition, env)
            if not self._is_compatible(cond_type, T_BOOL):
                self._error(f"require condition must be Bool, got {cond_type}", node)
            if node.message:
                self._infer(node.message, env)
        elif isinstance(node, BreakStatement):
            pass
        elif isinstance(node, ContinueStatement):
            pass
        elif isinstance(node, ExprStatement):
            self._infer(node.expr, env)
        elif isinstance(node, FunctionDef):
            self._check_function(node, env)
        elif isinstance(node, ContractDef):
            self._check_contract(node, env)
        elif isinstance(node, ImportStatement):
            pass
        elif isinstance(node, StructDef):
            for f in node.fields:
                if hasattr(f, 'value') and f.value:
                    val_type = self._infer(f.value, env)
                    field_type = self._resolve_type(f.type_hint) if f.type_hint else val_type
                    if not self._is_compatible(val_type, field_type):
                        self._error(f"struct field '{f.name}' type mismatch: expected {field_type}, got {val_type}", f)
        elif isinstance(node, EnumDef):
            pass
        elif isinstance(node, WalletDef):
            self._infer(node.value, env)
        elif isinstance(node, StateField):
            if node.value:
                val_type = self._infer(node.value, env)
        else:
            # Unknown statement — try to infer as expression
            self._infer(node, env)

    def _check_let(self, node: LetStatement, env: TypeEnvironment):
        val_type = self._infer(node.value, env)
        if node.type_hint:
            declared = self._resolve_type(node.type_hint)
            if not self._is_compatible(val_type, declared):
                self._error(
                    f"let '{node.name}': expected {declared}, got {val_type}",
                    node
                )
            env.define_var(node.name, declared)
        else:
            # Infer type from value
            env.define_var(node.name, val_type)

    def _check_return(self, node: ReturnStatement, env: TypeEnvironment):
        if node.value:
            self._infer(node.value, env)
        # Note: we'd check against function return type if we tracked it

    def _check_if(self, node: IfStatement, env: TypeEnvironment):
        cond_type = self._infer(node.condition, env)
        if not self._is_compatible(cond_type, T_BOOL):
            self._error(f"if condition must be Bool, got {cond_type}", node)
        for s in node.then_block:
            self._check_stmt(s, env)
        for elif_cond, elif_block in (node.elif_blocks or []):
            elif_type = self._infer(elif_cond, env)
            if not self._is_compatible(elif_type, T_BOOL):
                self._error(f"elif condition must be Bool, got {elif_type}", node)
            for s in elif_block:
                self._check_stmt(s, env)
        if node.else_block:
            for s in (node.else_block if isinstance(node.else_block, list) else [node.else_block]):
                self._check_stmt(s, env)

    def _check_for(self, node: ForStatement, env: TypeEnvironment):
        iter_type = self._infer(node.iterable, env)
        child_env = env.child()
        # For loop variable gets element type of iterable
        if isinstance(iter_type, ATCGenericType):
            child_env.define_var(node.var, iter_type.elem_type)
        else:
            child_env.define_var(node.var, T_ANY)
        for s in node.body:
            self._check_stmt(s, child_env)

    def _check_function(self, node: FunctionDef, env: TypeEnvironment):
        func_env = env.child()
        for p in node.params:
            ptype = self._resolve_type(p.type_hint) if p.type_hint else T_ANY
            func_env.define_var(p.name, ptype)
        for s in node.body:
            self._check_stmt(s, func_env)

    def _check_contract(self, node: ContractDef, env: TypeEnvironment):
        contract_env = env.child()
        for state in node.states:
            if isinstance(state, StateField):
                stype = self._resolve_type(state.type_hint) if state.type_hint else T_ANY
                contract_env.define_var(state.name, stype)
        for func in node.functions:
            self._check_function(func, contract_env)

    # ── Expression Inference ─────────────────────

    def _infer(self, node: ASTNode, env: TypeEnvironment) -> ATCType:
        if node is None:
            return T_NULL

        if isinstance(node, IntLiteral):
            return T_INT if node.value >= 0 else T_INT

        if isinstance(node, FloatLiteral):
            return T_FLOAT

        if isinstance(node, StringLiteral):
            return T_STRING

        if isinstance(node, BoolLiteral):
            return T_BOOL

        if isinstance(node, NullLiteral):
            return T_NULL

        if isinstance(node, Identifier):
            t = env.lookup_var(node.name)
            if t is None:
                self._error(f"undefined variable '{node.name}'", node)
                return T_UNKNOWN
            return t

        if isinstance(node, BinaryOp):
            return self._infer_binary(node, env)

        if isinstance(node, UnaryOp):
            operand_type = self._infer(node.operand, env)
            if node.op == "-":
                if self._is_compatible(operand_type, T_INT) or self._is_compatible(operand_type, T_FLOAT):
                    return operand_type
                self._error(f"unary '-' requires Int/Float, got {operand_type}", node)
                return T_UNKNOWN
            elif node.op == "!":
                if not self._is_compatible(operand_type, T_BOOL):
                    self._error(f"unary '!' requires Bool, got {operand_type}", node)
                return T_BOOL
            elif node.op == "~":
                if not self._is_compatible(operand_type, T_INT):
                    self._error(f"unary '~' requires Int, got {operand_type}", node)
                return T_INT
            return T_UNKNOWN

        if isinstance(node, Assignment):
            val_type = self._infer(node.value, env)
            if isinstance(node.target, Identifier):
                var_type = env.lookup_var(node.target.name)
                if var_type and not self._is_compatible(val_type, var_type):
                    self._error(
                        f"assignment to '{node.target.name}': expected {var_type}, got {val_type}",
                        node
                    )
                return val_type
            return val_type

        if isinstance(node, IndexAccess):
            target_type = self._infer(node.target, env)
            self._infer(node.index, env)
            if isinstance(target_type, ATCGenericType):
                return target_type.elem_type
            return T_ANY

        if isinstance(node, DotAccess):
            self._infer(node.target, env)
            return T_ANY  # Would need struct/contract field info

        if isinstance(node, NamespaceAccess):
            return T_ANY  # ATC:: namespace calls

        if isinstance(node, FunctionCall):
            return self._infer_call(node, env)

        if isinstance(node, TypeAnnotation):
            return self._resolve_type(node)

        # Unknown expression
        return T_UNKNOWN

    def _infer_binary(self, node: BinaryOp, env: TypeEnvironment) -> ATCType:
        left = self._infer(node.left, env)
        right = self._infer(node.right, env)
        op = node.op

        # Arithmetic operators
        if op in ("+", "-", "*", "/", "%", "**"):
            # String concat
            if op == "+" and self._is_compatible(left, T_STRING) and self._is_compatible(right, T_STRING):
                return T_STRING
            # Numeric arithmetic
            if self._is_numeric(left) and self._is_numeric(right):
                if self._is_compatible(left, T_FLOAT) or self._is_compatible(right, T_FLOAT):
                    return T_FLOAT
                return T_INT
            self._error(f"operator '{op}' requires numeric operands, got {left} and {right}", node)
            return T_UNKNOWN

        # Comparison operators
        if op in ("==", "!=", "<", ">", "<=", ">="):
            if not self._is_compatible(left, right):
                self._warning(f"comparison between different types: {left} and {right}", node)
            return T_BOOL

        # Logical operators
        if op in ("&&", "and", "||", "or"):
            if not self._is_compatible(left, T_BOOL) or not self._is_compatible(right, T_BOOL):
                self._error(f"logical '{op}' requires Bool operands, got {left} and {right}", node)
            return T_BOOL

        # Bitwise operators
        if op in ("&", "|", "^", "<<", ">>"):
            if not self._is_numeric(left) or not self._is_numeric(right):
                self._error(f"bitwise '{op}' requires Int operands, got {left} and {right}", node)
            return T_INT

        # Assignment operators
        if op in ("+=", "-=", "*=", "/="):
            if not self._is_numeric(left) or not self._is_numeric(right):
                self._error(f"compound '{op}' requires numeric operands", node)
            return left

        return T_UNKNOWN

    def _infer_call(self, node: FunctionCall, env: TypeEnvironment) -> ATCType:
        # Get function name
        if isinstance(node.target, Identifier):
            fname = node.target.name
            sig = env.lookup_function(fname)
            if sig:
                param_types, ret_type = sig
                # Check argument count
                if len(node.args) != len(param_types) and T_ANY not in param_types:
                    self._error(
                        f"function '{fname}' expects {len(param_types)} args, got {len(node.args)}",
                        node
                    )
                # Check argument types (skip Any params)
                for i, (arg, expected) in enumerate(zip(node.args, param_types)):
                    if expected == T_ANY: continue
                    arg_type = self._infer(arg, env)
                    if not self._is_compatible(arg_type, expected):
                        self._error(
                            f"function '{fname}' arg {i}: expected {expected}, got {arg_type}",
                            node
                        )
                return ret_type
            # Unknown function — not necessarily an error (could be stdlib)
            for arg in node.args:
                self._infer(arg, env)
            return T_UNKNOWN

        elif isinstance(node.target, NamespaceAccess):
            # ATC::Crypto::sha256(...) etc.
            for arg in node.args:
                self._infer(arg, env)
            return T_ANY

        # Method call
        for arg in node.args:
            self._infer(arg, env)
        return T_ANY

    # ── Type Resolution ──────────────────────────

    def _resolve_type(self, node: ASTNode) -> ATCType:
        if node is None:
            return T_VOID
        if isinstance(node, TypeAnnotation):
            tname = node.name
            if tname in ATC_TYPE_REGISTRY:
                return ATC_TYPE_REGISTRY[tname]
            # Unknown type — could be custom struct/enum
            return ATCType(tname)
        if isinstance(node, str):
            if node in ATC_TYPE_REGISTRY:
                return ATC_TYPE_REGISTRY[node]
            return ATCType(node)
        return T_UNKNOWN

    # ── Type Compatibility ───────────────────────

    def _is_compatible(self, a: ATCType, b: ATCType) -> bool:
        if a == T_ANY or b == T_ANY: return True
        if a == T_UNKNOWN or b == T_UNKNOWN: return True  # Don't error on unknown
        if a == b: return True
        # Int is compatible with UInt256 and vice versa
        if a in (T_INT, T_UINT256) and b in (T_INT, T_UINT256): return True
        # Int is compatible with Float
        if a == T_INT and b == T_FLOAT: return True
        if a == T_FLOAT and b == T_INT: return True
        # Null is compatible with nullable types
        if a == T_NULL and b != T_VOID: return True
        if b == T_NULL and a != T_VOID: return True
        return False

    def _is_numeric(self, t: ATCType) -> bool:
        return t in (T_INT, T_FLOAT, T_UINT256) or t == T_ANY or t == T_UNKNOWN

    # ── Error Reporting ──────────────────────────

    def _error(self, msg: str, node: ASTNode):
        line = getattr(node, 'line', 0)
        col = getattr(node, 'col', 0)
        self.errors.append(TypeError(msg, line, col))

    def _warning(self, msg: str, node: ASTNode):
        line = getattr(node, 'line', 0)
        col = getattr(node, 'col', 0)
        self.warnings.append(TypeError(msg, line, col))
