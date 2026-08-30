# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — AST → ATC Bytecode

Version: 0.3.0
ATCLang-first compiler pipeline.

Source
  ↓
Lexer
  ↓
Parser
  ↓
AST
  ↓
Compiler
  ↓
ATC Bytecode
  ↓
ATC VM

Der Compiler ist vollständig eigenständig und verwendet weder LLVM
noch GCC als Codegenerator.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from atclang.parser.ast_nodes import *
from atclang.vm.atcvm import Instruction, OP


# ══════════════════════════════════════════════════════════
# BYTECODE FORMAT
# ══════════════════════════════════════════════════════════

MAGIC = b"ATCB"
VERSION = b"\x01\x00"


# ══════════════════════════════════════════════════════════
# COMPILED MODULE
# ══════════════════════════════════════════════════════════

@dataclass
class CompiledModule:
    """
    Ergebnis einer ATCLang-Kompilierung.

    instructions:
        Top-Level/Main Bytecode.

    constants:
        Constant Pool des Moduls.

    functions:
        Kompilierte Funktionen.

    exports:
        Öffentlich exportierte Funktionen.

    function_params:
        Parameter-Metadaten pro Funktion.

    source_map:
        Source-Mapping für Main-Bytecode.

    function_source_maps:
        Source-Mapping für einzelne Funktionen.
    """

    name: str
    instructions: List[Instruction]
    constants: List[object]
    functions: Dict[str, List[Instruction]]

    exports: List[str] = field(default_factory=list)

    function_params: Dict[str, List[str]] = field(
        default_factory=dict
    )

    source_map: List[Tuple[int, int, int]] = field(
        default_factory=list
    )

    function_source_maps: Dict[str, List[Tuple[int, int, int]]] = field(
        default_factory=dict
    )

    def summary(self) -> str:
        return (
            f"Module '{self.name}' | "
            f"{len(self.instructions)} Instrs | "
            f"{len(self.functions)} Fns | "
            f"{len(self.constants)} Konstanten | "
            f"{len(self.exports)} Exports"
        )


# ══════════════════════════════════════════════════════════
# SYMBOL TABLE
# ══════════════════════════════════════════════════════════

@dataclass
class Symbol:
    name: str
    kind: str
    index: int
    typ: str = ""


class SymbolTable:
    """
    Lexikalische Symboltabelle mit Parent-Scope-Unterstützung.
    """

    def __init__(self, parent: Optional["SymbolTable"] = None):
        self.symbols: Dict[str, Symbol] = {}
        self.parent = parent
        self._next = 0

    def define(
        self,
        name: str,
        kind: str,
        typ: str = "",
    ) -> Symbol:
        symbol = Symbol(
            name=name,
            kind=kind,
            index=self._next,
            typ=typ,
        )

        self.symbols[name] = symbol
        self._next += 1

        return symbol

    def resolve(self, name: str) -> Optional[Symbol]:
        symbol = self.symbols.get(name)

        if symbol is not None:
            return symbol

        if self.parent is not None:
            return self.parent.resolve(name)

        return None

    def child(self) -> "SymbolTable":
        return SymbolTable(parent=self)


# ══════════════════════════════════════════════════════════
# LOOP CONTEXT
# ══════════════════════════════════════════════════════════

@dataclass
class LoopContext:
    """
    Kontrollflussinformationen einer einzelnen Schleife.

    break_positions:
        Alle noch nicht gepatchten break-Jumps.

    continue_target:
        Zieladresse für continue.
    """

    break_positions: List[int] = field(default_factory=list)
    continue_target: int = 0


# ══════════════════════════════════════════════════════════
# COMPILER
# ══════════════════════════════════════════════════════════

class ATCCompiler:
    """
    Kompiliert ATCLang AST → ATC Bytecode.

    Der Compiler erzeugt direkt ATC-VM-Instruktionen.
    """

    def __init__(self):
        # Main bytecode
        self.instructions: List[Instruction] = []

        # Module constant pool
        self.constants: List[object] = []

        # Functions
        self.functions: Dict[str, List[Instruction]] = {}

        self.function_params: Dict[str, List[str]] = {}

        # Public exports
        self.exports: List[str] = []

        # Main source map
        self.source_map: List[Tuple[int, int, int]] = []

        # Function source maps
        self.function_source_maps: Dict[
            str,
            List[Tuple[int, int, int]]
        ] = {}

        # Global symbols
        self.globals = SymbolTable()

        # Loop contexts
        self._loop_stack: List[LoopContext] = []

    # ══════════════════════════════════════════════════════
    # ERROR HANDLING
    # ══════════════════════════════════════════════════════

    def error(
        self,
        msg: str,
        node: Optional[ASTNode] = None,
    ):
        location = ""

        if node is not None and hasattr(node, "line"):
            location = f" @ Zeile {node.line}"

        raise CompileError(
            f"[ATCCompiler]{location}: {msg}"
        )

    # ══════════════════════════════════════════════════════
    # BYTECODE EMISSION
    # ══════════════════════════════════════════════════════

    def emit(
        self,
        op: OP,
        *args,
        line: int = 0,
        col: int = 0,
    ) -> int:

        index = len(self.instructions)

        self.instructions.append(
            Instruction(op, list(args))
        )

        self.source_map.append(
            (index, line, col)
        )

        return index

    def patch(
        self,
        index: int,
        *args,
    ):
        if index < 0 or index >= len(self.instructions):
            raise CompileError(
                f"[ATCCompiler]: Invalid patch index {index}"
            )

        self.instructions[index].args = list(args)

    def current_pos(self) -> int:
        return len(self.instructions)

    # ══════════════════════════════════════════════════════
    # CONSTANT POOL
    # ══════════════════════════════════════════════════════

    def add_constant(self, value: object) -> int:
        """
        Fügt einen Wert deterministisch zum Constant Pool hinzu.
        """

        try:
            return self.constants.index(value)
        except ValueError:
            index = len(self.constants)
            self.constants.append(value)
            return index

    # ══════════════════════════════════════════════════════
    # LOOP MANAGEMENT
    # ══════════════════════════════════════════════════════

    def push_loop(self, continue_target: int) -> LoopContext:
        context = LoopContext(
            continue_target=continue_target
        )

        self._loop_stack.append(context)

        return context

    def pop_loop(self, end_position: int):
        if not self._loop_stack:
            raise CompileError(
                "[ATCCompiler]: Internal loop stack underflow"
            )

        context = self._loop_stack.pop()

        for break_position in context.break_positions:
            self.patch(
                break_position,
                end_position,
            )

    def current_loop(self) -> Optional[LoopContext]:
        if not self._loop_stack:
            return None

        return self._loop_stack[-1]

    # ══════════════════════════════════════════════════════
    # EXPRESSION COMPILER
    # ══════════════════════════════════════════════════════

    def compile_expr(
        self,
        node: ASTNode,
        scope: SymbolTable,
    ):

        # ──────────────────────────────────────────────────
        # Literals
        # ──────────────────────────────────────────────────

        if isinstance(node, IntLiteral):
            self.emit(
                OP.PUSH,
                node.value,
                line=node.line,
            )

        elif isinstance(node, FloatLiteral):
            self.emit(
                OP.PUSH,
                node.value,
                line=node.line,
            )

        elif isinstance(node, StringLiteral):
            self.emit(
                OP.PUSH,
                node.value,
                line=node.line,
            )

        elif isinstance(node, BoolLiteral):
            self.emit(
                OP.PUSH,
                node.value,
                line=node.line,
            )

        elif isinstance(node, NullLiteral):
            self.emit(
                OP.PUSH,
                None,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Identifier
        # ──────────────────────────────────────────────────

        elif isinstance(node, Identifier):

            # Symbol resolution currently remains metadata-level.
            # ATC VM uses symbolic LOAD names.
            self.emit(
                OP.LOAD,
                node.name,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Namespace Access
        # ──────────────────────────────────────────────────

        elif isinstance(node, NamespaceAccess):

            name = "::".join(node.parts)

            self.emit(
                OP.PUSH,
                name,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Binary Operations
        # ──────────────────────────────────────────────────

        elif isinstance(node, BinaryOp):

            self.compile_expr(
                node.left,
                scope,
            )

            self.compile_expr(
                node.right,
                scope,
            )

            op_map = {
                "+": OP.ADD,
                "-": OP.SUB,
                "*": OP.MUL,
                "/": OP.DIV,
                "%": OP.MOD,
                "**": OP.POW,

                "==": OP.EQ,
                "!=": OP.NEQ,

                "<": OP.LT,
                ">": OP.GT,
                "<=": OP.LTE,
                ">=": OP.GTE,

                "&&": OP.AND,
                "and": OP.AND,

                "||": OP.OR,
                "or": OP.OR,

                "&": OP.BITAND,
                "|": OP.BITOR,
                "^": OP.BITXOR,

                "<<": OP.SHL,
                ">>": OP.SHR,
            }

            operation = op_map.get(node.op)

            if operation is None:
                self.error(
                    f"Unbekannter Operator: '{node.op}'",
                    node,
                )

            self.emit(
                operation,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Unary Operations
        # ──────────────────────────────────────────────────

        elif isinstance(node, UnaryOp):

            self.compile_expr(
                node.operand,
                scope,
            )

            if node.op == "-":
                self.emit(
                    OP.NEG,
                    line=node.line,
                )

            elif node.op == "!":
                self.emit(
                    OP.NOT,
                    line=node.line,
                )

            else:
                self.error(
                    f"Unbekannter Unary-Operator: '{node.op}'",
                    node,
                )

        # ──────────────────────────────────────────────────
        # Index Access
        # ──────────────────────────────────────────────────

        elif isinstance(node, IndexAccess):

            self.compile_expr(
                node.target,
                scope,
            )

            self.compile_expr(
                node.index,
                scope,
            )

            self.emit(
                OP.LOAD_IDX,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Dot Access
        # ──────────────────────────────────────────────────

        elif isinstance(node, DotAccess):

            self.compile_expr(
                node.target,
                scope,
            )

            self.emit(
                OP.GET_FIELD,
                node.field_name,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Function Call
        # ──────────────────────────────────────────────────

        elif isinstance(node, FunctionCall):

            for arg in node.args:
                self.compile_expr(
                    arg,
                    scope,
                )

            if isinstance(node.target, Identifier):

                function_name = node.target.name

                if function_name == "print":

                    self.emit(
                        OP.PRINT,
                        line=node.line,
                    )

                else:

                    self.emit(
                        OP.CALL,
                        function_name,
                        len(node.args),
                        line=node.line,
                    )

            elif isinstance(node.target, NamespaceAccess):

                function_name = "::".join(
                    node.target.parts
                )

                self.emit(
                    OP.CALL_EXT,
                    function_name,
                    len(node.args),
                    line=node.line,
                )

            elif isinstance(node.target, DotAccess):

                self.compile_expr(
                    node.target.target,
                    scope,
                )

                self.emit(
                    OP.CALL,
                    node.target.field_name,
                    len(node.args) + 1,
                    line=node.line,
                )

            else:

                self.compile_expr(
                    node.target,
                    scope,
                )

                self.emit(
                    OP.CALL,
                    "__dynamic__",
                    len(node.args),
                    line=node.line,
                )

        # ──────────────────────────────────────────────────
        # Assignment
        # ──────────────────────────────────────────────────

        elif isinstance(node, Assignment):

            self.compile_expr(
                node.value,
                scope,
            )

            if isinstance(node.target, Identifier):

                self.emit(
                    OP.STORE,
                    node.target.name,
                    line=node.line,
                )

            elif isinstance(node.target, IndexAccess):

                self.compile_expr(
                    node.target.target,
                    scope,
                )

                self.compile_expr(
                    node.target.index,
                    scope,
                )

                self.emit(
                    OP.STORE_IDX,
                    line=node.line,
                )

            elif isinstance(node.target, DotAccess):

                self.compile_expr(
                    node.target.target,
                    scope,
                )

                self.emit(
                    OP.SET_FIELD,
                    node.target.field_name,
                    line=node.line,
                )

            else:

                self.error(
                    "Ungültiges Assignment-Ziel",
                    node,
                )

        # ──────────────────────────────────────────────────
        # List
        # ──────────────────────────────────────────────────

        elif isinstance(node, ListLiteral):

            for element in node.elements:
                self.compile_expr(
                    element,
                    scope,
                )

            self.emit(
                OP.NEW_LIST,
                len(node.elements),
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Map
        # ──────────────────────────────────────────────────

        elif isinstance(node, MapLiteral):

            for pair in node.pairs:

                if isinstance(pair, tuple) and len(pair) >= 2:
                    key = pair[0]
                    value = pair[1]

                elif isinstance(pair, dict):
                    key = pair.get("key")
                    value = pair.get("value")

                else:
                    key = pair
                    value = None

                self.compile_expr(
                    value,
                    scope,
                )

                self.compile_expr(
                    key,
                    scope,
                )

            self.emit(
                OP.NEW_MAP,
                len(node.pairs),
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Struct
        # ──────────────────────────────────────────────────

        elif isinstance(node, StructLiteral):

            for field_name, field_value in node.fields:

                self.compile_expr(
                    field_value,
                    scope,
                )

            self.emit(
                OP.NEW_OBJ,
                node.struct_name or "struct",
                len(node.fields),
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Ternary
        # ──────────────────────────────────────────────────

        elif isinstance(node, TernaryExpr):

            self.compile_expr(
                node.cond,
                scope,
            )

            jump_else = self.emit(
                OP.JUMP_NOT,
                0,
                line=node.line,
            )

            self.compile_expr(
                node.then_expr,
                scope,
            )

            jump_end = self.emit(
                OP.JUMP,
                0,
                line=node.line,
            )

            else_position = self.current_pos()

            self.patch(
                jump_else,
                else_position,
            )

            self.compile_expr(
                node.else_expr,
                scope,
            )

            end_position = self.current_pos()

            self.patch(
                jump_end,
                end_position,
            )

        # ──────────────────────────────────────────────────
        # Cast
        # ──────────────────────────────────────────────────

        elif isinstance(node, CastExpr):

            value = (
                node.value
                if hasattr(node, "value")
                else node.operand
            )

            target_type = (
                node.target_type
                if hasattr(node, "target_type")
                else "Any"
            )

            self.compile_expr(
                value,
                scope,
            )

            self.emit(
                OP.CAST,
                target_type,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Tuple
        # ──────────────────────────────────────────────────

        elif isinstance(node, TupleExpr):

            for element in node.elements:
                self.compile_expr(
                    element,
                    scope,
                )

            # Current VM representation:
            # Tuple → list-compatible aggregate.
            self.emit(
                OP.NEW_LIST,
                len(node.elements),
                line=node.line,
            )

        else:

            self.error(
                f"Unbekannter Ausdruck-Typ: "
                f"{type(node).__name__}",
                node,
            )

    # ══════════════════════════════════════════════════════
    # STATEMENT COMPILER
    # ══════════════════════════════════════════════════════

    def compile_stmt(
        self,
        node: ASTNode,
        scope: SymbolTable,
    ):

        # ──────────────────────────────────────────────────
        # Let
        # ──────────────────────────────────────────────────

        if isinstance(node, LetStatement):

            if node.value is not None:
                self.compile_expr(
                    node.value,
                    scope,
                )
            else:
                self.emit(
                    OP.PUSH,
                    None,
                    line=node.line,
                )

            self.emit(
                OP.STORE,
                node.name,
                line=node.line,
            )

            type_name = ""

            if node.type_hint:
                type_name = str(
                    node.type_hint.name
                )

            scope.define(
                node.name,
                "local",
                type_name,
            )

        # ──────────────────────────────────────────────────
        # Return
        # ──────────────────────────────────────────────────

        elif isinstance(node, ReturnStatement):

            if node.value is not None:
                self.compile_expr(
                    node.value,
                    scope,
                )
            else:
                self.emit(
                    OP.PUSH,
                    None,
                    line=node.line,
                )

            self.emit(
                OP.RETURN,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Emit
        # ──────────────────────────────────────────────────

        elif isinstance(node, EmitStatement):

            for arg in node.args:
                self.compile_expr(
                    arg,
                    scope,
                )

            self.emit(
                OP.EMIT,
                node.event,
                len(node.args),
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Require
        # ──────────────────────────────────────────────────

        elif isinstance(node, RequireStatement):

            self.compile_expr(
                node.condition,
                scope,
            )

            message = ""

            if (
                node.message
                and isinstance(node.message, StringLiteral)
            ):
                message = node.message.value

            self.emit(
                OP.REQUIRE,
                message,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # If
        # ──────────────────────────────────────────────────

        elif isinstance(node, IfStatement):

            self.compile_expr(
                node.condition,
                scope,
            )

            jump_if_false = self.emit(
                OP.JUMP_NOT,
                0,
                line=node.line,
            )

            child_scope = scope.child()

            for statement in node.then_block:
                self.compile_stmt(
                    statement,
                    child_scope,
                )

            end_jumps: List[int] = []

            if node.else_block or node.elif_blocks:

                end_jumps.append(
                    self.emit(
                        OP.JUMP,
                        0,
                        line=node.line,
                    )
                )

            self.patch(
                jump_if_false,
                self.current_pos(),
            )

            for elif_condition, elif_body in node.elif_blocks:

                self.compile_expr(
                    elif_condition,
                    scope,
                )

                elif_false = self.emit(
                    OP.JUMP_NOT,
                    0,
                    line=node.line,
                )

                elif_scope = scope.child()

                for statement in elif_body:
                    self.compile_stmt(
                        statement,
                        elif_scope,
                    )

                end_jumps.append(
                    self.emit(
                        OP.JUMP,
                        0,
                        line=node.line,
                    )
                )

                self.patch(
                    elif_false,
                    self.current_pos(),
                )

            if node.else_block:

                else_scope = scope.child()

                for statement in node.else_block:
                    self.compile_stmt(
                        statement,
                        else_scope,
                    )

            end_position = self.current_pos()

            for jump in end_jumps:
                self.patch(
                    jump,
                    end_position,
                )

        # ──────────────────────────────────────────────────
        # While
        # ──────────────────────────────────────────────────

        elif isinstance(node, WhileStatement):

            loop_start = self.current_pos()

            self.compile_expr(
                node.condition,
                scope,
            )

            jump_out = self.emit(
                OP.JUMP_NOT,
                0,
                line=node.line,
            )

            loop = self.push_loop(
                continue_target=loop_start
            )

            body_scope = scope.child()

            for statement in node.body:
                self.compile_stmt(
                    statement,
                    body_scope,
                )

            self.emit(
                OP.JUMP,
                loop_start,
                line=node.line,
            )

            end_position = self.current_pos()

            self.patch(
                jump_out,
                end_position,
            )

            self.pop_loop(
                end_position
            )

        # ──────────────────────────────────────────────────
        # For
        # ──────────────────────────────────────────────────

        elif isinstance(node, ForStatement):

            # iter = iterable
            self.compile_expr(
                node.iterable,
                scope,
            )

            iterator_name = (
                f"__iter_{node.var}__"
            )

            index_name = (
                f"__i_{node.var}__"
            )

            self.emit(
                OP.STORE,
                iterator_name,
                line=node.line,
            )

            # i = 0
            self.emit(
                OP.PUSH,
                0,
                line=node.line,
            )

            self.emit(
                OP.STORE,
                index_name,
                line=node.line,
            )

            loop_start = self.current_pos()

            # i
            self.emit(
                OP.LOAD,
                index_name,
                line=node.line,
            )

            # len(iter)
            self.emit(
                OP.LOAD,
                iterator_name,
                line=node.line,
            )

            self.emit(
                OP.CALL_EXT,
                "ATC::Std::len",
                1,
                line=node.line,
            )

            self.emit(
                OP.LT,
                line=node.line,
            )

            jump_out = self.emit(
                OP.JUMP_NOT,
                0,
                line=node.line,
            )

            # x = iter[i]
            self.emit(
                OP.LOAD,
                iterator_name,
                line=node.line,
            )

            self.emit(
                OP.LOAD,
                index_name,
                line=node.line,
            )

            self.emit(
                OP.LOAD_IDX,
                line=node.line,
            )

            self.emit(
                OP.STORE,
                node.var,
                line=node.line,
            )

            body_scope = scope.child()

            body_scope.define(
                node.var,
                "local",
            )

            # Continue must jump to increment,
            # NOT loop_start.
            #
            # This is critical:
            #
            # for x in list {
            #     if (...) {
            #         continue
            #     }
            # }
            #
            # must execute i += 1.
            increment_position = None

            # Temporary loop context.
            loop = self.push_loop(
                continue_target=0
            )

            for statement in node.body:
                self.compile_stmt(
                    statement,
                    body_scope,
                )

            # Continue target.
            increment_position = self.current_pos()
            loop.continue_target = increment_position

            # i += 1
            self.emit(
                OP.LOAD,
                index_name,
                line=node.line,
            )

            self.emit(
                OP.PUSH,
                1,
                line=node.line,
            )

            self.emit(
                OP.ADD,
                line=node.line,
            )

            self.emit(
                OP.STORE,
                index_name,
                line=node.line,
            )

            self.emit(
                OP.JUMP,
                loop_start,
                line=node.line,
            )

            end_position = self.current_pos()

            self.patch(
                jump_out,
                end_position,
            )

            self.pop_loop(
                end_position
            )

        # ──────────────────────────────────────────────────
        # Break
        # ──────────────────────────────────────────────────

        elif isinstance(node, BreakStatement):

            loop = self.current_loop()

            if loop is None:
                self.error(
                    "break außerhalb einer Schleife",
                    node,
                )

            jump = self.emit(
                OP.JUMP,
                0,
                line=node.line,
            )

            loop.break_positions.append(
                jump
            )

        # ──────────────────────────────────────────────────
        # Continue
        # ──────────────────────────────────────────────────

        elif isinstance(node, ContinueStatement):

            loop = self.current_loop()

            if loop is None:
                self.error(
                    "continue außerhalb einer Schleife",
                    node,
                )

            # For-loops initially set this to 0,
            # but the value is resolved before loop
            # compilation finishes.
            self.emit(
                OP.JUMP,
                loop.continue_target,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Expression Statement
        # ──────────────────────────────────────────────────

        elif isinstance(node, ExprStatement):

            self.compile_expr(
                node.expr,
                scope,
            )

            self.emit(
                OP.POP,
                line=node.line,
            )

        # ──────────────────────────────────────────────────
        # Assignment Statement
        # ──────────────────────────────────────────────────

        elif isinstance(node, Assignment):

            self.compile_expr(
                node,
                scope,
            )

        # ──────────────────────────────────────────────────
        # State Field
        # ──────────────────────────────────────────────────

        elif isinstance(node, StateField):

            # State declarations are represented as
            # contract metadata and initialized by
            # compile_contract().
            pass

        else:

            self.error(
                f"Unbekanntes Statement: "
                f"{type(node).__name__}",
                node,
            )

    # ══════════════════════════════════════════════════════
    # TOP LEVEL IF
    # ══════════════════════════════════════════════════════

    def compile_if_toplevel(
        self,
        node: IfStatement,
        scope: SymbolTable,
    ):

        self.compile_expr(
            node.condition,
            scope,
        )

        jump_if_false = self.emit(
            OP.JUMP_NOT,
            0,
            line=node.line,
        )

        then_scope = scope.child()

        for statement in node.then_block:

            if isinstance(statement, ExprStatement):
                self.compile_expr(
                    statement.expr,
                    then_scope,
                )
            else:
                self.compile_stmt(
                    statement,
                    then_scope,
                )

        end_jumps: List[int] = []

        if node.else_block or node.elif_blocks:

            end_jumps.append(
                self.emit(
                    OP.JUMP,
                    0,
                    line=node.line,
                )
            )

        self.patch(
            jump_if_false,
            self.current_pos(),
        )

        for elif_condition, elif_body in node.elif_blocks:

            self.compile_expr(
                elif_condition,
                scope,
            )

            elif_false = self.emit(
                OP.JUMP_NOT,
                0,
                line=node.line,
            )

            elif_scope = scope.child()

            for statement in elif_body:

                if isinstance(statement, ExprStatement):
                    self.compile_expr(
                        statement.expr,
                        elif_scope,
                    )
                else:
                    self.compile_stmt(
                        statement,
                        elif_scope,
                    )

            end_jumps.append(
                self.emit(
                    OP.JUMP,
                    0,
                    line=node.line,
                )
            )

            self.patch(
                elif_false,
                self.current_pos(),
            )

        if node.else_block:

            else_scope = scope.child()

            for statement in node.else_block:

                if isinstance(statement, ExprStatement):
                    self.compile_expr(
                        statement.expr,
                        else_scope,
                    )
                else:
                    self.compile_stmt(
                        statement,
                        else_scope,
                    )

        end_position = self.current_pos()

        for jump in end_jumps:
            self.patch(
                jump,
                end_position,
            )

    # ══════════════════════════════════════════════════════
    # FUNCTION COMPILATION
    # ══════════════════════════════════════════════════════

    def compile_function(
        self,
        fn: FunctionDef,
        function_name: Optional[str] = None,
    ) -> List[Instruction]:

        saved_instructions = self.instructions
        saved_source_map = self.source_map

        self.instructions = []
        self.source_map = []

        scope = self.globals.child()

        for parameter in fn.params:

            type_name = ""

            if parameter.type_hint:
                type_name = parameter.type_hint.name

            scope.define(
                parameter.name,
                "local",
                type_name,
            )

        for statement in fn.body:
            self.compile_stmt(
                statement,
                scope,
            )

        # Implicit return None
        if (
            not self.instructions
            or self.instructions[-1].op != OP.RETURN
        ):

            self.emit(
                OP.PUSH,
                None,
            )

            self.emit(
                OP.RETURN,
            )

        function_instructions = self.instructions

        actual_name = (
            function_name
            if function_name is not None
            else fn.name
        )

        self.function_source_maps[
            actual_name
        ] = list(self.source_map)

        # Restore main compiler state.
        self.instructions = saved_instructions
        self.source_map = saved_source_map

        self.function_params[
            actual_name
        ] = [
            parameter.name
            for parameter in fn.params
        ]

        return function_instructions

    # ══════════════════════════════════════════════════════
    # CONTRACT COMPILATION
    # ══════════════════════════════════════════════════════

    def compile_contract(
        self,
        contract: ContractDef,
    ):

        # ──────────────────────────────────────────────────
        # State fields
        # ──────────────────────────────────────────────────

        for state in contract.states:

            type_name = ""

            if state.type_hint:
                type_name = state.type_hint.name

            if "Map" in type_name:

                self.emit(
                    OP.NEW_MAP,
                    line=getattr(state, "line", 0),
                )

            else:

                self.emit(
                    OP.PUSH,
                    None,
                    line=getattr(state, "line", 0),
                )

            state_name = (
                f"{contract.name}.{state.name}"
            )

            self.emit(
                OP.STORE,
                state_name,
                line=getattr(state, "line", 0),
            )

            self.globals.define(
                state_name,
                "state",
                type_name,
            )

        # ──────────────────────────────────────────────────
        # Contract functions
        # ──────────────────────────────────────────────────

        for fn in contract.functions:

            function_name = (
                f"{contract.name}.{fn.name}"
            )

            instructions = self.compile_function(
                fn,
                function_name=function_name,
            )

            self.functions[
                function_name
            ] = instructions

            self.exports.append(
                function_name
            )

    # ══════════════════════════════════════════════════════
    # PROGRAM COMPILATION
    # ══════════════════════════════════════════════════════

    def compile_program(
        self,
        program: Program,
    ) -> CompiledModule:

        scope = self.globals

        statements = program.statements
        last_index = len(statements) - 1

        for index, node in enumerate(statements):

            is_last = index == last_index

            # ──────────────────────────────────────────────
            # Contract
            # ──────────────────────────────────────────────

            if isinstance(node, ContractDef):

                self.compile_contract(
                    node
                )

            # ──────────────────────────────────────────────
            # Function
            # ──────────────────────────────────────────────

            elif isinstance(node, FunctionDef):

                instructions = self.compile_function(
                    node
                )

                self.functions[
                    node.name
                ] = instructions

                if node.is_pub:
                    self.exports.append(
                        node.name
                    )

            # ──────────────────────────────────────────────
            # Wallet
            # ──────────────────────────────────────────────

            elif isinstance(node, WalletDef):

                self.compile_expr(
                    node.value,
                    scope,
                )

                self.emit(
                    OP.STORE,
                    node.name,
                    line=node.line,
                )

                scope.define(
                    node.name,
                    "global",
                    "ATCWallet",
                )

            # ──────────────────────────────────────────────
            # Let
            # ──────────────────────────────────────────────

            elif isinstance(node, LetStatement):

                self.compile_stmt(
                    node,
                    scope,
                )

            # ──────────────────────────────────────────────
            # Import
            # ──────────────────────────────────────────────

            elif isinstance(node, ImportStatement):

                path = "::".join(
                    node.path
                )

                self.emit(
                    OP.CALL_EXT,
                    f"ATC::Import::{path}",
                    0,
                    line=getattr(node, "line", 0),
                )

                if node.alias:

                    self.emit(
                        OP.STORE,
                        node.alias,
                        line=getattr(node, "line", 0),
                    )

            # ──────────────────────────────────────────────
            # Enum
            # ──────────────────────────────────────────────

            elif isinstance(node, EnumDef):

                variants = {}

                for enum_index, variant in enumerate(
                    node.variants
                ):

                    variants[variant] = enum_index

                    self.emit(
                        OP.PUSH,
                        enum_index,
                        line=getattr(node, "line", 0),
                    )

                    self.emit(
                        OP.STORE,
                        f"{node.name}::{variant}",
                        line=getattr(node, "line", 0),
                    )

                self.emit(
                    OP.PUSH,
                    variants,
                    line=getattr(node, "line", 0),
                )

                self.emit(
                    OP.STORE,
                    node.name,
                    line=getattr(node, "line", 0),
                )

            # ──────────────────────────────────────────────
            # Struct
            # ──────────────────────────────────────────────

            elif isinstance(node, StructDef):

                # Struct definitions are currently runtime
                # metadata. No executable bytecode required.
                pass

            # ──────────────────────────────────────────────
            # Class / Storage / TypeAlias
            # ──────────────────────────────────────────────

            elif isinstance(
                node,
                (
                    ClassDef,
                    StorageBlock,
                    TypeAliasDef,
                ),
            ):

                # Runtime/type-system metadata.
                pass

            # ──────────────────────────────────────────────
            # Last expression
            # ──────────────────────────────────────────────

            elif (
                is_last
                and isinstance(node, ExprStatement)
            ):

                self.compile_expr(
                    node.expr,
                    scope,
                )

                self.emit(
                    OP.RETURN,
                    line=node.line,
                )

            # ──────────────────────────────────────────────
            # Last top-level if
            # ──────────────────────────────────────────────

            elif (
                is_last
                and isinstance(node, IfStatement)
            ):

                self.compile_if_toplevel(
                    node,
                    scope,
                )

            # ──────────────────────────────────────────────
            # Everything else
            # ──────────────────────────────────────────────

            else:

                self.compile_stmt(
                    node,
                    scope,
                )

        # ──────────────────────────────────────────────────
        # Final HALT
        # ──────────────────────────────────────────────────

        if (
            not self.instructions
            or self.instructions[-1].op != OP.RETURN
        ):

            self.emit(
                OP.HALT
            )

        return CompiledModule(
            name="main",
            instructions=self.instructions,
            constants=self.constants,
            functions=self.functions,
            function_params=self.function_params,
            exports=self.exports,
            source_map=self.source_map,
            function_source_maps=self.function_source_maps,
        )


# ══════════════════════════════════════════════════════════
# COMPILE ERROR
# ══════════════════════════════════════════════════════════

class CompileError(Exception):
    """ATCLang compiler error."""
    pass


# ══════════════════════════════════════════════════════════
# PUBLIC COMPILE API
# ══════════════════════════════════════════════════════════

def compile_source(
    source: str,
) -> CompiledModule:
    """
    ATCLang Source → AST → ATC Bytecode.
    """

    from atclang.parser.parser import parse

    ast = parse(source)

    compiler = ATCCompiler()

    return compiler.compile_program(
        ast
    )


# ══════════════════════════════════════════════════════════
# DISASSEMBLER
# ══════════════════════════════════════════════════════════

def disassemble(
    module: CompiledModule,
) -> str:
    """
    Gibt ATC Bytecode menschenlesbar aus.
    """

    lines = [
        f"=== ATC Bytecode: {module.name} ===",
        (
            f"Instrs: {len(module.instructions)} | "
            f"Fns: {len(module.functions)} | "
            f"Constants: {len(module.constants)} | "
            f"Exports: {module.exports}"
        ),
        "",
        "[MAIN]",
    ]

    for index, instruction in enumerate(
        module.instructions
    ):

        args = (
            " ".join(
                repr(argument)
                for argument in instruction.args
            )
            if instruction.args
            else ""
        )

        lines.append(
            f"  {index:04d}  "
            f"{instruction.op.name:<12} "
            f"{args}"
        )

    for function_name, function_instructions in (
        module.functions.items()
    ):

        lines.append(
            f"\n[FN: {function_name}]"
        )

        for index, instruction in enumerate(
            function_instructions
        ):

            args = (
                " ".join(
                    repr(argument)
                    for argument in instruction.args
                )
                if instruction.args
                else ""
            )

            lines.append(
                f"  {index:04d}  "
                f"{instruction.op.name:<12} "
                f"{args}"
            )

    return "\n".join(lines)