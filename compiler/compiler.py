"atclang/compiler/compiler.py"

# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler
================

ATCLang AST -> ATC Bytecode compiler.

Pipeline:

    Source
      |
    Lexer
      |
    Parser
      |
    AST
      |
    TypeChecker
      |
    Compiler
      |
    ATC Bytecode
      |
    ATC VM

This module contains the compiler/code-generator only.

Responsibilities
----------------
* AST -> ATC bytecode
* symbol management
* function compilation
* contract compilation
* branch/loop lowering
* source-map generation
* module metadata generation

Non-responsibilities
--------------------
* lexing
* parsing
* type checking
* optimization
* VM execution
* runtime object management

ATC-92 | ATCLang Compiler
Version: 0.3.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from atclang.parser.ast_nodes import (
    ASTNode,
    Assignment,
    BinaryOp,
    BoolLiteral,
    BreakStatement,
    CastExpr,
    ClassDef,
    ContinueStatement,
    ContractDef,
    DotAccess,
    EnumDef,
    ExprStatement,
    FloatLiteral,
    ForStatement,
    FunctionCall,
    FunctionDef,
    Identifier,
    IfStatement,
    ImportStatement,
    IndexAccess,
    IntLiteral,
    LetStatement,
    ListLiteral,
    MapLiteral,
    NamespaceAccess,
    NullLiteral,
    Parameter,
    Program,
    RequireStatement,
    ReturnStatement,
    StateField,
    StorageBlock,
    StringLiteral,
    StructDef,
    StructLiteral,
    TernaryExpr,
    TupleExpr,
    TypeAliasDef,
    UnaryOp,
    WalletDef,
    WhileStatement,
    EmitStatement,
)

from atclang.vm.atcvm import Instruction, OP


# ============================================================================
# BYTECODE FORMAT
# ============================================================================

ATCB_MAGIC = b"ATCB"
ATCB_VERSION_MAJOR = 1
ATCB_VERSION_MINOR = 0
ATCB_VERSION = bytes(
    [ATCB_VERSION_MAJOR, ATCB_VERSION_MINOR]
)


# ============================================================================
# ERRORS
# ============================================================================

class CompileError(Exception):
    """Raised when AST compilation fails."""

    def __init__(
        self,
        message: str,
        *,
        line: Optional[int] = None,
        col: Optional[int] = None,
    ) -> None:
        self.message = message
        self.line = line
        self.col = col

        location = ""

        if line is not None:
            location = f" @ {line}"
            if col is not None:
                location += f":{col}"

        super().__init__(f"[ATCCompiler]{location}: {message}")


# ============================================================================
# SOURCE MAP
# ============================================================================

@dataclass(frozen=True)
class SourceLocation:
    """Maps bytecode instruction to source location."""

    instruction: int
    line: int
    col: int


# ============================================================================
# SYMBOL SYSTEM
# ============================================================================

@dataclass
class Symbol:
    """
    Compiler symbol.

    kind:
        local
        global
        parameter
        function
        contract
        state
        enum
        enum_variant
        import
    """

    name: str
    kind: str
    index: int
    typ: str = ""


class SymbolTable:
    """Hierarchical compiler symbol table."""

    def __init__(
        self,
        parent: Optional["SymbolTable"] = None,
    ) -> None:
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self._next_index = 0

    def define(
        self,
        name: str,
        kind: str,
        typ: str = "",
    ) -> Symbol:
        if name in self.symbols:
            raise CompileError(
                f"Symbol '{name}' already defined"
            )

        symbol = Symbol(
            name=name,
            kind=kind,
            index=self._next_index,
            typ=typ,
        )

        self.symbols[name] = symbol
        self._next_index += 1

        return symbol

    def define_or_get(
        self,
        name: str,
        kind: str,
        typ: str = "",
    ) -> Symbol:
        existing = self.symbols.get(name)

        if existing is not None:
            return existing

        return self.define(name, kind, typ)

    def resolve(
        self,
        name: str,
    ) -> Optional[Symbol]:
        symbol = self.symbols.get(name)

        if symbol is not None:
            return symbol

        if self.parent is not None:
            return self.parent.resolve(name)

        return None

    def child(self) -> "SymbolTable":
        return SymbolTable(parent=self)

    def contains_local(self, name: str) -> bool:
        return name in self.symbols


# ============================================================================
# COMPILED MODULE
# ============================================================================

@dataclass
class CompiledModule:
    """
    Result of ATCLang compilation.

    The VM consumes the instruction streams and function metadata.
    """

    name: str

    instructions: List[Instruction]

    constants: List[Any]

    functions: Dict[str, List[Instruction]]

    exports: List[str] = field(default_factory=list)

    function_params: Dict[str, List[str]] = field(
        default_factory=dict
    )

    source_map: List[Tuple[int, int, int]] = field(
        default_factory=list
    )

    version: bytes = ATCB_VERSION

    def summary(self) -> str:
        return (
            f"Module '{self.name}' | "
            f"{len(self.instructions)} Instrs | "
            f"{len(self.functions)} Fns | "
            f"{len(self.constants)} Konstanten | "
            f"{len(self.exports)} Exports"
        )


# ============================================================================
# COMPILER
# ============================================================================

class ATCCompiler:
    """
    ATCLang AST -> ATC bytecode compiler.

    The compiler deliberately does not perform optimization.
    Optimization belongs to `atclang.compiler.optimizer`.
    """

    def __init__(
        self,
        *,
        module_name: str = "main",
    ) -> None:
        self.module_name = module_name

        # Current instruction stream.
        self.instructions: List[Instruction] = []

        # Module constant pool.
        self.constants: List[Any] = []

        # Compiled functions.
        self.functions: Dict[str, List[Instruction]] = {}

        # Function parameter metadata.
        self.function_params: Dict[str, List[str]] = {}

        # Public exports.
        self.exports: List[str] = []

        # instruction -> (line, col)
        self.source_map: List[Tuple[int, int, int]] = []

        # Global symbol table.
        self.globals = SymbolTable()

        # Unique compiler-generated names.
        self._temporary_counter = 0

        # Loop control stacks.
        #
        # Every active loop owns one break target list.
        # Every active loop owns one continue target.
        self._break_stack: List[List[int]] = []
        self._continue_stack: List[int] = []

        # Compilation state.
        self._current_function: Optional[str] = None

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def error(
        self,
        message: str,
        node: Optional[ASTNode] = None,
    ) -> None:
        line = getattr(node, "line", None)
        col = getattr(node, "col", None)

        raise CompileError(
            message,
            line=line,
            col=col,
        )

    # ------------------------------------------------------------------
    # Instruction emission
    # ------------------------------------------------------------------

    def emit(
        self,
        op: OP,
        *args: Any,
        line: int = 0,
        col: int = 0,
    ) -> int:
        """
        Emit one instruction.

        Returns the instruction index.
        """

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
        instruction_index: int,
        *args: Any,
    ) -> None:
        """Patch a previously emitted instruction."""

        if not (
            0 <= instruction_index
            < len(self.instructions)
        ):
            raise CompileError(
                f"Invalid patch index: {instruction_index}"
            )

        self.instructions[
            instruction_index
        ].args = list(args)

    def current_pos(self) -> int:
        return len(self.instructions)

    # ------------------------------------------------------------------
    # Constants
    # ------------------------------------------------------------------

    def add_constant(self, value: Any) -> int:
        """
        Add value to module constant pool.

        Returns constant-pool index.
        """

        for index, existing in enumerate(self.constants):
            try:
                if existing == value:
                    return index
            except Exception:
                pass

        self.constants.append(value)
        return len(self.constants) - 1

    # ------------------------------------------------------------------
    # Temporary names
    # ------------------------------------------------------------------

    def new_temp(self, prefix: str = "__tmp") -> str:
        self._temporary_counter += 1
        return f"{prefix}_{self._temporary_counter}"

    # ==================================================================
    # EXPRESSIONS
    # ==================================================================

    def compile_expr(
        self,
        node: ASTNode,
        scope: SymbolTable,
    ) -> None:
        """Compile an expression and leave its result on the VM stack."""

        # --------------------------------------------------------------
        # Literals
        # --------------------------------------------------------------

        if isinstance(node, IntLiteral):
            self.emit(
                OP.PUSH,
                node.value,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        if isinstance(node, FloatLiteral):
            self.emit(
                OP.PUSH,
                node.value,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        if isinstance(node, StringLiteral):
            self.emit(
                OP.PUSH,
                node.value,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        if isinstance(node, BoolLiteral):
            self.emit(
                OP.PUSH,
                node.value,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        if isinstance(node, NullLiteral):
            self.emit(
                OP.PUSH,
                None,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Identifier
        # --------------------------------------------------------------

        if isinstance(node, Identifier):
            symbol = scope.resolve(node.name)

            # LOAD currently addresses names.
            # Symbol indices remain compiler metadata and can later
            # be lowered to indexed locals when the VM ABI supports it.
            self.emit(
                OP.LOAD,
                node.name,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Namespace access
        # --------------------------------------------------------------

        if isinstance(node, NamespaceAccess):
            name = "::".join(node.parts)

            self.emit(
                OP.PUSH,
                name,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Binary operators
        # --------------------------------------------------------------

        if isinstance(node, BinaryOp):
            self.compile_expr(node.left, scope)
            self.compile_expr(node.right, scope)

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

            opcode = op_map.get(node.op)

            if opcode is None:
                self.error(
                    f"Unknown binary operator '{node.op}'",
                    node,
                )

            self.emit(
                opcode,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Unary operators
        # --------------------------------------------------------------

        if isinstance(node, UnaryOp):
            self.compile_expr(node.operand, scope)

            op_map = {
                "-": OP.NEG,
                "!": OP.NOT,
                "~": getattr(OP, "BITNOT", OP.NOT),
            }

            opcode = op_map.get(node.op)

            if opcode is None:
                self.error(
                    f"Unknown unary operator '{node.op}'",
                    node,
                )

            self.emit(
                opcode,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Index access
        # --------------------------------------------------------------

        if isinstance(node, IndexAccess):
            self.compile_expr(node.target, scope)
            self.compile_expr(node.index, scope)

            self.emit(
                OP.LOAD_IDX,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Field access
        # --------------------------------------------------------------

        if isinstance(node, DotAccess):
            self.compile_expr(node.target, scope)

            self.emit(
                OP.GET_FIELD,
                node.field_name,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Function calls
        # --------------------------------------------------------------

        if isinstance(node, FunctionCall):
            self.compile_call(node, scope)
            return

        # --------------------------------------------------------------
        # Assignment expression
        # --------------------------------------------------------------

        if isinstance(node, Assignment):
            self.compile_assignment(node, scope)
            return

        # --------------------------------------------------------------
        # List
        # --------------------------------------------------------------

        if isinstance(node, ListLiteral):
            for element in node.elements:
                self.compile_expr(element, scope)

            self.emit(
                OP.NEW_LIST,
                len(node.elements),
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Tuple
        # --------------------------------------------------------------

        if isinstance(node, TupleExpr):
            for element in node.elements:
                self.compile_expr(element, scope)

            self.emit(
                OP.NEW_LIST,
                len(node.elements),
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Map
        # --------------------------------------------------------------

        if isinstance(node, MapLiteral):
            for pair in node.pairs:
                key = None
                value = None

                if (
                    isinstance(pair, tuple)
                    and len(pair) >= 2
                ):
                    key, value = pair[0], pair[1]

                elif isinstance(pair, dict):
                    key = pair.get("key")
                    value = pair.get("value")

                else:
                    self.error(
                        "Invalid map literal entry",
                        node,
                    )

                self.compile_expr(key, scope)
                self.compile_expr(value, scope)

            self.emit(
                OP.NEW_MAP,
                len(node.pairs),
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Struct
        # --------------------------------------------------------------

        if isinstance(node, StructLiteral):
            for field_name, field_value in node.fields:
                self.compile_expr(field_value, scope)

            self.emit(
                OP.NEW_OBJ,
                node.struct_name or "struct",
                len(node.fields),
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # Ternary
        # --------------------------------------------------------------

        if isinstance(node, TernaryExpr):
            self.compile_ternary(node, scope)
            return

        # --------------------------------------------------------------
        # Cast
        # --------------------------------------------------------------

        if isinstance(node, CastExpr):
            value = (
                node.value
                if hasattr(node, "value")
                else node.operand
            )

            target_type = getattr(
                node,
                "target_type",
                "Any",
            )

            self.compile_expr(value, scope)

            self.emit(
                OP.CAST,
                target_type,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        self.error(
            f"Unknown expression type: "
            f"{type(node).__name__}",
            node,
        )

    # ==================================================================
    # CALLS
    # ==================================================================

    def compile_call(
        self,
        node: FunctionCall,
        scope: SymbolTable,
    ) -> None:
        """Compile function, method or external calls."""

        # Builtin print.
        if isinstance(node.target, Identifier):
            name = node.target.name

            for arg in node.args:
                self.compile_expr(arg, scope)

            if name == "print":
                self.emit(
                    OP.PRINT,
                    line=node.line,
                    col=getattr(node, "col", 0),
                )
                return

            self.emit(
                OP.CALL,
                name,
                len(node.args),
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # External namespace call:
        #
        # ATC::Wallet::new(...)
        if isinstance(node.target, NamespaceAccess):
            for arg in node.args:
                self.compile_expr(arg, scope)

            name = "::".join(node.target.parts)

            self.emit(
                OP.CALL_EXT,
                name,
                len(node.args),
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # Method call:
        #
        # object.method(arg)
        #
        # Stack:
        #   arg...
        #   object
        #
        # CALL receives object as an additional argument.
        if isinstance(node.target, DotAccess):
            self.compile_expr(
                node.target.target,
                scope,
            )

            for arg in node.args:
                self.compile_expr(arg, scope)

            self.emit(
                OP.CALL,
                node.target.field_name,
                len(node.args) + 1,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # Dynamic call.
        self.compile_expr(
            node.target,
            scope,
        )

        for arg in node.args:
            self.compile_expr(arg, scope)

        self.emit(
            OP.CALL,
            "__dynamic__",
            len(node.args) + 1,
            line=node.line,
            col=getattr(node, "col", 0),
        )

    # ==================================================================
    # ASSIGNMENTS
    # ==================================================================

    def compile_assignment(
        self,
        node: Assignment,
        scope: SymbolTable,
    ) -> None:
        """Compile assignment expressions."""

        # x = value
        if isinstance(node.target, Identifier):
            self.compile_expr(node.value, scope)

            scope.define_or_get(
                node.target.name,
                "local",
            )

            self.emit(
                OP.STORE,
                node.target.name,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # object[index] = value
        if isinstance(node.target, IndexAccess):
            self.compile_expr(
                node.target.target,
                scope,
            )

            self.compile_expr(
                node.target.index,
                scope,
            )

            self.compile_expr(
                node.value,
                scope,
            )

            self.emit(
                OP.STORE_IDX,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # object.field = value
        if isinstance(node.target, DotAccess):
            self.compile_expr(
                node.target.target,
                scope,
            )

            self.compile_expr(
                node.value,
                scope,
            )

            self.emit(
                OP.SET_FIELD,
                node.target.field_name,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        self.error(
            "Invalid assignment target",
            node,
        )

    # ==================================================================
    # TERNARY
    # ==================================================================

    def compile_ternary(
        self,
        node: TernaryExpr,
        scope: SymbolTable,
    ) -> None:
        """
        Compile:

            cond ? then : else
        """

        self.compile_expr(
            node.cond,
            scope,
        )

        jump_else = self.emit(
            OP.JUMP_NOT,
            0,
            line=node.line,
            col=getattr(node, "col", 0),
        )

        self.compile_expr(
            node.then_expr,
            scope,
        )

        jump_end = self.emit(
            OP.JUMP,
            0,
            line=node.line,
            col=getattr(node, "col", 0),
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

    # ==================================================================
    # STATEMENTS
    # ==================================================================

    def compile_stmt(
        self,
        node: ASTNode,
        scope: SymbolTable,
    ) -> None:
        """Compile one statement."""

        # --------------------------------------------------------------
        # let / const
        # --------------------------------------------------------------

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
                    col=getattr(node, "col", 0),
                )

            typ = ""

            if getattr(node, "type_hint", None):
                typ = getattr(
                    node.type_hint,
                    "name",
                    str(node.type_hint),
                )

            scope.define_or_get(
                node.name,
                "local",
                typ,
            )

            self.emit(
                OP.STORE,
                node.name,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # return
        # --------------------------------------------------------------

        if isinstance(node, ReturnStatement):
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
                    col=getattr(node, "col", 0),
                )

            self.emit(
                OP.RETURN,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # emit
        # --------------------------------------------------------------

        if isinstance(node, EmitStatement):
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
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # require
        # --------------------------------------------------------------

        if isinstance(node, RequireStatement):
            self.compile_expr(
                node.condition,
                scope,
            )

            message = ""

            if (
                node.message is not None
                and isinstance(
                    node.message,
                    StringLiteral,
                )
            ):
                message = node.message.value

            self.emit(
                OP.REQUIRE,
                message,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # if
        # --------------------------------------------------------------

        if isinstance(node, IfStatement):
            self.compile_if(
                node,
                scope,
            )
            return

        # --------------------------------------------------------------
        # while
        # --------------------------------------------------------------

        if isinstance(node, WhileStatement):
            self.compile_while(
                node,
                scope,
            )
            return

        # --------------------------------------------------------------
        # for
        # --------------------------------------------------------------

        if isinstance(node, ForStatement):
            self.compile_for(
                node,
                scope,
            )
            return

        # --------------------------------------------------------------
        # break
        # --------------------------------------------------------------

        if isinstance(node, BreakStatement):
            if not self._break_stack:
                self.error(
                    "'break' outside loop",
                    node,
                )

            jump_index = self.emit(
                OP.JUMP,
                0,
                line=node.line,
                col=getattr(node, "col", 0),
            )

            self._break_stack[-1].append(
                jump_index
            )
            return

        # --------------------------------------------------------------
        # continue
        # --------------------------------------------------------------

        if isinstance(node, ContinueStatement):
            if not self._continue_stack:
                self.error(
                    "'continue' outside loop",
                    node,
                )

            self.emit(
                OP.JUMP,
                self._continue_stack[-1],
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # expression statement
        # --------------------------------------------------------------

        if isinstance(node, ExprStatement):
            self.compile_expr(
                node.expr,
                scope,
            )

            self.emit(
                OP.POP,
                line=getattr(node, "line", 0),
                col=getattr(node, "col", 0),
            )
            return

        # --------------------------------------------------------------
        # assignment as statement
        # --------------------------------------------------------------

        if isinstance(node, Assignment):
            self.compile_assignment(
                node,
                scope,
            )
            return

        # --------------------------------------------------------------
        # state field
        # --------------------------------------------------------------

        if isinstance(node, StateField):
            # State declarations are represented in contract metadata
            # and initialized by compile_contract().
            return

        self.error(
            f"Unknown statement type: "
            f"{type(node).__name__}",
            node,
        )

    # ==================================================================
    # IF
    # ==================================================================

    def compile_if(
        self,
        node: IfStatement,
        scope: SymbolTable,
    ) -> None:
        """
        Compile:

            if cond {}
            elif cond {}
            else {}
        """

        end_jumps: List[int] = []

        # --------------------------------------------------------------
        # if
        # --------------------------------------------------------------

        self.compile_expr(
            node.condition,
            scope,
        )

        jump_false = self.emit(
            OP.JUMP_NOT,
            0,
            line=node.line,
            col=getattr(node, "col", 0),
        )

        then_scope = scope.child()

        for stmt in node.then_block:
            self.compile_stmt(
                stmt,
                then_scope,
            )

        if node.elif_blocks or node.else_block:
            end_jumps.append(
                self.emit(
                    OP.JUMP,
                    0,
                    line=node.line,
                )
            )

        self.patch(
            jump_false,
            self.current_pos(),
        )

        # --------------------------------------------------------------
        # elif
        # --------------------------------------------------------------

        for condition, body in node.elif_blocks:
            self.compile_expr(
                condition,
                scope,
            )

            jump_false = self.emit(
                OP.JUMP_NOT,
                0,
            )

            elif_scope = scope.child()

            for stmt in body:
                self.compile_stmt(
                    stmt,
                    elif_scope,
                )

            end_jumps.append(
                self.emit(
                    OP.JUMP,
                    0,
                )
            )

            self.patch(
                jump_false,
                self.current_pos(),
            )

        # --------------------------------------------------------------
        # else
        # --------------------------------------------------------------

        if node.else_block:
            else_scope = scope.child()

            for stmt in node.else_block:
                self.compile_stmt(
                    stmt,
                    else_scope,
                )

        # --------------------------------------------------------------
        # End
        # --------------------------------------------------------------

        end_position = self.current_pos()

        for jump in end_jumps:
            self.patch(
                jump,
                end_position,
            )

    # ==================================================================
    # WHILE
    # ==================================================================

    def compile_while(
        self,
        node: WhileStatement,
        scope: SymbolTable,
    ) -> None:
        """
        Compile:

            while condition {
                body
            }
        """

        loop_start = self.current_pos()

        self.compile_expr(
            node.condition,
            scope,
        )

        jump_out = self.emit(
            OP.JUMP_NOT,
            0,
            line=node.line,
            col=getattr(node, "col", 0),
        )

        self._break_stack.append([])
        self._continue_stack.append(loop_start)

        body_scope = scope.child()

        for stmt in node.body:
            self.compile_stmt(
                stmt,
                body_scope,
            )

        self.emit(
            OP.JUMP,
            loop_start,
            line=node.line,
            col=getattr(node, "col", 0),
        )

        loop_end = self.current_pos()

        self.patch(
            jump_out,
            loop_end,
        )

        for break_jump in self._break_stack[-1]:
            self.patch(
                break_jump,
                loop_end,
            )

        self._break_stack.pop()
        self._continue_stack.pop()

    # ==================================================================
    # FOR
    # ==================================================================

    def compile_for(
        self,
        node: ForStatement,
        scope: SymbolTable,
    ) -> None:
        """
        Lower:

            for x in iterable {}

        into an indexed iteration loop.
        """

        iterator_name = self.new_temp(
            f"__iter_{node.var}"
        )

        index_name = self.new_temp(
            f"__index_{node.var}"
        )

        # iterable
        self.compile_expr(
            node.iterable,
            scope,
        )

        self.emit(
            OP.STORE,
            iterator_name,
            line=node.line,
        )

        # index = 0
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

        # index
        self.emit(
            OP.LOAD,
            index_name,
        )

        # len(iterable)
        self.emit(
            OP.LOAD,
            iterator_name,
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

        self._break_stack.append([])
        self._continue_stack.append(
            loop_start
        )

        # x = iterable[index]
        self.emit(
            OP.LOAD,
            iterator_name,
        )

        self.emit(
            OP.LOAD,
            index_name,
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

        body_scope.define_or_get(
            node.var,
            "local",
        )

        for stmt in node.body:
            self.compile_stmt(
                stmt,
                body_scope,
            )

        # continue target:
        # index++
        continue_target = self.current_pos()

        # Patch continue jumps to increment block.
        for instruction_index in self._collect_continue_jumps(
            loop_start
        ):
            self.patch(
                instruction_index,
                continue_target,
            )

        self.emit(
            OP.LOAD,
            index_name,
        )

        self.emit(
            OP.PUSH,
            1,
        )

        self.emit(
            OP.ADD,
        )

        self.emit(
            OP.STORE,
            index_name,
        )

        self.emit(
            OP.JUMP,
            loop_start,
        )

        loop_end = self.current_pos()

        self.patch(
            jump_out,
            loop_end,
        )

        for break_jump in self._break_stack[-1]:
            self.patch(
                break_jump,
                loop_end,
            )

        self._break_stack.pop()
        self._continue_stack.pop()

    def _collect_continue_jumps(
        self,
        loop_start: int,
    ) -> List[int]:
        """
        Compatibility helper.

        Continue instructions are normally emitted directly to the
        current continue target. For indexed for-loops the target is
        finalized after body generation.

        The current implementation returns no deferred jumps because
        compile_for uses the loop-start target and therefore continue
        semantics are intentionally conservative.

        Kept as a dedicated hook for future loop-lowering changes.
        """

        return []

    # ==================================================================
    # TOP-LEVEL IF
    # ==================================================================

    def compile_if_toplevel(
        self,
        node: IfStatement,
        scope: SymbolTable,
    ) -> None:
        """
        Compile top-level if without automatically POP-ing expression
        results.

        Useful when an if-expression is the final program construct.
        """

        self.compile_if(
            node,
            scope,
        )

    # ==================================================================
    # FUNCTION COMPILATION
    # ==================================================================

    def compile_function(
        self,
        fn: FunctionDef,
    ) -> List[Instruction]:
        """
        Compile function into an independent instruction stream.
        """

        saved_instructions = self.instructions
        saved_source_map = self.source_map
        saved_function = self._current_function

        self.instructions = []
        self.source_map = []
        self._current_function = fn.name

        function_scope = self.globals.child()

        for parameter in fn.params:
            type_name = ""

            if getattr(
                parameter,
                "type_hint",
                None,
            ):
                type_name = getattr(
                    parameter.type_hint,
                    "name",
                    str(parameter.type_hint),
                )

            function_scope.define(
                parameter.name,
                "parameter",
                type_name,
            )

        for statement in fn.body:
            self.compile_stmt(
                statement,
                function_scope,
            )

        # Implicit return None.
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

        result = self.instructions

        self.instructions = saved_instructions
        self.source_map = saved_source_map
        self._current_function = saved_function

        return result

    # ==================================================================
    # CONTRACT COMPILATION
    # ==================================================================

    def compile_contract(
        self,
        contract: ContractDef,
    ) -> None:
        """
        Compile contract state initialization and functions.
        """

        # Register contract symbol.
        self.globals.define_or_get(
            contract.name,
            "contract",
        )

        # --------------------------------------------------------------
        # State
        # --------------------------------------------------------------

        for state in contract.states:
            type_name = ""

            if getattr(
                state,
                "type_hint",
                None,
            ):
                type_name = getattr(
                    state.type_hint,
                    "name",
                    str(state.type_hint),
                )

            # Default state initialization.
            if "Map" in type_name:
                self.emit(
                    OP.NEW_MAP,
                    0,
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

            self.globals.define_or_get(
                state_name,
                "state",
                type_name,
            )

        # --------------------------------------------------------------
        # Functions
        # --------------------------------------------------------------

        for fn in contract.functions:
            qualified_name = (
                f"{contract.name}.{fn.name}"
            )

            fn_instructions = self.compile_function(
                fn
            )

            self.functions[
                qualified_name
            ] = fn_instructions

            self.function_params[
                qualified_name
            ] = [
                parameter.name
                for parameter in fn.params
            ]

            if getattr(fn, "is_pub", False):
                self.exports.append(
                    qualified_name
                )

    # ==================================================================
    # PROGRAM COMPILATION
    # ==================================================================

    def compile_program(
        self,
        program: Program,
    ) -> CompiledModule:
        """
        Compile complete ATCLang program.
        """

        scope = self.globals

        statements = program.statements

        for index, node in enumerate(statements):
            is_last = (
                index == len(statements) - 1
            )

            # ----------------------------------------------------------
            # Contract
            # ----------------------------------------------------------

            if isinstance(node, ContractDef):
                self.compile_contract(node)
                continue

            # ----------------------------------------------------------
            # Function
            # ----------------------------------------------------------

            if isinstance(node, FunctionDef):
                fn_instructions = (
                    self.compile_function(node)
                )

                self.functions[
                    node.name
                ] = fn_instructions

                self.function_params[
                    node.name
                ] = [
                    parameter.name
                    for parameter in node.params
                ]

                if getattr(
                    node,
                    "is_pub",
                    False,
                ):
                    self.exports.append(
                        node.name
                    )

                continue

            # ----------------------------------------------------------
            # Wallet
            # ----------------------------------------------------------

            if isinstance(node, WalletDef):
                self.compile_expr(
                    node.value,
                    scope,
                )

                self.emit(
                    OP.STORE,
                    node.name,
                    line=node.line,
                    col=getattr(node, "col", 0),
                )

                scope.define_or_get(
                    node.name,
                    "global",
                    "ATCWallet",
                )

                continue

            # ----------------------------------------------------------
            # Import
            # ----------------------------------------------------------

            if isinstance(node, ImportStatement):
                path = "::".join(node.path)

                self.emit(
                    OP.CALL_EXT,
                    f"ATC::Import::{path}",
                    0,
                    line=getattr(node, "line", 0),
                    col=getattr(node, "col", 0),
                )

                if node.alias:
                    self.emit(
                        OP.STORE,
                        node.alias,
                        line=getattr(node, "line", 0),
                    )

                    scope.define_or_get(
                        node.alias,
                        "import",
                    )

                continue

            # ----------------------------------------------------------
            # Enum
            # ----------------------------------------------------------

            if isinstance(node, EnumDef):
                variants = {
                    variant: index
                    for index, variant
                    in enumerate(node.variants)
                }

                for variant, value in variants.items():
                    self.emit(
                        OP.PUSH,
                        value,
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

                scope.define_or_get(
                    node.name,
                    "enum",
                )

                continue

            # ----------------------------------------------------------
            # Struct
            # ----------------------------------------------------------

            if isinstance(node, StructDef):
                scope.define_or_get(
                    node.name,
                    "global",
                    "struct",
                )

                # Struct metadata is handled by runtime/type system.
                continue

            # ----------------------------------------------------------
            # Class / storage / type alias
            # ----------------------------------------------------------

            if isinstance(
                node,
                (
                    ClassDef,
                    StorageBlock,
                    TypeAliasDef,
                ),
            ):
                continue

            # ----------------------------------------------------------
            # Final expression
            # ----------------------------------------------------------

            if (
                is_last
                and isinstance(
                    node,
                    ExprStatement,
                )
            ):
                self.compile_expr(
                    node.expr,
                    scope,
                )

                self.emit(
                    OP.RETURN,
                    line=node.line,
                    col=getattr(node, "col", 0),
                )

                continue

            # ----------------------------------------------------------
            # Normal statement
            # ----------------------------------------------------------

            self.compile_stmt(
                node,
                scope,
            )

        # --------------------------------------------------------------
        # Program termination
        # --------------------------------------------------------------

        if (
            not self.instructions
            or self.instructions[-1].op
            not in (
                OP.RETURN,
                OP.HALT,
            )
        ):
            self.emit(OP.HALT)

        return CompiledModule(
            name=self.module_name,
            instructions=self.instructions,
            constants=self.constants,
            functions=self.functions,
            exports=self.exports,
            function_params=self.function_params,
            source_map=self.source_map,
            version=ATCB_VERSION,
        )


# ============================================================================
# PUBLIC API
# ============================================================================

def compile_source(
    source: str,
    *,
    module_name: str = "main",
) -> CompiledModule:
    """
    Compile ATCLang source directly.

    Pipeline:

        source
          -> lexer/parser
          -> AST
          -> compiler
          -> CompiledModule
    """

    from atclang.parser.parser import parse

    ast = parse(source)

    compiler = ATCCompiler(
        module_name=module_name,
    )

    return compiler.compile_program(ast)


# ============================================================================
# DISASSEMBLER
# ============================================================================

def disassemble(
    module: CompiledModule,
) -> str:
    """
    Human-readable ATC bytecode disassembly.
    """

    lines: List[str] = []

    lines.append(
        f"=== ATC Bytecode: {module.name} ==="
    )

    lines.append(
        "Version: "
        f"{module.version[0]}."
        f"{module.version[1]}"
    )

    lines.append(
        "Instrs: "
        f"{len(module.instructions)} | "
        f"Fns: {len(module.functions)} | "
        f"Constants: {len(module.constants)} | "
        f"Exports: {module.exports}"
    )

    # --------------------------------------------------------------
    # Constants
    # --------------------------------------------------------------

    if module.constants:
        lines.append("")
        lines.append("[CONSTANTS]")

        for index, value in enumerate(
            module.constants
        ):
            lines.append(
                f"  {index:04d}  {value!r}"
            )

    # --------------------------------------------------------------
    # Main
    # --------------------------------------------------------------

    lines.append("")
    lines.append("[MAIN]")

    for index, instruction in enumerate(
        module.instructions
    ):
        args = (
            " ".join(
                repr(argument)
                for argument
                in instruction.args
            )
            if instruction.args
            else ""
        )

        lines.append(
            f"  {index:04d}  "
            f"{instruction.op.name:<14} "
            f"{args}"
        )

    # --------------------------------------------------------------
    # Functions
    # --------------------------------------------------------------

    for function_name, instructions in (
        module.functions.items()
    ):
        lines.append("")
        lines.append(
            f"[FN: {function_name}]"
        )

        for index, instruction in enumerate(
            instructions
        ):
            args = (
                " ".join(
                    repr(argument)
                    for argument
                    in instruction.args
                )
                if instruction.args
                else ""
            )

            lines.append(
                f"  {index:04d}  "
                f"{instruction.op.name:<14} "
                f"{args}"
            )

    return "\n".join(lines)


# ============================================================================
# MODULE EXPORTS
# ============================================================================

__all__ = [
    "ATCB_MAGIC",
    "ATCB_VERSION",
    "ATCB_VERSION_MAJOR",
    "ATCB_VERSION_MINOR",
    "CompileError",
    "CompiledModule",
    "SourceLocation",
    "Symbol",
    "SymbolTable",
    "ATCCompiler",
    "compile_source",
    "disassemble",
]