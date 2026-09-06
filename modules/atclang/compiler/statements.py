# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Statement Compilation
========================================

Compiles ATCLang AST statements into ATC bytecode.

Responsibilities
----------------
- let / const declarations
- assignments
- return
- expression statements
- require / emit
- if / elif / else
- while
- for
- break / continue
- state declarations
- import statements
- wallet declarations
- enum declarations

The module deliberately contains statement-level compilation only.
Expression compilation is delegated to ``expressions.py``.
Control-flow mechanics are delegated to ``control_flow.py``.
Function and contract compilation remain in their respective modules.
"""


from __future__ import annotations

from typing import TYPE_CHECKING, Any

from atclang.parser.ast_nodes import (
    ASTNode,
    Assignment,
    BreakStatement,
    ContinueStatement,
    EmitStatement,
    EnumDef,
    ExprStatement,
    ForStatement,
    IfStatement,
    ImportStatement,
    LetStatement,
    RequireStatement,
    ReturnStatement,
    StateField,
    WhileStatement,
    WalletDef,
)

from atclang.vm.atcvm import OP

from .errors import CompileError

if TYPE_CHECKING:
    from .context import CompilerContext
    from .symbols import SymbolTable


class StatementCompiler:
    """
    Statement-level ATCLang compiler.

    The compiler operates on a shared :class:`CompilerContext`.
    """

    def __init__(self, context: CompilerContext):
        self.ctx = context

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compile(self, node: ASTNode, scope: SymbolTable | None = None) -> None:
        """
        Compile one AST statement.

        ``scope`` defaults to the current compiler scope.
        """
        if scope is None:
            scope = self.ctx.scope

        if isinstance(node, LetStatement):
            self.compile_let(node, scope)

        elif isinstance(node, ReturnStatement):
            self.compile_return(node, scope)

        elif isinstance(node, Assignment):
            self.compile_assignment(node, scope)

        elif isinstance(node, ExprStatement):
            self.compile_expression_statement(node, scope)

        elif isinstance(node, EmitStatement):
            self.compile_emit(node, scope)

        elif isinstance(node, RequireStatement):
            self.compile_require(node, scope)

        elif isinstance(node, IfStatement):
            self.compile_if(node, scope)

        elif isinstance(node, WhileStatement):
            self.compile_while(node, scope)

        elif isinstance(node, ForStatement):
            self.compile_for(node, scope)

        elif isinstance(node, BreakStatement):
            self.compile_break(node)

        elif isinstance(node, ContinueStatement):
            self.compile_continue(node)

        elif isinstance(node, StateField):
            self.compile_state_field(node, scope)

        elif isinstance(node, WalletDef):
            self.compile_wallet(node, scope)

        elif isinstance(node, ImportStatement):
            self.compile_import(node, scope)

        elif isinstance(node, EnumDef):
            self.compile_enum(node, scope)

        else:
            raise CompileError(
                f"Unsupported statement type: {type(node).__name__}"
            )

    # ------------------------------------------------------------------
    # Declarations
    # ------------------------------------------------------------------

    def compile_let(
        self,
        node: LetStatement,
        scope: SymbolTable,
    ) -> None:
        """
        Compile:

            let x = expr
            const x = expr
        """

        if node.value is not None:
            self.ctx.expressions.compile(node.value, scope)
        else:
            self.ctx.emit(OP.PUSH, None, node=node)

        symbol = scope.define(
            node.name,
            kind="local" if scope.parent is not None else "global",
            typ=self._type_name(node),
        )

        self.ctx.emit(
            OP.STORE,
            node.name,
            node=node,
        )

        # Preserve declaration metadata for later compiler passes.
        if hasattr(symbol, "is_const"):
            symbol.is_const = bool(getattr(node, "is_const", False))

    def compile_assignment(
        self,
        node: Assignment,
        scope: SymbolTable,
    ) -> None:
        """
        Compile assignment expressions used as statements.

        Assignment targets:

            x = value
            obj.field = value
            array[index] = value
        """

        self.ctx.expressions.compile_assignment(node, scope)

    # ------------------------------------------------------------------
    # Expression statements
    # ------------------------------------------------------------------

    def compile_expression_statement(
        self,
        node: ExprStatement,
        scope: SymbolTable,
    ) -> None:
        self.ctx.expressions.compile(node.expr, scope)

        # Expression statements do not retain their result.
        self.ctx.emit(OP.POP, node=node)

    # ------------------------------------------------------------------
    # Return
    # ------------------------------------------------------------------

    def compile_return(
        self,
        node: ReturnStatement,
        scope: SymbolTable,
    ) -> None:
        if node.value is not None:
            self.ctx.expressions.compile(node.value, scope)
        else:
            self.ctx.emit(OP.PUSH, None, node=node)

        self.ctx.emit(OP.RETURN, node=node)

        # Used by control-flow / dead-code analysis.
        self.ctx.mark_terminated()

    # ------------------------------------------------------------------
    # Events / require
    # ------------------------------------------------------------------

    def compile_emit(
        self,
        node: EmitStatement,
        scope: SymbolTable,
    ) -> None:
        for arg in node.args:
            self.ctx.expressions.compile(arg, scope)

        self.ctx.emit(
            OP.EMIT,
            node.event,
            len(node.args),
            node=node,
        )

    def compile_require(
        self,
        node: RequireStatement,
        scope: SymbolTable,
    ) -> None:
        self.ctx.expressions.compile(
            node.condition,
            scope,
        )

        message = ""

        if node.message is not None:
            self.ctx.expressions.compile(
                node.message,
                scope,
            )

            # Runtime supports the compact REQUIRE(message) form.
            # Keep the source message available where possible.
            if hasattr(node.message, "value"):
                message = str(node.message.value)

        self.ctx.emit(
            OP.REQUIRE,
            message,
            node=node,
        )

    # ------------------------------------------------------------------
    # If / elif / else
    # ------------------------------------------------------------------

    def compile_if(
        self,
        node: IfStatement,
        scope: SymbolTable,
    ) -> None:
        """
        Compile conditional control flow through the control-flow manager.
        """

        self.ctx.control_flow.compile_if(
            node,
            scope,
            self.compile,
        )

    # ------------------------------------------------------------------
    # While
    # ------------------------------------------------------------------

    def compile_while(
        self,
        node: WhileStatement,
        scope: SymbolTable,
    ) -> None:
        """
        Compile:

            while condition {
                ...
            }
        """

        self.ctx.control_flow.compile_while(
            node,
            scope,
            self.compile,
        )

    # ------------------------------------------------------------------
    # For
    # ------------------------------------------------------------------

    def compile_for(
        self,
        node: ForStatement,
        scope: SymbolTable,
    ) -> None:
        """
        Compile:

            for item in iterable {
                ...
            }

        The implementation is delegated to the control-flow subsystem.
        """

        self.ctx.control_flow.compile_for(
            node,
            scope,
            self.compile,
        )

    # ------------------------------------------------------------------
    # Break / Continue
    # ------------------------------------------------------------------

    def compile_break(self, node: BreakStatement) -> None:
        if not self.ctx.control_flow.in_loop:
            raise CompileError(
                f"break outside loop @ line {getattr(node, 'line', 0)}"
            )

        self.ctx.control_flow.emit_break(node)

        self.ctx.mark_terminated()

    def compile_continue(
        self,
        node: ContinueStatement,
    ) -> None:
        if not self.ctx.control_flow.in_loop:
            raise CompileError(
                f"continue outside loop @ line {getattr(node, 'line', 0)}"
            )

        self.ctx.control_flow.emit_continue(node)

        self.ctx.mark_terminated()

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    def compile_state_field(
        self,
        node: StateField,
        scope: SymbolTable,
    ) -> None:
        """
        State fields are represented as persistent contract metadata.

        Initialization itself is handled by ``contracts.py``.
        """

        state_type = self._type_name(node)

        scope.define(
            node.name,
            kind="state",
            typ=state_type,
        )

        # State declarations normally produce no runtime instruction here.
        self.ctx.register_state(
            name=node.name,
            typ=state_type,
            node=node,
        )

    # ------------------------------------------------------------------
    # Wallet
    # ------------------------------------------------------------------

    def compile_wallet(
        self,
        node: WalletDef,
        scope: SymbolTable,
    ) -> None:
        """
        Compile wallet declaration.

        Example:

            wallet owner = ATC::Wallet::new(...)
        """

        if node.value is not None:
            self.ctx.expressions.compile(
                node.value,
                scope,
            )
        else:
            self.ctx.emit(
                OP.PUSH,
                None,
                node=node,
            )

        scope.define(
            node.name,
            kind="global",
            typ="ATCWallet",
        )

        self.ctx.emit(
            OP.STORE,
            node.name,
            node=node,
        )

    # ------------------------------------------------------------------
    # Imports
    # ------------------------------------------------------------------

    def compile_import(
        self,
        node: ImportStatement,
        scope: SymbolTable,
    ) -> None:
        """
        Compile module import.

        Import resolution is a runtime/module-loader concern.
        """

        path = "::".join(node.path)

        self.ctx.emit(
            OP.CALL_EXT,
            f"ATC::Import::{path}",
            0,
            node=node,
        )

        if node.alias:
            scope.define(
                node.alias,
                kind="global",
                typ="module",
            )

            self.ctx.emit(
                OP.STORE,
                node.alias,
                node=node,
            )

    # ------------------------------------------------------------------
    # Enum
    # ------------------------------------------------------------------

    def compile_enum(
        self,
        node: EnumDef,
        scope: SymbolTable,
    ) -> None:
        """
        Compile enum metadata.

        Each variant receives a deterministic integer discriminator.
        """

        variants = list(node.variants)

        for index, variant in enumerate(variants):
            qualified_name = f"{node.name}::{variant}"

            self.ctx.emit(
                OP.PUSH,
                index,
                node=node,
            )

            self.ctx.emit(
                OP.STORE,
                qualified_name,
                node=node,
            )

        enum_values = {
            variant: index
            for index, variant in enumerate(variants)
        }

        self.ctx.emit(
            OP.PUSH,
            enum_values,
            node=node,
        )

        self.ctx.emit(
            OP.STORE,
            node.name,
            node=node,
        )

        scope.define(
            node.name,
            kind="global",
            typ=f"enum:{node.name}",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _type_name(node: Any) -> str:
        """
        Extract a stable type name from AST type annotations.
        """

        annotation = getattr(node, "type_hint", None)

        if annotation is None:
            return ""

        name = getattr(annotation, "name", None)

        if name is not None:
            return str(name)

        return str(annotation)


def compile_statement(
    context: CompilerContext,
    node: ASTNode,
    scope: SymbolTable | None = None,
) -> None:
    """
    Functional convenience API.

    Allows ``compiler.py`` and tests to compile a single statement
    without directly instantiating ``StatementCompiler``.
    """

    StatementCompiler(context).compile(
        node,
        scope,
    )


__all__ = [
    "StatementCompiler",
    "compile_statement",
]