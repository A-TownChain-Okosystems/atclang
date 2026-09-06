# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Control Flow
================================

ATC-92 | Compiler Backend

Verantwortlich für:
    - if / elif / else
    - while
    - for
    - break
    - continue
    - Jump-Emission und Backpatching
    - verschachtelte Control-Flow-Kontexte

Dieses Modul enthält ausschließlich Control-Flow-Logik.
Die eigentliche Bytecode-Repräsentation wird durch bytecode.py
und der Compilerzustand durch context.py verwaltet.

Designziele:
    - deterministische Codegenerierung
    - korrekte Jump-Targets
    - verschachtelte Loops
    - sichere break/continue-Semantik
    - keine globale mutable Control-Flow-State
    - Source-Map-kompatible Emission
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Sequence, Tuple

from atclang.vm.atcvm import OP, Instruction

try:
    from atclang.parser.ast_nodes import (
        ASTNode,
        IfStatement,
        WhileStatement,
        ForStatement,
        BreakStatement,
        ContinueStatement,
    )
except ImportError:  # pragma: no cover
    ASTNode = Any
    IfStatement = Any
    WhileStatement = Any
    ForStatement = Any
    BreakStatement = Any
    ContinueStatement = Any


# ══════════════════════════════════════════════════════════
# TYPES
# ══════════════════════════════════════════════════════════

ExpressionCompiler = Callable[[Any, Any], None]
StatementCompiler = Callable[[Any, Any], None]


class ControlFlowError(Exception):
    """Fehler während der Control-Flow-Kompilierung."""


@dataclass
class LoopContext:
    """
    Kontext eines aktiven Loops.

    break_target:
        Instruction index, zu dem break springt.
        None während der Loop-Body kompiliert wird.

    continue_target:
        Instruction index, zu dem continue springt.
        None während der Loop-Header kompiliert wird.

    break_jumps:
        Noch nicht gepatchte break-Jumps.

    continue_jumps:
        Noch nicht gepatchte continue-Jumps.

    loop_start:
        Beginn des Loop-Headers.
    """

    loop_start: int

    break_target: Optional[int] = None
    continue_target: Optional[int] = None

    break_jumps: List[int] = None
    continue_jumps: List[int] = None

    def __post_init__(self) -> None:
        if self.break_jumps is None:
            self.break_jumps = []

        if self.continue_jumps is None:
            self.continue_jumps = []


@dataclass
class IfContext:
    """
    Temporärer Kontext einer if/elif/else-Kette.
    """

    end_jumps: List[int]

    condition_jump: Optional[int] = None


# ══════════════════════════════════════════════════════════
# CONTROL FLOW COMPILER
# ══════════════════════════════════════════════════════════

class ControlFlowCompiler:
    """
    Compiler für Control-Flow-Konstrukte.

    Der Compiler wird bewusst über Callbacks an den Hauptcompiler
    angebunden. Dadurch bleibt die Control-Flow-Implementierung
    unabhängig von Expression- und Statement-Details.

    Erwartete Compiler-API:

        emit(op, *args, line=0, col=0) -> int
        patch(index, *args)
        current_pos() -> int

    Zusätzlich werden zwei Callbacks benötigt:

        compile_expr(node, scope)
        compile_stmt(node, scope)
    """

    def __init__(
        self,
        compiler: Any,
        compile_expr: Optional[ExpressionCompiler] = None,
        compile_stmt: Optional[StatementCompiler] = None,
    ) -> None:
        self.compiler = compiler

        self.compile_expr = compile_expr
        self.compile_stmt = compile_stmt

        self._loops: List[LoopContext] = []

    # ══════════════════════════════════════════════════════
    # BASIC HELPERS
    # ══════════════════════════════════════════════════════

    @property
    def instructions(self) -> List[Instruction]:
        return self.compiler.instructions

    def emit(
        self,
        op: OP,
        *args: Any,
        node: Optional[Any] = None,
    ) -> int:
        """
        Delegiert Instruction-Emission an den Hauptcompiler.
        """

        line = getattr(node, "line", 0) if node is not None else 0
        col = getattr(node, "col", 0) if node is not None else 0

        return self.compiler.emit(
            op,
            *args,
            line=line,
            col=col,
        )

    def patch(self, index: int, *args: Any) -> None:
        """Patcht ein Jump-Target."""

        if index < 0 or index >= len(self.instructions):
            raise ControlFlowError(
                f"Invalid jump patch index: {index}"
            )

        self.compiler.patch(index, *args)

    def current_pos(self) -> int:
        return len(self.instructions)

    # ══════════════════════════════════════════════════════
    # CALLBACK MANAGEMENT
    # ══════════════════════════════════════════════════════

    def set_callbacks(
        self,
        compile_expr: ExpressionCompiler,
        compile_stmt: StatementCompiler,
    ) -> None:
        """
        Setzt Compiler-Callbacks.

        Wird verwendet, wenn ControlFlowCompiler vor dem
        vollständigen Aufbau des Hauptcompilers erzeugt wird.
        """

        self.compile_expr = compile_expr
        self.compile_stmt = compile_stmt

    def _require_callbacks(self) -> None:
        if self.compile_expr is None:
            raise ControlFlowError(
                "Expression compiler callback is not configured"
            )

        if self.compile_stmt is None:
            raise ControlFlowError(
                "Statement compiler callback is not configured"
            )

    # ══════════════════════════════════════════════════════
    # SCOPE
    # ══════════════════════════════════════════════════════

    def _child_scope(self, scope: Any) -> Any:
        """
        Erzeugt einen Child-Scope, sofern die SymbolTable dies
        unterstützt.

        Fallback:
            Der aktuelle Scope wird verwendet.
        """

        child = getattr(scope, "child", None)

        if callable(child):
            return child()

        return scope

    # ══════════════════════════════════════════════════════
    # BLOCK
    # ══════════════════════════════════════════════════════

    def compile_block(
        self,
        statements: Sequence[Any],
        scope: Any,
    ) -> None:
        """Kompiliert einen Statement-Block."""

        self._require_callbacks()

        child_scope = self._child_scope(scope)

        for statement in statements:
            self.compile_stmt(statement, child_scope)

    # ══════════════════════════════════════════════════════
    # IF / ELIF / ELSE
    # ══════════════════════════════════════════════════════

    def compile_if(
        self,
        node: Any,
        scope: Any,
        *,
        preserve_result: bool = False,
    ) -> None:
        """
        Kompiliert:

            if condition {
                ...
            } elif condition {
                ...
            } else {
                ...
            }

        Jump-Struktur:

            condition
            JUMP_NOT else_or_elif

            then

            JUMP end

        elif:
            condition
            JUMP_NOT next

            body

            JUMP end

        else:
            body

        end:
        """

        self._require_callbacks()

        end_jumps: List[int] = []

        # ────────────────────────────────────────────────
        # IF
        # ────────────────────────────────────────────────

        condition = getattr(node, "condition", None)

        if condition is None:
            raise ControlFlowError(
                "IfStatement has no condition"
            )

        self.compile_expr(condition, scope)

        jump_false = self.emit(
            OP.JUMP_NOT,
            0,
            node=node,
        )

        then_block = getattr(node, "then_block", None)

        if then_block is None:
            then_block = []

        self.compile_block(
            then_block,
            scope,
        )

        elif_blocks = getattr(node, "elif_blocks", None) or []

        else_block = getattr(node, "else_block", None)

        has_alternative = bool(
            elif_blocks or else_block
        )

        if has_alternative:
            jump_end = self.emit(
                OP.JUMP,
                0,
                node=node,
            )

            end_jumps.append(jump_end)

        # ────────────────────────────────────────────────
        # NEXT CONDITION
        # ────────────────────────────────────────────────

        self.patch(
            jump_false,
            self.current_pos(),
        )

        # ────────────────────────────────────────────────
        # ELIF
        # ────────────────────────────────────────────────

        for elif_condition, elif_body in elif_blocks:

            self.compile_expr(
                elif_condition,
                scope,
            )

            elif_false = self.emit(
                OP.JUMP_NOT,
                0,
                node=node,
            )

            self.compile_block(
                elif_body,
                scope,
            )

            if else_block:
                jump_end = self.emit(
                    OP.JUMP,
                    0,
                    node=node,
                )

                end_jumps.append(jump_end)

            elif_index = self.current_pos()

            self.patch(
                elif_false,
                elif_index,
            )

        # ────────────────────────────────────────────────
        # ELSE
        # ────────────────────────────────────────────────

        if else_block:
            if not isinstance(else_block, (list, tuple)):
                else_block = [else_block]

            self.compile_block(
                else_block,
                scope,
            )

        # ────────────────────────────────────────────────
        # END
        # ────────────────────────────────────────────────

        end_pos = self.current_pos()

        for jump in end_jumps:
            self.patch(
                jump,
                end_pos,
            )

    # ══════════════════════════════════════════════════════
    # WHILE
    # ══════════════════════════════════════════════════════

    def compile_while(
        self,
        node: Any,
        scope: Any,
    ) -> None:
        """
        Kompiliert:

            while condition {
                body
            }

        Struktur:

            loop_start:
                condition
                JUMP_NOT loop_end

                body

                JUMP loop_start

            loop_end:
        """

        self._require_callbacks()

        loop_start = self.current_pos()

        context = LoopContext(
            loop_start=loop_start,
        )

        self._loops.append(context)

        try:
            condition = getattr(node, "condition", None)

            if condition is None:
                raise ControlFlowError(
                    "WhileStatement has no condition"
                )

            self.compile_expr(
                condition,
                scope,
            )

            jump_out = self.emit(
                OP.JUMP_NOT,
                0,
                node=node,
            )

            self.compile_block(
                getattr(node, "body", []) or [],
                scope,
            )

            # Continue bei while springt zurück zur Bedingung.
            context.continue_target = loop_start

            self.emit(
                OP.JUMP,
                loop_start,
                node=node,
            )

            loop_end = self.current_pos()

            # Bedingung false → Ende.
            self.patch(
                jump_out,
                loop_end,
            )

            context.break_target = loop_end

            # break-Jumps patchen.
            self._patch_context_jumps(context)

        finally:
            self._loops.pop()

    # ══════════════════════════════════════════════════════
    # FOR
    # ══════════════════════════════════════════════════════

    def compile_for(
        self,
        node: Any,
        scope: Any,
    ) -> None:
        """
        Kompiliert einen generischen for-loop.

        Semantik:

            for x in iterable {
                body
            }

        Wird auf eine indexbasierte Iteration reduziert:

            __iter = iterable
            __i = 0

            loop:
                if __i >= len(__iter):
                    end

                x = __iter[__i]

                body

                __i = __i + 1
                jump loop

        Die temporären Variablennamen werden mit einer eindeutigen
        Compiler-ID versehen, damit verschachtelte for-loops nicht
        kollidieren.
        """

        self._require_callbacks()

        iterable = getattr(node, "iterable", None)

        if iterable is None:
            raise ControlFlowError(
                "ForStatement has no iterable"
            )

        variable = getattr(node, "var", None)

        if not variable:
            raise ControlFlowError(
                "ForStatement has no loop variable"
            )

        # ────────────────────────────────────────────────
        # Unique temporaries
        # ────────────────────────────────────────────────

        counter = getattr(
            self.compiler,
            "_for_counter",
            0,
        )

        setattr(
            self.compiler,
            "_for_counter",
            counter + 1,
        )

        iterator_name = f"__atc_iter_{counter}"
        index_name = f"__atc_index_{counter}"

        # ────────────────────────────────────────────────
        # iterable
        # ────────────────────────────────────────────────

        self.compile_expr(
            iterable,
            scope,
        )

        self.emit(
            OP.STORE,
            iterator_name,
            node=node,
        )

        # index = 0
        self.emit(
            OP.PUSH,
            0,
            node=node,
        )

        self.emit(
            OP.STORE,
            index_name,
            node=node,
        )

        # ────────────────────────────────────────────────
        # LOOP
        # ────────────────────────────────────────────────

        loop_start = self.current_pos()

        context = LoopContext(
            loop_start=loop_start,
        )

        self._loops.append(context)

        try:
            # i
            self.emit(
                OP.LOAD,
                index_name,
                node=node,
            )

            # len(iter)
            self.emit(
                OP.LOAD,
                iterator_name,
                node=node,
            )

            self.emit(
                OP.CALL_EXT,
                "ATC::Std::len",
                1,
                node=node,
            )

            # i < len
            self.emit(
                OP.LT,
                node=node,
            )

            jump_out = self.emit(
                OP.JUMP_NOT,
                0,
                node=node,
            )

            # ────────────────────────────────────────────
            # loop variable = iterator[index]
            # ────────────────────────────────────────────

            self.emit(
                OP.LOAD,
                iterator_name,
                node=node,
            )

            self.emit(
                OP.LOAD,
                index_name,
                node=node,
            )

            self.emit(
                OP.LOAD_IDX,
                node=node,
            )

            self.emit(
                OP.STORE,
                variable,
                node=node,
            )

            # ────────────────────────────────────────────
            # BODY
            # ────────────────────────────────────────────

            body_scope = self._child_scope(scope)

            # Define loop variable if SymbolTable supports it.
            define = getattr(
                body_scope,
                "define",
                None,
            )

            if callable(define):
                try:
                    existing = body_scope.resolve(variable)
                except Exception:
                    existing = None

                if existing is None:
                    define(
                        variable,
                        "local",
                        "",
                    )

            self.compile_block(
                getattr(node, "body", []) or [],
                body_scope,
            )

            # continue target = increment
            context.continue_target = self.current_pos()

            # i = i + 1
            self.emit(
                OP.LOAD,
                index_name,
                node=node,
            )

            self.emit(
                OP.PUSH,
                1,
                node=node,
            )

            self.emit(
                OP.ADD,
                node=node,
            )

            self.emit(
                OP.STORE,
                index_name,
                node=node,
            )

            # loop
            self.emit(
                OP.JUMP,
                loop_start,
                node=node,
            )

            loop_end = self.current_pos()

            self.patch(
                jump_out,
                loop_end,
            )

            context.break_target = loop_end

            self._patch_context_jumps(context)

        finally:
            self._loops.pop()

    # ══════════════════════════════════════════════════════
    # BREAK
    # ══════════════════════════════════════════════════════

    def compile_break(
        self,
        node: Any,
    ) -> None:
        """
        Kompiliert break.

        Der Jump wird zunächst als Placeholder emittiert und
        beim Verlassen des Loops gepatcht.
        """

        if not self._loops:
            raise ControlFlowError(
                "break außerhalb einer Schleife"
            )

        jump = self.emit(
            OP.JUMP,
            0,
            node=node,
        )

        self._loops[-1].break_jumps.append(
            jump
        )

    # ══════════════════════════════════════════════════════
    # CONTINUE
    # ══════════════════════════════════════════════════════

    def compile_continue(
        self,
        node: Any,
    ) -> None:
        """
        Kompiliert continue.

        Bei while:
            → loop_start

        Bei for:
            → increment section
        """

        if not self._loops:
            raise ControlFlowError(
                "continue außerhalb einer Schleife"
            )

        context = self._loops[-1]

        if context.continue_target is None:
            jump = self.emit(
                OP.JUMP,
                0,
                node=node,
            )

            context.continue_jumps.append(
                jump
            )

        else:
            self.emit(
                OP.JUMP,
                context.continue_target,
                node=node,
            )

    # ══════════════════════════════════════════════════════
    # PATCH
    # ══════════════════════════════════════════════════════

    def _patch_context_jumps(
        self,
        context: LoopContext,
    ) -> None:
        """Patcht alle break/continue-Jumps eines Loops."""

        if context.break_target is None:
            raise ControlFlowError(
                "Loop break target was not resolved"
            )

        for jump in context.break_jumps:
            self.patch(
                jump,
                context.break_target,
            )

        if context.continue_target is None:
            raise ControlFlowError(
                "Loop continue target was not resolved"
            )

        for jump in context.continue_jumps:
            self.patch(
                jump,
                context.continue_target,
            )

        context.break_jumps.clear()
        context.continue_jumps.clear()

    # ══════════════════════════════════════════════════════
    # DISPATCH
    # ══════════════════════════════════════════════════════

    def compile(
        self,
        node: Any,
        scope: Any,
        *,
        preserve_result: bool = False,
    ) -> bool:
        """
        Allgemeiner Dispatcher.

        Returns:
            True  → Node wurde verarbeitet
            False → Node ist kein Control-Flow-Node
        """

        if isinstance(node, IfStatement):
            self.compile_if(
                node,
                scope,
                preserve_result=preserve_result,
            )
            return True

        if isinstance(node, WhileStatement):
            self.compile_while(
                node,
                scope,
            )
            return True

        if isinstance(node, ForStatement):
            self.compile_for(
                node,
                scope,
            )
            return True

        if isinstance(node, BreakStatement):
            self.compile_break(node)
            return True

        if isinstance(node, ContinueStatement):
            self.compile_continue(node)
            return True

        return False

    # ══════════════════════════════════════════════════════
    # DEBUG / INTROSPECTION
    # ══════════════════════════════════════════════════════

    @property
    def loop_depth(self) -> int:
        """Aktuelle Verschachtelungstiefe der Loops."""

        return len(self._loops)

    @property
    def in_loop(self) -> bool:
        """True, wenn aktuell innerhalb eines Loops kompiliert wird."""

        return bool(self._loops)

    def current_loop(self) -> Optional[LoopContext]:
        """Gibt den innersten Loop-Kontext zurück."""

        if not self._loops:
            return None

        return self._loops[-1]


__all__ = [
    "ControlFlowError",
    "LoopContext",
    "IfContext",
    "ControlFlowCompiler",
]