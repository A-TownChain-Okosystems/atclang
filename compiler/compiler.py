# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler
================

ATCLang AST -> ATC Bytecode compiler.

Pipeline:

    Source
      |
      v
    Lexer
      |
      v
    Parser
      |
      v
     AST
      |
      v
    TypeChecker
      |
      v
    ATCCompiler
      |
      v
    ATC Bytecode
      |
      v
    ATC VM

ATC-92 / ATC-93

Design goals
------------

* deterministic compilation
* explicit lexical scopes
* isolated function compilation contexts
* correct nested loop control flow
* source-map preservation
* explicit symbol management
* contract/function metadata
* no LLVM/GCC dependency
* compiler-level API only

The compiler assumes the parser and VM expose the AST and OP/Instruction
interfaces used by the ATCLang project.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
)

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

MAGIC = b"ATCB"
VERSION = b"\x01\x00"


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
# SYMBOL MANAGEMENT
# ============================================================================


@dataclass(frozen=True)
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
        wallet
    """

    name: str
    kind: str
    index: int
    typ: str = ""
    owner: Optional[str] = None


class SymbolTable:
    """
    Lexical symbol table.

    Resolution walks from the current scope towards the parent scope.
    """

    def __init__(
        self,
        parent: Optional["SymbolTable"] = None,
        *,
        name: str = "<scope>",
    ) -> None:
        self.parent = parent
        self.name = name

        self.symbols: Dict[str, Symbol] = {}
        self._next_index = 0

    @property
    def next_index(self) -> int:
        return self._next_index

    def define(
        self,
        name: str,
        kind: str,
        typ: str = "",
        *,
        owner: Optional[str] = None,
    ) -> Symbol:
        """
        Define a symbol in the current scope.

        Shadowing parent symbols is allowed.
        Redefinition in the same scope is rejected.
        """

        if name in self.symbols:
            raise CompileError(
                f"Symbol bereits definiert: '{name}'"
            )

        symbol = Symbol(
            name=name,
            kind=kind,
            index=self._next_index,
            typ=typ,
            owner=owner,
        )

        self.symbols[name] = symbol
        self._next_index += 1

        return symbol

    def resolve_local(self, name: str) -> Optional[Symbol]:
        return self.symbols.get(name)

    def resolve(self, name: str) -> Optional[Symbol]:
        symbol = self.symbols.get(name)

        if symbol is not None:
            return symbol

        if self.parent is not None:
            return self.parent.resolve(name)

        return None

    def child(self, *, name: str = "<child>") -> "SymbolTable":
        return SymbolTable(
            parent=self,
            name=name,
        )


# ============================================================================
# CONTROL FLOW
# ============================================================================


@dataclass
class LoopContext:
    """
    Control-flow context for one loop.

    continue_target:
        Target used by continue.

    break_jumps:
        Jump instructions waiting for the final loop end position.
    """

    continue_target: int
    break_jumps: List[int] = field(default_factory=list)


# ============================================================================
# COMPILATION CONTEXT
# ============================================================================


@dataclass
class CompileContext:
    """
    Instruction-generation context.

    A separate context is created for every function. This prevents function
    compilation from mutating the main instruction stream.
    """

    instructions: List[Instruction] = field(default_factory=list)

    source_map: List[Tuple[int, int, int]] = field(
        default_factory=list
    )

    scope: Optional[SymbolTable] = None

    function_name: Optional[str] = None

    loop_stack: List[LoopContext] = field(
        default_factory=list
    )


# ============================================================================
# COMPILED MODULE
# ============================================================================


@dataclass
class CompiledModule:
    """
    Result of ATCLang compilation.
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

    function_source_maps: Dict[
        str,
        List[Tuple[int, int, int]]
    ] = field(default_factory=dict)

    compiler_version: str = "0.3.0"

    bytecode_magic: bytes = MAGIC

    bytecode_version: bytes = VERSION

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

    The compiler itself does not perform parsing or type checking.

    Expected pipeline:

        parse(source)
            ->
        type checker
            ->
        ATCCompiler.compile_program(ast)
    """

    VERSION = "0.3.0"

    # ---------------------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------------------

    def __init__(self) -> None:
        self.constants: List[Any] = []

        self.functions: Dict[str, List[Instruction]] = {}

        self.function_params: Dict[str, List[str]] = {}

        self.function_source_maps: Dict[
            str,
            List[Tuple[int, int, int]]
        ] = {}

        self.exports: List[str] = []

        self.globals = SymbolTable(
            name="<global>"
        )

        self.context = CompileContext(
            scope=self.globals
        )

        self._label_count = 0

    # ---------------------------------------------------------------------
    # Error handling
    # ---------------------------------------------------------------------

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

    # ---------------------------------------------------------------------
    # Instruction API
    # ---------------------------------------------------------------------

    @property
    def instructions(self) -> List[Instruction]:
        return self.context.instructions

    @property
    def source_map(self) -> List[Tuple[int, int, int]]:
        return self.context.source_map

    def emit(
        self,
        op: OP,
        *args: Any,
        line: int = 0,
        col: int = 0,
    ) -> int:
        """
        Emit one instruction and return its instruction index.
        """

        index = len(self.instructions)

        self.instructions.append(
            Instruction(
                op,
                list(args),
            )
        )

        self.source_map.append(
            (
                index,
                line,
                col,
            )
        )

        return index

    def patch(
        self,
        instruction_index: int,
        *args: Any,
    ) -> None:
        """
        Patch instruction arguments.

        Used primarily for unresolved jump targets.
        """

        if not (
            0 <= instruction_index
            < len(self.instructions)
        ):
            self.error(
                f"Ungültiger Patch-Index: "
                f"{instruction_index}"
            )

        self.instructions[
            instruction_index
        ].args = list(args)

    def emit_jump(
        self,
        op: OP,
        *,
        line: int = 0,
        col: int = 0,
    ) -> int:
        """
        Emit an unresolved jump.
        """

        if op not in (
            OP.JUMP,
            OP.JUMP_IF,
            OP.JUMP_NOT,
        ):
            raise ValueError(
                "emit_jump() erwartet einen Jump-Opcode"
            )

        return self.emit(
            op,
            0,
            line=line,
            col=col,
        )

    # ---------------------------------------------------------------------
    # Constants
    # ---------------------------------------------------------------------

    def add_constant(self, value: Any) -> int:
        """
        Add a value to the module constant pool.

        Equality-based deduplication is intentional to keep bytecode
        deterministic.
        """

        for index, existing in enumerate(self.constants):
            try:
                if existing == value:
                    return index
            except Exception:
                continue

        self.constants.append(value)

        return len(self.constants) - 1

    # ---------------------------------------------------------------------
    # Labels
    # ---------------------------------------------------------------------

    def new_label(self) -> int:
        self._label_count += 1
        return self._label_count

    def current_pos(self) -> int:
        return len(self.instructions)

    # =========================================================================
    # LOOP CONTROL
    # =========================================================================

    def begin_loop(
        self,
        continue_target: int,
    ) -> LoopContext:
        context = LoopContext(
            continue_target=continue_target
        )

        self.context.loop_stack.append(context)

        return context

    def end_loop(
        self,
        end_position: int,
    ) -> None:
        if not self.context.loop_stack:
            self.error(
                "Interner Fehler: kein aktiver Loop-Context"
            )

        context = self.context.loop_stack.pop()

        for jump_index in context.break_jumps:
            self.patch(
                jump_index,
                end_position,
            )

    def emit_break(
        self,
        node: ASTNode,
    ) -> None:
        if not self.context.loop_stack:
            self.error(
                "break außerhalb einer Schleife",
                node,
            )

        jump_index = self.emit_jump(
            OP.JUMP,
            line=getattr(node, "line", 0),
            col=getattr(node, "col", 0),
        )

        self.context.loop_stack[
            -1
        ].break_jumps.append(
            jump_index
        )

    def emit_continue(
        self,
        node: ASTNode,
    ) -> None:
        if not self.context.loop_stack:
            self.error(
                "continue außerhalb einer Schleife",
                node,
            )

        target = self.context.loop_stack[
            -1
        ].continue_target

        self.emit(
            OP.JUMP,
            target,
            line=getattr(node, "line", 0),
            col=getattr(node, "col", 0),
        )

    # =========================================================================
    # EXPRESSIONS
    # =========================================================================

    def compile_expr(
        self,
        node: ASTNode,
        scope: SymbolTable,
    ) -> None:

        if node is None:
            self.error("Expression darf nicht None sein")

        # -----------------------------------------------------------------
        # Literals
        # -----------------------------------------------------------------

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

        # -----------------------------------------------------------------
        # Identifier
        # -----------------------------------------------------------------

        if isinstance(node, Identifier):
            symbol = scope.resolve(node.name)

            # LOAD uses the symbolic name because the current VM ABI resolves
            # names at runtime. The symbol lookup here is still important for
            # compiler validation and future indexed locals.
            if symbol is None:
                # Builtins / external runtime symbols are allowed.
                self.emit(
                    OP.LOAD,
                    node.name,
                    line=node.line,
                    col=getattr(node, "col", 0),
                )
                return

            self.emit(
                OP.LOAD,
                symbol.name,
                line=node.line,
                col=getattr(node, "col", 0),
            )
            return

        # -----------------------------------------------------------------
        # Namespace access
        # -----------------------------------------------------------------

        if isinstance(node, NamespaceAccess):
            name = "::".join(node.parts)

            self.emit(
                OP.PUSH,
                name,
                line=node.line,
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Binary operation
        # -----------------------------------------------------------------

        if isinstance(node, BinaryOp):
            self.compile_expr(
                node.left,
                scope,
            )

            self.compile_expr(
                node.right,
                scope,
            )

            operator_map = {
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

            opcode = operator_map.get(node.op)

            if opcode is None:
                self.error(
                    f"Unbekannter Operator: '{node.op}'",
                    node,
                )

            self.emit(
                opcode,
                line=node.line,
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Unary operation
        # -----------------------------------------------------------------

        if isinstance(node, UnaryOp):
            self.compile_expr(
                node.operand,
                scope,
            )

            if node.op == "-":
                opcode = OP.NEG

            elif node.op == "!":
                opcode = OP.NOT

            elif node.op == "~":
                if hasattr(OP, "BITNOT"):
                    opcode = OP.BITNOT
                else:
                    self.error(
                        "ATC VM unterstützt OP.BITNOT nicht",
                        node,
                    )

            else:
                self.error(
                    f"Unbekannter Unary-Operator: "
                    f"'{node.op}'",
                    node,
                )

            self.emit(
                opcode,
                line=node.line,
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Index access
        # -----------------------------------------------------------------

        if isinstance(node, IndexAccess):
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
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Dot access
        # -----------------------------------------------------------------

        if isinstance(node, DotAccess):
            self.compile_expr(
                node.target,
                scope,
            )

            self.emit(
                OP.GET_FIELD,
                node.field_name,
                line=node.line,
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Function call
        # -----------------------------------------------------------------

        if isinstance(node, FunctionCall):

            for argument in node.args:
                self.compile_expr(
                    argument,
                    scope,
                )

            if isinstance(
                node.target,
                Identifier,
            ):
                function_name = node.target.name

                if function_name == "print":
                    self.emit(
                        OP.PRINT,
                        line=node.line,
                        col=getattr(node, "col", 0),
                    )
                else:
                    self.emit(
                        OP.CALL,
                        function_name,
                        len(node.args),
                        line=node.line,
                        col=getattr(node, "col", 0),
                    )

                return

            if isinstance(
                node.target,
                NamespaceAccess,
            ):
                function_name = "::".join(
                    node.target.parts
                )

                self.emit(
                    OP.CALL_EXT,
                    function_name,
                    len(node.args),
                    line=node.line,
                    col=getattr(node, "col", 0),
                )

                return

            if isinstance(
                node.target,
                DotAccess,
            ):
                self.compile_expr(
                    node.target.target,
                    scope,
                )

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

            self.emit(
                OP.CALL,
                "__dynamic__",
                len(node.args),
                line=node.line,
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Assignment
        # -----------------------------------------------------------------

        if isinstance(node, Assignment):

            self.compile_expr(
                node.value,
                scope,
            )

            if isinstance(
                node.target,
                Identifier,
            ):
                self.emit(
                    OP.STORE,
                    node.target.name,
                    line=node.line,
                    col=getattr(node, "col", 0),
                )
                return

            if isinstance(
                node.target,
                IndexAccess,
            ):
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
                    col=getattr(node, "col", 0),
                )

                return

            if isinstance(
                node.target,
                DotAccess,
            ):
                self.compile_expr(
                    node.target.target,
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
                "Ungültiges Assignment-Ziel",
                node,
            )

        # -----------------------------------------------------------------
        # List
        # -----------------------------------------------------------------

        if isinstance(node, ListLiteral):

            for element in node.elements:
                self.compile_expr(
                    element,
                    scope,
                )

            self.emit(
                OP.NEW_LIST,
                len(node.elements),
                line=node.line,
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Map
        # -----------------------------------------------------------------

        if isinstance(node, MapLiteral):

            for pair in node.pairs:

                if isinstance(pair, tuple) and len(pair) >= 2:
                    key = pair[0]
                    value = pair[1]

                elif isinstance(pair, dict):
                    key = pair.get("key")
                    value = pair.get("value")

                else:
                    self.error(
                        "Ungültiges Map-Literal-Paar",
                        node,
                    )

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
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Struct
        # -----------------------------------------------------------------

        if isinstance(node, StructLiteral):

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
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Tuple
        # -----------------------------------------------------------------

        if isinstance(node, TupleExpr):

            for element in node.elements:
                self.compile_expr(
                    element,
                    scope,
                )

            self.emit(
                OP.NEW_LIST,
                len(node.elements),
                line=node.line,
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # Ternary
        # -----------------------------------------------------------------

        if isinstance(node, TernaryExpr):

            self.compile_expr(
                node.cond,
                scope,
            )

            jump_else = self.emit_jump(
                OP.JUMP_NOT,
                line=node.line,
                col=getattr(node, "col", 0),
            )

            self.compile_expr(
                node.then_expr,
                scope,
            )

            jump_end = self.emit_jump(
                OP.JUMP,
                line=node.line,
                col=getattr(node, "col", 0),
            )

            self.patch(
                jump_else,
                self.current_pos(),
            )

            self.compile_expr(
                node.else_expr,
                scope,
            )

            self.patch(
                jump_end,
                self.current_pos(),
            )

            return

        # -----------------------------------------------------------------
        # Cast
        # -----------------------------------------------------------------

        if isinstance(node, CastExpr):

            value = getattr(
                node,
                "value",
                getattr(
                    node,
                    "operand",
                    None,
                ),
            )

            target_type = getattr(
                node,
                "target_type",
                "Any",
            )

            self.compile_expr(
                value,
                scope,
            )

            self.emit(
                OP.CAST,
                target_type,
                line=node.line,
                col=getattr(node, "col", 0),
            )

            return

        self.error(
            f"Unbekannter Ausdruck-Typ: "
            f"{type(node).__name__}",
            node,
        )

    # =========================================================================
    # STATEMENTS
    # =========================================================================

    def compile_stmt(
        self,
        node: ASTNode,
        scope: SymbolTable,
    ) -> None:

        # -----------------------------------------------------------------
        # let / const
        # -----------------------------------------------------------------

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
                    line=getattr(node, "line", 0),
                    col=getattr(node, "col", 0),
                )

            symbol_type = ""

            if getattr(node, "type_hint", None):
                symbol_type = getattr(
                    node.type_hint,
                    "name",
                    str(node.type_hint),
                )

            symbol = scope.define(
                node.name,
                "local",
                symbol_type,
            )

            self.emit(
                OP.STORE,
                symbol.name,
                line=getattr(node, "line", 0),
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # return
        # -----------------------------------------------------------------

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
                    line=getattr(node, "line", 0),
                    col=getattr(node, "col", 0),
                )

            self.emit(
                OP.RETURN,
                line=getattr(node, "line", 0),
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # emit
        # -----------------------------------------------------------------

        if isinstance(node, EmitStatement):

            for argument in node.args:
                self.compile_expr(
                    argument,
                    scope,
                )

            self.emit(
                OP.EMIT,
                node.event,
                len(node.args),
                line=getattr(node, "line", 0),
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # require
        # -----------------------------------------------------------------

        if isinstance(node, RequireStatement):

            self.compile_expr(
                node.condition,
                scope,
            )

            message = ""

            if (
                getattr(node, "message", None)
                and isinstance(
                    node.message,
                    StringLiteral,
                )
            ):
                message = node.message.value

            self.emit(
                OP.REQUIRE,
                message,
                line=getattr(node, "line", 0),
                col=getattr(node, "col", 0),
            )

            return

        # -----------------------------------------------------------------
        # if
        # -----------------------------------------------------------------

        if isinstance(node, IfStatement):

            self.compile_if(
                node,
                scope,
            )

            return

        # -----------------------------------------------------------------
        # while
        # -----------------------------------------------------------------

        if isinstance(node, WhileStatement):

            loop_start = self.current_pos()

            self.begin_loop(
                continue_target=loop_start
            )

            self.compile_expr(
                node.condition,
                scope,
            )

            jump_out = self.emit_jump(
                OP.JUMP_NOT,
                line=getattr(node, "line", 0),
                col=getattr(node, "col", 0),
            )

            child_scope = scope.child(
                name="while"
            )

            for statement in node.body:
                self.compile_stmt(
                    statement,
                    child_scope,
                )

            self.emit(
                OP.JUMP,
                loop_start,
            )

            end_position = self.current_pos()

            self.patch(
                jump_out,
                end_position,
            )

            self.end_loop(
                end_position
            )

            return

        # -----------------------------------------------------------------
        # for
        # -----------------------------------------------------------------

        if isinstance(node, ForStatement):

            # Evaluate iterable exactly once.
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
            )

            self.emit(
                OP.PUSH,
                0,
            )

            self.emit(
                OP.STORE,
                index_name,
            )

            loop_start = self.current_pos()

            # Continue in a for-loop must target the increment section,
            # not the condition. Therefore the actual continue target is
            # patched after the body is emitted.
            loop_context = LoopContext(
                continue_target=-1
            )

            self.context.loop_stack.append(
                loop_context
            )

            # i < len(iterable)
            self.emit(
                OP.LOAD,
                index_name,
            )

            self.emit(
                OP.LOAD,
                iterator_name,
            )

            self.emit(
                OP.CALL_EXT,
                "ATC::Std::len",
                1,
            )

            self.emit(
                OP.LT
            )

            jump_out = self.emit_jump(
                OP.JUMP_NOT
            )

            # Loop variable.
            self.emit(
                OP.LOAD,
                iterator_name,
            )

            self.emit(
                OP.LOAD,
                index_name,
            )

            self.emit(
                OP.LOAD_IDX
            )

            self.emit(
                OP.STORE,
                node.var,
            )

            child_scope = scope.child(
                name=f"for:{node.var}"
            )

            child_scope.define(
                node.var,
                "local",
            )

            for statement in node.body:
                self.compile_stmt(
                    statement,
                    child_scope,
                )

            # Increment section.
            increment_position = self.current_pos()

            loop_context.continue_target = (
                increment_position
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
                OP.ADD
            )

            self.emit(
                OP.STORE,
                index_name,
            )

            self.emit(
                OP.JUMP,
                loop_start,
            )

            end_position = self.current_pos()

            self.patch(
                jump_out,
                end_position,
            )

            self.context.loop_stack.pop()

            # Patch all break jumps.
            for jump_index in loop_context.break_jumps:
                self.patch(
                    jump_index,
                    end_position,
                )

            # Patch all continue jumps that were emitted before the
            # increment target became known.
            for index, instruction in enumerate(
                self.instructions
            ):
                if (
                    instruction.op == OP.JUMP
                    and instruction.args == [-1]
                ):
                    self.patch(
                        index,
                        increment_position,
                    )

            return

        # -----------------------------------------------------------------
        # break
        # -----------------------------------------------------------------

        if isinstance(node, BreakStatement):

            self.emit_break(node)

            return

        # -----------------------------------------------------------------
        # continue
        # -----------------------------------------------------------------

        if isinstance(node, ContinueStatement):

            self.emit_continue(node)

            return

        # -----------------------------------------------------------------
        # expression statement
        # -----------------------------------------------------------------

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

        # -----------------------------------------------------------------
        # assignment
        # -----------------------------------------------------------------

        if isinstance(node, Assignment):

            self.compile_expr(
                node,
                scope,
            )

            return

        # -----------------------------------------------------------------
        # state field
        # -----------------------------------------------------------------

        if isinstance(node, StateField):
            # State fields are initialized by compile_contract().
            return

        self.error(
            f"Unbekannter Statement-Typ: "
            f"{type(node).__name__}",
            node,
        )

    # =========================================================================
    # IF
    # =========================================================================

    def compile_if(
        self,
        node: IfStatement,
        scope: SymbolTable,
        *,
        preserve_result: bool = False,
    ) -> None:

        self.compile_expr(
            node.condition,
            scope,
        )

        jump_if_false = self.emit_jump(
            OP.JUMP_NOT,
            line=getattr(node, "line", 0),
            col=getattr(node, "col", 0),
        )

        then_scope = scope.child(
            name="if.then"
        )

        for statement in node.then_block:
            if (
                preserve_result
                and isinstance(
                    statement,
                    ExprStatement,
                )
            ):
                self.compile_expr(
                    statement.expr,
                    scope,
                )
            else:
                self.compile_stmt(
                    statement,
                    then_scope,
                )

        end_jumps: List[int] = []

        if node.else_block or node.elif_blocks:
            end_jumps.append(
                self.emit_jump(
                    OP.JUMP
                )
            )

        self.patch(
            jump_if_false,
            self.current_pos(),
        )

        # elif chain
        for elif_condition, elif_body in (
            node.elif_blocks or []
        ):

            self.compile_expr(
                elif_condition,
                scope,
            )

            elif_false = self.emit_jump(
                OP.JUMP_NOT
            )

            elif_scope = scope.child(
                name="if.elif"
            )

            for statement in elif_body:
                if (
                    preserve_result
                    and isinstance(
                        statement,
                        ExprStatement,
                    )
                ):
                    self.compile_expr(
                        statement.expr,
                        scope,
                    )
                else:
                    self.compile_stmt(
                        statement,
                        elif_scope,
                    )

            end_jumps.append(
                self.emit_jump(
                    OP.JUMP
                )
            )

            self.patch(
                elif_false,
                self.current_pos(),
            )

        # else
        if node.else_block:
            else_scope = scope.child(
                name="if.else"
            )

            for statement in node.else_block:
                if (
                    preserve_result
                    and isinstance(
                        statement,
                        ExprStatement,
                    )
                ):
                    self.compile_expr(
                        statement.expr,
                        scope,
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

    # =========================================================================
    # FUNCTIONS
    # =========================================================================

    def compile_function(
        self,
        function: FunctionDef,
        *,
        qualified_name: Optional[str] = None,
    ) -> List[Instruction]:
        """
        Compile a function in an isolated CompileContext.
        """

        function_name = (
            qualified_name
            or function.name
        )

        previous_context = self.context

        function_scope = self.globals.child(
            name=f"fn:{function_name}"
        )

        function_context = CompileContext(
            scope=function_scope,
            function_name=function_name,
        )

        self.context = function_context

        try:

            parameter_names: List[str] = []

            for parameter in function.params:
                parameter_name = parameter.name

                parameter_type = ""

                if getattr(
                    parameter,
                    "type_hint",
                    None,
                ):
                    parameter_type = getattr(
                        parameter.type_hint,
                        "name",
                        str(parameter.type_hint),
                    )

                function_scope.define(
                    parameter_name,
                    "parameter",
                    parameter_type,
                    owner=function_name,
                )

                parameter_names.append(
                    parameter_name
                )

            self.function_params[
                function_name
            ] = parameter_names

            for statement in function.body:
                self.compile_stmt(
                    statement,
                    function_scope,
                )

            # Implicit return None.
            if (
                not self.instructions
                or self.instructions[-1].op
                not in (
                    OP.RETURN,
                    OP.HALT,
                )
            ):
                self.emit(
                    OP.PUSH,
                    None,
                )

                self.emit(
                    OP.RETURN
                )

            function_instructions = list(
                self.instructions
            )

            self.function_source_maps[
                function_name
            ] = list(
                self.source_map
            )

            self.functions[
                function_name
            ] = function_instructions

            return function_instructions

        finally:
            self.context = previous_context

    # =========================================================================
    # CONTRACTS
    # =========================================================================

    def compile_contract(
        self,
        contract: ContractDef,
    ) -> None:
        """
        Compile contract state and functions.
        """

        contract_name = contract.name

        # Contract symbol.
        if self.globals.resolve_local(
            contract_name
        ) is None:
            self.globals.define(
                contract_name,
                "contract",
                owner=contract_name,
            )

        # State fields.
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

            state_symbol_name = (
                f"{contract_name}.{state.name}"
            )

            # Map defaults.
            if "Map" in type_name:
                self.emit(
                    OP.NEW_MAP,
                    0,
                    line=getattr(state, "line", 0),
                    col=getattr(state, "col", 0),
                )
            else:
                self.emit(
                    OP.PUSH,
                    None,
                    line=getattr(state, "line", 0),
                    col=getattr(state, "col", 0),
                )

            self.emit(
                OP.STORE,
                state_symbol_name,
                line=getattr(state, "line", 0),
                col=getattr(state, "col", 0),
            )

            if (
                self.globals.resolve_local(
                    state_symbol_name
                )
                is None
            ):
                self.globals.define(
                    state_symbol_name,
                    "state",
                    type_name,
                    owner=contract_name,
                )

        # Contract functions.
        for function in contract.functions:

            qualified_name = (
                f"{contract_name}.{function.name}"
            )

            self.compile_function(
                function,
                qualified_name=qualified_name,
            )

            if qualified_name not in self.exports:
                self.exports.append(
                    qualified_name
                )

    # =========================================================================
    # ENUMS
    # =========================================================================

    def compile_enum(
        self,
        enum: EnumDef,
    ) -> None:

        variants: Dict[str, int] = {}

        for index, variant in enumerate(
            enum.variants
        ):
            variant_name = (
                f"{enum.name}::{variant}"
            )

            variants[variant] = index

            self.emit(
                OP.PUSH,
                index,
            )

            self.emit(
                OP.STORE,
                variant_name,
            )

            if (
                self.globals.resolve_local(
                    variant_name
                )
                is None
            ):
                self.globals.define(
                    variant_name,
                    "enum_variant",
                    "Int",
                    owner=enum.name,
                )

        self.emit(
            OP.PUSH,
            variants,
        )

        self.emit(
            OP.STORE,
            enum.name,
        )

        if (
            self.globals.resolve_local(
                enum.name
            )
            is None
        ):
            self.globals.define(
                enum.name,
                "enum",
                owner=enum.name,
            )

    # =========================================================================
    # TOP-LEVEL PROGRAM
    # =========================================================================

    def compile_program(
        self,
        program: Program,
    ) -> CompiledModule:
        """
        Compile a complete AST program.
        """

        if not isinstance(
            program,
            Program,
        ):
            raise TypeError(
                "compile_program() erwartet Program"
            )

        statements = program.statements

        for index, node in enumerate(
            statements
        ):

            is_last = (
                index == len(statements) - 1
            )

            # -------------------------------------------------------------
            # Contract
            # -------------------------------------------------------------

            if isinstance(
                node,
                ContractDef,
            ):
                self.compile_contract(
                    node
                )
                continue

            # -------------------------------------------------------------
            # Function
            # -------------------------------------------------------------

            if isinstance(
                node,
                FunctionDef,
            ):

                self.compile_function(
                    node
                )

                if (
                    getattr(
                        node,
                        "is_pub",
                        False,
                    )
                    and node.name
                    not in self.exports
                ):
                    self.exports.append(
                        node.name
                    )

                continue

            # -------------------------------------------------------------
            # Wallet
            # -------------------------------------------------------------

            if isinstance(
                node,
                WalletDef,
            ):

                self.compile_expr(
                    node.value,
                    self.globals,
                )

                self.emit(
                    OP.STORE,
                    node.name,
                    line=getattr(node, "line", 0),
                    col=getattr(node, "col", 0),
                )

                if (
                    self.globals.resolve_local(
                        node.name
                    )
                    is None
                ):
                    self.globals.define(
                        node.name,
                        "wallet",
                        "ATCWallet",
                    )

                continue

            # -------------------------------------------------------------
            # Import
            # -------------------------------------------------------------

            if isinstance(
                node,
                ImportStatement,
            ):

                path = "::".join(
                    node.path
                )

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
                        col=getattr(node, "col", 0),
                    )

                    if (
                        self.globals.resolve_local(
                            node.alias
                        )
                        is None
                    ):
                        self.globals.define(
                            node.alias,
                            "import",
                        )

                continue

            # -------------------------------------------------------------
            # Enum
            # -------------------------------------------------------------

            if isinstance(
                node,
                EnumDef,
            ):
                self.compile_enum(
                    node
                )
                continue

            # -------------------------------------------------------------
            # Struct
            # -------------------------------------------------------------

            if isinstance(
                node,
                StructDef,
            ):
                # Struct declarations are metadata.
                # StructLiteral compilation handles runtime construction.
                continue

            # -------------------------------------------------------------
            # Type/Class/Storage metadata
            # -------------------------------------------------------------

            if isinstance(
                node,
                (
                    ClassDef,
                    StorageBlock,
                    TypeAliasDef,
                ),
            ):
                continue

            # -------------------------------------------------------------
            # Last expression
            # -------------------------------------------------------------

            if (
                is_last
                and isinstance(
                    node,
                    ExprStatement,
                )
            ):

                self.compile_expr(
                    node.expr,
                    self.globals,
                )

                self.emit(
                    OP.RETURN,
                    line=getattr(node, "line", 0),
                    col=getattr(node, "col", 0),
                )

                continue

            # -------------------------------------------------------------
            # Last top-level if
            # -------------------------------------------------------------

            if (
                is_last
                and isinstance(
                    node,
                    IfStatement,
                )
            ):

                self.compile_if(
                    node,
                    self.globals,
                    preserve_result=True,
                )

                continue

            # -------------------------------------------------------------
            # Standard statement
            # -------------------------------------------------------------

            self.compile_stmt(
                node,
                self.globals,
            )

        # Main termination.
        if (
            not self.instructions
            or self.instructions[-1].op
            not in (
                OP.RETURN,
                OP.HALT,
            )
        ):
            self.emit(
                OP.HALT
            )

        return CompiledModule(
            name="main",
            instructions=list(
                self.instructions
            ),
            constants=list(
                self.constants
            ),
            functions=dict(
                self.functions
            ),
            exports=list(
                self.exports
            ),
            function_params=dict(
                self.function_params
            ),
            source_map=list(
                self.source_map
            ),
            function_source_maps=dict(
                self.function_source_maps
            ),
            compiler_version=self.VERSION,
            bytecode_magic=MAGIC,
            bytecode_version=VERSION,
        )


# ============================================================================
# SOURCE COMPILATION
# ============================================================================


def compile_source(
    source: str,
) -> CompiledModule:
    """
    Compile ATCLang source directly.

    Pipeline:

        source
          ->
        parser
          ->
        AST
          ->
        compiler
          ->
        CompiledModule

    Type checking and optimization are intentionally not forced here so that
    callers can choose their own compilation pipeline.
    """

    if not isinstance(
        source,
        str,
    ):
        raise TypeError(
            "source muss str sein"
        )

    from atclang.parser.parser import parse

    ast = parse(source)

    compiler = ATCCompiler()

    return compiler.compile_program(
        ast
    )


# ============================================================================
# DISASSEMBLER
# ============================================================================


def disassemble(
    module: CompiledModule,
) -> str:
    """
    Render compiled ATC bytecode in human-readable form.
    """

    lines: List[str] = []

    lines.append(
        f"=== ATC Bytecode: {module.name} ==="
    )

    lines.append(
        f"Compiler: {module.compiler_version}"
    )

    lines.append(
        f"Magic: {module.bytecode_magic!r}"
    )

    lines.append(
        f"Version: {module.bytecode_version!r}"
    )

    lines.append(
        f"Instrs: {len(module.instructions)} | "
        f"Fns: {len(module.functions)} | "
        f"Constants: {len(module.constants)} | "
        f"Exports: {module.exports}"
    )

    lines.append("")

    # ---------------------------------------------------------------------
    # Constants
    # ---------------------------------------------------------------------

    lines.append(
        "[CONSTANTS]"
    )

    if module.constants:
        for index, value in enumerate(
            module.constants
        ):
            lines.append(
                f"  {index:04d}  {value!r}"
            )
    else:
        lines.append(
            "  <empty>"
        )

    # ---------------------------------------------------------------------
    # Main
    # ---------------------------------------------------------------------

    lines.append("")
    lines.append(
        "[MAIN]"
    )

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

        source = ""

        if index < len(
            module.source_map
        ):
            _, line, col = (
                module.source_map[index]
            )

            source = (
                f"    ; source {line}:{col}"
            )

        lines.append(
            f"  {index:04d}  "
            f"{instruction.op.name:<12} "
            f"{args}{source}"
        )

    # ---------------------------------------------------------------------
    # Functions
    # ---------------------------------------------------------------------

    for function_name, function_instructions in (
        module.functions.items()
    ):

        lines.append("")
        lines.append(
            f"[FN: {function_name}]"
        )

        function_map = (
            module.function_source_maps.get(
                function_name,
                [],
            )
        )

        for index, instruction in enumerate(
            function_instructions
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

            source = ""

            if index < len(function_map):
                _, line, col = (
                    function_map[index]
                )

                source = (
                    f"    ; source {line}:{col}"
                )

            lines.append(
                f"  {index:04d}  "
                f"{instruction.op.name:<12} "
                f"{args}{source}"
            )

    return "\n".join(
        lines
    )


# ============================================================================
# PUBLIC API
# ============================================================================


__all__ = [
    "MAGIC",
    "VERSION",
    "CompileError",
    "Symbol",
    "SymbolTable",
    "LoopContext",
    "CompileContext",
    "CompiledModule",
    "ATCCompiler",
    "compile_source",
    "disassemble",
]