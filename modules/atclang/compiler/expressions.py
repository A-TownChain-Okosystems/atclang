# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Expression Compilation
==========================================

Compiles ATCLang AST expressions into ATC bytecode.

Responsibilities
----------------
- Literal expressions
- Identifiers
- Namespace access
- Unary expressions
- Binary expressions
- Ternary expressions
- Function calls
- Index access
- Field access
- Assignments
- Collection literals
- Struct/object literals
- Cast expressions
- Tuple expressions

Architecture
------------
    AST Expression
          │
          ▼
    ExpressionCompiler
          │
          ├── CompilerContext
          ├── SymbolTable
          ├── ConstantPool
          └── BytecodeEmitter
          │
          ▼
      ATC Bytecode

This module intentionally contains no parser or VM implementation.

ATC-92
ATCLang Compiler Pipeline
"""

from __future__ import annotations

from typing import Any, Optional

from atclang.parser.ast_nodes import (
    ASTNode,
    IntLiteral,
    FloatLiteral,
    StringLiteral,
    BoolLiteral,
    NullLiteral,
    Identifier,
    NamespaceAccess,
    BinaryOp,
    UnaryOp,
    IndexAccess,
    DotAccess,
    FunctionCall,
    Assignment,
    ListLiteral,
    MapLiteral,
    StructLiteral,
    TernaryExpr,
    CastExpr,
    TupleExpr,
)

from atclang.vm.atcvm import OP

from .context import CompilerContext
from .errors import CompileError


class ExpressionCompiler:
    """
    Compile ATCLang expressions into ATC bytecode.

    The compiler operates against a CompilerContext rather than
    owning compiler-global state itself.
    """

    def __init__(self, context: CompilerContext):
        self.ctx = context

    # ==============================================================
    # PUBLIC API
    # ==============================================================

    def compile(
        self,
        node: ASTNode,
        *,
        scope=None,
    ) -> None:
        """
        Compile one expression.

        The resulting expression value remains on the VM stack unless
        the expression itself has assignment semantics.
        """
        if node is None:
            self.error("Cannot compile a null expression")

        if scope is None:
            scope = self.ctx.scope

        # ----------------------------------------------------------
        # Literals
        # ----------------------------------------------------------

        if isinstance(node, IntLiteral):
            self._literal(node.value, node)
            return

        if isinstance(node, FloatLiteral):
            self._literal(node.value, node)
            return

        if isinstance(node, StringLiteral):
            self._literal(node.value, node)
            return

        if isinstance(node, BoolLiteral):
            self._literal(node.value, node)
            return

        if isinstance(node, NullLiteral):
            self._literal(None, node)
            return

        # ----------------------------------------------------------
        # Identifier / Namespace
        # ----------------------------------------------------------

        if isinstance(node, Identifier):
            self._identifier(node, scope)
            return

        if isinstance(node, NamespaceAccess):
            self._namespace_access(node)
            return

        # ----------------------------------------------------------
        # Operators
        # ----------------------------------------------------------

        if isinstance(node, BinaryOp):
            self._binary(node, scope)
            return

        if isinstance(node, UnaryOp):
            self._unary(node, scope)
            return

        if isinstance(node, TernaryExpr):
            self._ternary(node, scope)
            return

        # ----------------------------------------------------------
        # Access
        # ----------------------------------------------------------

        if isinstance(node, IndexAccess):
            self._index_access(node, scope)
            return

        if isinstance(node, DotAccess):
            self._dot_access(node, scope)
            return

        # ----------------------------------------------------------
        # Calls
        # ----------------------------------------------------------

        if isinstance(node, FunctionCall):
            self._function_call(node, scope)
            return

        # ----------------------------------------------------------
        # Assignment
        # ----------------------------------------------------------

        if isinstance(node, Assignment):
            self._assignment(node, scope)
            return

        # ----------------------------------------------------------
        # Collections / Objects
        # ----------------------------------------------------------

        if isinstance(node, ListLiteral):
            self._list_literal(node, scope)
            return

        if isinstance(node, MapLiteral):
            self._map_literal(node, scope)
            return

        if isinstance(node, StructLiteral):
            self._struct_literal(node, scope)
            return

        if isinstance(node, TupleExpr):
            self._tuple_literal(node, scope)
            return

        # ----------------------------------------------------------
        # Type operations
        # ----------------------------------------------------------

        if isinstance(node, CastExpr):
            self._cast(node, scope)
            return

        self.error(
            f"Unknown expression type: {type(node).__name__}",
            node,
        )

    # ==============================================================
    # LITERALS
    # ==============================================================

    def _literal(self, value: Any, node: ASTNode) -> None:
        """
        Emit a literal.

        Constants are routed through the compiler constant pool when
        the context provides one. Primitive values may also be emitted
        directly because ATC PUSH supports immediate values.
        """
        emit = self.ctx.emit

        emit(
            OP.PUSH,
            value,
            node=node,
        )

    # ==============================================================
    # IDENTIFIERS
    # ==============================================================

    def _identifier(self, node: Identifier, scope) -> None:
        symbol = self._resolve(scope, node.name)

        if symbol is not None:
            self.ctx.emit(
                OP.LOAD,
                node.name,
                node=node,
            )
            return

        # Unresolved identifiers are intentionally emitted as LOAD.
        #
        # This permits:
        #   - runtime globals
        #   - builtins
        #   - imported symbols
        #   - host-provided capabilities
        #
        # Static rejection belongs to TypeChecker/name resolution,
        # not to this low-level expression emitter.

        self.ctx.emit(
            OP.LOAD,
            node.name,
            node=node,
        )

    # ==============================================================
    # NAMESPACE ACCESS
    # ==============================================================

    def _namespace_access(
        self,
        node: NamespaceAccess,
    ) -> None:
        """
        Compile:

            ATC::Wallet::new

        into a qualified runtime reference.
        """
        parts = getattr(node, "parts", None)

        if not parts:
            self.error(
                "NamespaceAccess contains no namespace components",
                node,
            )

        name = "::".join(str(part) for part in parts)

        self.ctx.emit(
            OP.PUSH,
            name,
            node=node,
        )

    # ==============================================================
    # BINARY OPERATORS
    # ==============================================================

    def _binary(
        self,
        node: BinaryOp,
        scope,
    ) -> None:
        self.compile(node.left, scope=scope)
        self.compile(node.right, scope=scope)

        opcode = self._binary_opcode(node.op)

        if opcode is None:
            self.error(
                f"Unknown binary operator: '{node.op}'",
                node,
            )

        self.ctx.emit(
            opcode,
            node=node,
        )

    def _binary_opcode(self, operator: str) -> Optional[OP]:
        """
        ATCLang operator → ATC VM opcode.
        """

        return {
            # Arithmetic
            "+": OP.ADD,
            "-": OP.SUB,
            "*": OP.MUL,
            "/": OP.DIV,
            "%": OP.MOD,
            "**": OP.POW,

            # Comparison
            "==": OP.EQ,
            "!=": OP.NEQ,
            "<": OP.LT,
            ">": OP.GT,
            "<=": OP.LTE,
            ">=": OP.GTE,

            # Logical
            "&&": OP.AND,
            "and": OP.AND,
            "||": OP.OR,
            "or": OP.OR,

            # Bitwise
            "&": OP.BITAND,
            "|": OP.BITOR,
            "^": OP.BITXOR,
            "<<": OP.SHL,
            ">>": OP.SHR,
        }.get(operator)

    # ==============================================================
    # UNARY OPERATORS
    # ==============================================================

    def _unary(
        self,
        node: UnaryOp,
        scope,
    ) -> None:
        self.compile(node.operand, scope=scope)

        opcode = {
            "-": OP.NEG,
            "!": OP.NOT,
        }.get(node.op)

        if opcode is None:
            self.error(
                f"Unknown unary operator: '{node.op}'",
                node,
            )

        self.ctx.emit(
            opcode,
            node=node,
        )

    # ==============================================================
    # INDEX ACCESS
    # ==============================================================

    def _index_access(
        self,
        node: IndexAccess,
        scope,
    ) -> None:
        """
        Compile:

            value[index]
        """

        self.compile(node.target, scope=scope)
        self.compile(node.index, scope=scope)

        self.ctx.emit(
            OP.LOAD_IDX,
            node=node,
        )

    # ==============================================================
    # FIELD ACCESS
    # ==============================================================

    def _dot_access(
        self,
        node: DotAccess,
        scope,
    ) -> None:
        """
        Compile:

            object.field
        """

        self.compile(node.target, scope=scope)

        field_name = getattr(node, "field_name", None)

        if not field_name:
            self.error(
                "DotAccess has no field name",
                node,
            )

        self.ctx.emit(
            OP.GET_FIELD,
            field_name,
            node=node,
        )

    # ==============================================================
    # FUNCTION CALLS
    # ==============================================================

    def _function_call(
        self,
        node: FunctionCall,
        scope,
    ) -> None:
        """
        Compile function calls.

        Supported forms:

            foo(a, b)
            print(x)
            ATC::Wallet::new(...)
            object.method(...)
            dynamic(...)
        """

        args = getattr(node, "args", None) or []

        # ----------------------------------------------------------
        # Arguments
        # ----------------------------------------------------------

        for arg in args:
            self.compile(arg, scope=scope)

        target = node.target

        # ----------------------------------------------------------
        # Direct identifier call
        # ----------------------------------------------------------

        if isinstance(target, Identifier):
            function_name = target.name

            # Builtin print
            if function_name == "print":
                self.ctx.emit(
                    OP.PRINT,
                    node=node,
                )
                return

            self.ctx.emit(
                OP.CALL,
                function_name,
                len(args),
                node=node,
            )
            return

        # ----------------------------------------------------------
        # Namespace call
        # ----------------------------------------------------------

        if isinstance(target, NamespaceAccess):
            parts = getattr(target, "parts", None)

            if not parts:
                self.error(
                    "Namespace function call has no namespace",
                    node,
                )

            function_name = "::".join(
                str(part) for part in parts
            )

            self.ctx.emit(
                OP.CALL_EXT,
                function_name,
                len(args),
                node=node,
            )
            return

        # ----------------------------------------------------------
        # Method call
        # ----------------------------------------------------------

        if isinstance(target, DotAccess):
            self.compile(
                target.target,
                scope=scope,
            )

            self.ctx.emit(
                OP.CALL,
                target.field_name,
                len(args) + 1,
                node=node,
            )
            return

        # ----------------------------------------------------------
        # Dynamic call
        # ----------------------------------------------------------

        self.compile(
            target,
            scope=scope,
        )

        self.ctx.emit(
            OP.CALL,
            "__dynamic__",
            len(args),
            node=node,
        )

    # ==============================================================
    # ASSIGNMENT
    # ==============================================================

    def _assignment(
        self,
        node: Assignment,
        scope,
    ) -> None:
        """
        Compile assignment targets.

        Supported:

            x = value
            obj.field = value
            array[index] = value
        """

        target = node.target
        value = node.value

        # ----------------------------------------------------------
        # Identifier
        # ----------------------------------------------------------

        if isinstance(target, Identifier):
            self.compile(value, scope=scope)

            self.ctx.emit(
                OP.STORE,
                target.name,
                node=node,
            )
            return

        # ----------------------------------------------------------
        # Indexed assignment
        # ----------------------------------------------------------

        if isinstance(target, IndexAccess):
            # Keep the canonical stack order:
            #
            #   value
            #   target
            #   index
            #
            # STORE_IDX consumes the three values.

            self.compile(value, scope=scope)
            self.compile(target.target, scope=scope)
            self.compile(target.index, scope=scope)

            self.ctx.emit(
                OP.STORE_IDX,
                node=node,
            )
            return

        # ----------------------------------------------------------
        # Field assignment
        # ----------------------------------------------------------

        if isinstance(target, DotAccess):
            self.compile(value, scope=scope)
            self.compile(target.target, scope=scope)

            self.ctx.emit(
                OP.SET_FIELD,
                target.field_name,
                node=node,
            )
            return

        self.error(
            f"Invalid assignment target: "
            f"{type(target).__name__}",
            node,
        )

    # ==============================================================
    # LIST
    # ==============================================================

    def _list_literal(
        self,
        node: ListLiteral,
        scope,
    ) -> None:
        elements = getattr(node, "elements", None) or []

        for element in elements:
            self.compile(
                element,
                scope=scope,
            )

        self.ctx.emit(
            OP.NEW_LIST,
            len(elements),
            node=node,
        )

    # ==============================================================
    # MAP
    # ==============================================================

    def _map_literal(
        self,
        node: MapLiteral,
        scope,
    ) -> None:
        pairs = getattr(node, "pairs", None) or []

        for pair in pairs:
            key, value = self._map_pair(pair)

            # Preserve compiler/VM stack convention:
            #
            #   value
            #   key
            #
            self.compile(
                value,
                scope=scope,
            )

            self.compile(
                key,
                scope=scope,
            )

        self.ctx.emit(
            OP.NEW_MAP,
            len(pairs),
            node=node,
        )

    def _map_pair(self, pair):
        """
        Normalize the different AST map-pair representations.
        """

        if isinstance(pair, tuple):
            if len(pair) >= 2:
                return pair[0], pair[1]

        if isinstance(pair, dict):
            return (
                pair.get("key"),
                pair.get("value"),
            )

        # Defensive fallback.
        return pair, None

    # ==============================================================
    # STRUCT LITERAL
    # ==============================================================

    def _struct_literal(
        self,
        node: StructLiteral,
        scope,
    ) -> None:
        fields = getattr(node, "fields", None) or []

        for field_name, field_value in fields:
            self.compile(
                field_value,
                scope=scope,
            )

        struct_name = (
            getattr(node, "struct_name", None)
            or "struct"
        )

        self.ctx.emit(
            OP.NEW_OBJ,
            struct_name,
            len(fields),
            node=node,
        )

    # ==============================================================
    # TUPLE
    # ==============================================================

    def _tuple_literal(
        self,
        node: TupleExpr,
        scope,
    ) -> None:
        elements = getattr(node, "elements", None) or []

        for element in elements:
            self.compile(
                element,
                scope=scope,
            )

        # Current ATC VM representation uses the list constructor
        # for tuple values. This keeps tuple semantics compatible
        # with indexed access while preserving deterministic ordering.
        self.ctx.emit(
            OP.NEW_LIST,
            len(elements),
            node=node,
        )

    # ==============================================================
    # TERNARY
    # ==============================================================

    def _ternary(
        self,
        node: TernaryExpr,
        scope,
    ) -> None:
        """
        Compile:

            condition ? then_expr : else_expr
        """

        self.compile(
            node.cond,
            scope=scope,
        )

        jump_else = self.ctx.emit(
            OP.JUMP_NOT,
            0,
            node=node,
        )

        self.compile(
            node.then_expr,
            scope=scope,
        )

        jump_end = self.ctx.emit(
            OP.JUMP,
            0,
            node=node,
        )

        else_position = self.ctx.position()

        self.ctx.patch(
            jump_else,
            else_position,
        )

        self.compile(
            node.else_expr,
            scope=scope,
        )

        end_position = self.ctx.position()

        self.ctx.patch(
            jump_end,
            end_position,
        )

    # ==============================================================
    # CAST
    # ==============================================================

    def _cast(
        self,
        node: CastExpr,
        scope,
    ) -> None:
        value = getattr(
            node,
            "value",
            None,
        )

        if value is None:
            value = getattr(
                node,
                "operand",
                None,
            )

        if value is None:
            self.error(
                "Cast expression has no operand",
                node,
            )

        self.compile(
            value,
            scope=scope,
        )

        target_type = getattr(
            node,
            "target_type",
            None,
        )

        if target_type is None:
            target_type = "Any"

        # Normalize AST type objects to a stable runtime representation.
        if hasattr(target_type, "name"):
            target_type = target_type.name

        self.ctx.emit(
            OP.CAST,
            target_type,
            node=node,
        )

    # ==============================================================
    # SYMBOL RESOLUTION
    # ==============================================================

    @staticmethod
    def _resolve(scope, name: str):
        """
        Resolve a symbol against the active scope.

        Supports both:
            scope.resolve(name)

        and contexts exposing:
            context.resolve(name)
        """

        if scope is None:
            return None

        resolver = getattr(
            scope,
            "resolve",
            None,
        )

        if callable(resolver):
            return resolver(name)

        return None

    # ==============================================================
    # ERROR HANDLING
    # ==============================================================

    def error(
        self,
        message: str,
        node: Optional[ASTNode] = None,
    ) -> None:
        """
        Raise a compiler error with source location.
        """

        line = getattr(
            node,
            "line",
            None,
        )

        col = getattr(
            node,
            "col",
            None,
        )

        if line is not None:
            if col is not None:
                message = (
                    f"{message} "
                    f"(line {line}, column {col})"
                )
            else:
                message = (
                    f"{message} "
                    f"(line {line})"
                )

        raise CompileError(
            f"[ATCCompiler] {message}"
        )


# ==================================================================
# COMPATIBILITY FUNCTION
# ==================================================================

def compile_expression(
    context: CompilerContext,
    node: ASTNode,
    scope=None,
) -> None:
    """
    Functional API for callers that do not need a persistent
    ExpressionCompiler instance.
    """

    compiler = ExpressionCompiler(context)

    compiler.compile(
        node,
        scope=scope,
    )


__all__ = [
    "ExpressionCompiler",
    "compile_expression",
]