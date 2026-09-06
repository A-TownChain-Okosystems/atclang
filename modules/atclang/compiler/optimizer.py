# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Optimizer
=================

ATC-92 | Compiler Optimization Pipeline

Der Optimizer arbeitet auf zwei Ebenen:

    Source
      ↓
    AST Optimizer
      ├── Constant Folding
      ├── Constant Propagation
      ├── Algebraic Simplification
      └── Dead Code Elimination
      ↓
    Compiler
      ↓
    ATC Bytecode
      ↓
    Bytecode Optimizer
      ├── Jump Threading
      ├── Reachability Analysis
      └── Peephole Optimization

Designziele:

- deterministische Transformationen
- keine Änderung beobachtbarer Semantik
- keine Optimierung über Seiteneffekte hinweg
- scope-sichere Constant Propagation
- keine Annahme über VM-interne Implementierungsdetails
- kompatibel mit der modularisierten compiler/-Struktur

Optimization Levels:

    0 = disabled
    1 = constant folding + safe dead code elimination
    2 = + constant propagation + algebraic simplification
    3 = + bytecode peephole + jump threading
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from atclang.parser.ast_nodes import (
    ASTNode,
    Program,

    IntLiteral,
    FloatLiteral,
    StringLiteral,
    BoolLiteral,
    NullLiteral,

    Identifier,
    BinaryOp,
    UnaryOp,
    Assignment,
    IndexAccess,
    DotAccess,
    NamespaceAccess,
    FunctionCall,
    TernaryExpr,
    CastExpr,
    TupleExpr,
    ListLiteral,
    MapLiteral,
    StructLiteral,

    LetStatement,
    ReturnStatement,
    EmitStatement,
    RequireStatement,
    IfStatement,
    ForStatement,
    WhileStatement,
    BreakStatement,
    ContinueStatement,
    ExprStatement,

    FunctionDef,
    ContractDef,
    WalletDef,
    ImportStatement,
    EnumDef,
    StructDef,
    ClassDef,
    StorageBlock,
    TypeAliasDef,
    StateField,
)

from atclang.vm.atcvm import Instruction, OP


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass(frozen=True)
class OptimizerConfig:
    """
    Optimizer configuration.

    level:
        0 = disabled
        1 = conservative
        2 = aggressive AST
        3 = AST + bytecode
    """

    level: int = 1
    constant_folding: bool = True
    constant_propagation: bool = True
    algebraic_simplification: bool = True
    dead_code_elimination: bool = True
    jump_threading: bool = True
    peephole: bool = True

    def normalized(self) -> "OptimizerConfig":
        level = max(0, min(3, self.level))

        if level == 0:
            return OptimizerConfig(
                level=0,
                constant_folding=False,
                constant_propagation=False,
                algebraic_simplification=False,
                dead_code_elimination=False,
                jump_threading=False,
                peephole=False,
            )

        if level == 1:
            return OptimizerConfig(
                level=1,
                constant_folding=self.constant_folding,
                constant_propagation=False,
                algebraic_simplification=False,
                dead_code_elimination=self.dead_code_elimination,
                jump_threading=False,
                peephole=False,
            )

        if level == 2:
            return OptimizerConfig(
                level=2,
                constant_folding=self.constant_folding,
                constant_propagation=self.constant_propagation,
                algebraic_simplification=self.algebraic_simplification,
                dead_code_elimination=self.dead_code_elimination,
                jump_threading=False,
                peephole=False,
            )

        return OptimizerConfig(
            level=3,
            constant_folding=self.constant_folding,
            constant_propagation=self.constant_propagation,
            algebraic_simplification=self.algebraic_simplification,
            dead_code_elimination=self.dead_code_elimination,
            jump_threading=self.jump_threading,
            peephole=self.peephole,
        )


# ============================================================================
# STATISTICS
# ============================================================================

@dataclass
class OptimizationStats:
    constants_folded: int = 0
    constants_propagated: int = 0
    algebraic_simplified: int = 0
    dead_code_removed: int = 0
    dead_stores_removed: int = 0
    jumps_threaded: int = 0
    peephole_optimizations: int = 0

    def as_dict(self) -> Dict[str, int]:
        return {
            "constants_folded": self.constants_folded,
            "constants_propagated": self.constants_propagated,
            "algebraic_simplified": self.algebraic_simplified,
            "dead_code_removed": self.dead_code_removed,
            "dead_stores_removed": self.dead_stores_removed,
            "jumps_threaded": self.jumps_threaded,
            "peephole_optimizations": self.peephole_optimizations,
        }

    def reset(self) -> None:
        self.constants_folded = 0
        self.constants_propagated = 0
        self.algebraic_simplified = 0
        self.dead_code_removed = 0
        self.dead_stores_removed = 0
        self.jumps_threaded = 0
        self.peephole_optimizations = 0


# ============================================================================
# CONSTANT INFORMATION
# ============================================================================

_UNKNOWN = object()


@dataclass
class ConstantInfo:
    value: Any
    immutable: bool = True


# ============================================================================
# OPTIMIZER
# ============================================================================

class ATCOptimizer:
    """
    ATCLang AST + bytecode optimizer.

    The optimizer is deliberately conservative around:

    - function calls
    - external calls
    - assignments
    - state fields
    - imports
    - dynamic access
    - contract boundaries

    This is critical for smart-contract semantics.
    """

    VERSION = "0.3.0"

    def __init__(
        self,
        level: int = 1,
        config: Optional[OptimizerConfig] = None,
    ):
        if config is None:
            config = OptimizerConfig(level=level)

        self.config = config.normalized()
        self.level = self.config.level
        self.stats = OptimizationStats()

    # ========================================================================
    # PUBLIC API
    # ========================================================================

    def optimize_ast(self, program: Program) -> Program:
        """
        Optimize an AST in-place and return it.

        The AST remains structurally compatible with the parser.
        """

        if self.level == 0:
            return program

        constants: Dict[str, ConstantInfo] = {}

        program.statements = self._opt_block(
            program.statements,
            constants,
            top_level=True,
        )

        return program

    def optimize_bytecode(
        self,
        instructions: List[Instruction],
    ) -> List[Instruction]:
        """
        Optimize one bytecode instruction stream.

        Jump targets are reindexed after reachability pruning.
        """

        if self.level < 3 or not instructions:
            return instructions

        result = list(instructions)

        if self.config.jump_threading:
            result = self._thread_jumps(result)

        if self.config.dead_code_elimination:
            result = self._remove_unreachable(result)

        if self.config.peephole:
            result = self._peephole(result)

        return result

    def get_stats(self) -> Dict[str, int]:
        return self.stats.as_dict()

    def reset_stats(self) -> None:
        self.stats.reset()

    # ========================================================================
    # AST BLOCKS
    # ========================================================================

    def _opt_block(
        self,
        block: List[ASTNode],
        constants: Dict[str, ConstantInfo],
        *,
        top_level: bool = False,
    ) -> List[ASTNode]:

        result: List[ASTNode] = []

        local_constants = dict(constants)

        for stmt in block:
            optimized = self._opt_stmt(stmt, local_constants)

            if optimized is None:
                self.stats.dead_code_removed += 1
                continue

            if isinstance(optimized, list):
                result.extend(optimized)
            else:
                result.append(optimized)

            if self.config.dead_code_elimination:
                if self._terminates_flow(optimized):
                    remaining = len(block) - len(result)

                    if remaining > 0:
                        self.stats.dead_code_removed += remaining

                    break

        return result

    def _terminates_flow(self, node: ASTNode) -> bool:
        return isinstance(
            node,
            (
                ReturnStatement,
                BreakStatement,
                ContinueStatement,
            ),
        )

    # ========================================================================
    # STATEMENTS
    # ========================================================================

    def _opt_stmt(
        self,
        node: ASTNode,
        constants: Dict[str, ConstantInfo],
    ) -> Optional[ASTNode]:

        # --------------------------------------------------------------------
        # LET
        # --------------------------------------------------------------------

        if isinstance(node, LetStatement):

            if node.value is not None:
                node.value = self._opt_expr(
                    node.value,
                    constants,
                )

                value = self._evaluate_constant(
                    node.value,
                    constants,
                )

                if node.is_const and value is not _UNKNOWN:
                    constants[node.name] = ConstantInfo(value)

                elif node.name in constants:
                    del constants[node.name]

            return node

        # --------------------------------------------------------------------
        # RETURN
        # --------------------------------------------------------------------

        if isinstance(node, ReturnStatement):

            if node.value is not None:
                node.value = self._opt_expr(
                    node.value,
                    constants,
                )

            return node

        # --------------------------------------------------------------------
        # ASSIGNMENT STATEMENT
        # --------------------------------------------------------------------

        if isinstance(node, Assignment):

            node.value = self._opt_expr(
                node.value,
                constants,
            )

            self._invalidate_assignment_constants(
                node,
                constants,
            )

            return node

        # --------------------------------------------------------------------
        # EXPRESSION
        # --------------------------------------------------------------------

        if isinstance(node, ExprStatement):

            node.expr = self._opt_expr(
                node.expr,
                constants,
            )

            return node

        # --------------------------------------------------------------------
        # REQUIRE
        # --------------------------------------------------------------------

        if isinstance(node, RequireStatement):

            node.condition = self._opt_expr(
                node.condition,
                constants,
            )

            if node.message is not None:
                node.message = self._opt_expr(
                    node.message,
                    constants,
                )

            return node

        # --------------------------------------------------------------------
        # EMIT
        # --------------------------------------------------------------------

        if isinstance(node, EmitStatement):

            node.args = [
                self._opt_expr(arg, constants)
                for arg in node.args
            ]

            return node

        # --------------------------------------------------------------------
        # IF
        # --------------------------------------------------------------------

        if isinstance(node, IfStatement):

            node.condition = self._opt_expr(
                node.condition,
                constants,
            )

            condition = self._evaluate_constant(
                node.condition,
                constants,
            )

            if condition is True:
                self.stats.dead_code_removed += 1

                return self._opt_block(
                    node.then_block,
                    dict(constants),
                )

            if condition is False and not node.elif_blocks:
                self.stats.dead_code_removed += 1

                if node.else_block:
                    return self._opt_block(
                        self._as_block(node.else_block),
                        dict(constants),
                    )

                return None

            node.then_block = self._opt_block(
                node.then_block,
                dict(constants),
            )

            optimized_elifs = []

            for condition_node, body in node.elif_blocks:

                condition_node = self._opt_expr(
                    condition_node,
                    constants,
                )

                body = self._opt_block(
                    body,
                    dict(constants),
                )

                optimized_elifs.append(
                    (condition_node, body)
                )

            node.elif_blocks = optimized_elifs

            if node.else_block:
                node.else_block = self._opt_block(
                    self._as_block(node.else_block),
                    dict(constants),
                )

            return node

        # --------------------------------------------------------------------
        # WHILE
        # --------------------------------------------------------------------

        if isinstance(node, WhileStatement):

            node.condition = self._opt_expr(
                node.condition,
                constants,
            )

            condition = self._evaluate_constant(
                node.condition,
                constants,
            )

            if condition is False:
                self.stats.dead_code_removed += 1
                return None

            node.body = self._opt_block(
                node.body,
                dict(constants),
            )

            return node

        # --------------------------------------------------------------------
        # FOR
        # --------------------------------------------------------------------

        if isinstance(node, ForStatement):

            node.iterable = self._opt_expr(
                node.iterable,
                constants,
            )

            body_constants = dict(constants)

            body_constants.pop(node.var, None)

            node.body = self._opt_block(
                node.body,
                body_constants,
            )

            return node

        # --------------------------------------------------------------------
        # FUNCTION
        # --------------------------------------------------------------------

        if isinstance(node, FunctionDef):

            # Function scopes must never inherit caller-local constants.
            function_constants: Dict[str, ConstantInfo] = {}

            for parameter in node.params:
                function_constants.pop(
                    parameter.name,
                    None,
                )

            node.body = self._opt_block(
                node.body,
                function_constants,
            )

            return node

        # --------------------------------------------------------------------
        # CONTRACT
        # --------------------------------------------------------------------

        if isinstance(node, ContractDef):

            for function in node.functions:
                self._opt_stmt(
                    function,
                    {},
                )

            return node

        # --------------------------------------------------------------------
        # OTHER DECLARATIONS
        # --------------------------------------------------------------------

        if isinstance(
            node,
            (
                WalletDef,
                ImportStatement,
                EnumDef,
                StructDef,
                ClassDef,
                StorageBlock,
                TypeAliasDef,
                StateField,
            ),
        ):
            return node

        if isinstance(
            node,
            (
                BreakStatement,
                ContinueStatement,
            ),
        ):
            return node

        return node

    # ========================================================================
    # EXPRESSIONS
    # ========================================================================

    def _opt_expr(
        self,
        node: Optional[ASTNode],
        constants: Dict[str, ConstantInfo],
    ) -> Optional[ASTNode]:

        if node is None:
            return None

        # --------------------------------------------------------------------
        # IDENTIFIER
        # --------------------------------------------------------------------

        if isinstance(node, Identifier):

            if (
                self.config.constant_propagation
                and node.name in constants
            ):
                info = constants[node.name]

                self.stats.constants_propagated += 1

                return self._make_literal(
                    info.value,
                    getattr(node, "line", 0),
                    getattr(node, "col", 0),
                )

            return node

        # --------------------------------------------------------------------
        # BINARY
        # --------------------------------------------------------------------

        if isinstance(node, BinaryOp):

            node.left = self._opt_expr(
                node.left,
                constants,
            )

            # Preserve short-circuit semantics.
            left_value = self._evaluate_constant(
                node.left,
                constants,
            )

            if node.op in ("&&", "and") and left_value is False:
                self.stats.constants_folded += 1
                return BoolLiteral(
                    False,
                    node.line,
                    node.col,
                )

            if node.op in ("||", "or") and left_value is True:
                self.stats.constants_folded += 1
                return BoolLiteral(
                    True,
                    node.line,
                    node.col,
                )

            node.right = self._opt_expr(
                node.right,
                constants,
            )

            if self.config.constant_folding:
                folded = self._try_fold(
                    node.left,
                    node.op,
                    node.right,
                )

                if folded is not None:
                    self.stats.constants_folded += 1
                    return folded

            if self.config.algebraic_simplification:
                simplified = self._algebraic_simplify(
                    node.left,
                    node.op,
                    node.right,
                )

                if simplified is not None:
                    self.stats.algebraic_simplified += 1
                    return simplified

            return node

        # --------------------------------------------------------------------
        # UNARY
        # --------------------------------------------------------------------

        if isinstance(node, UnaryOp):

            node.operand = self._opt_expr(
                node.operand,
                constants,
            )

            if self.config.constant_folding:

                value = self._literal_value(
                    node.operand
                )

                if value is not _UNKNOWN:

                    try:
                        if node.op == "-":
                            self.stats.constants_folded += 1
                            return self._make_literal(
                                -value,
                                node.line,
                                node.col,
                            )

                        if node.op == "!":
                            self.stats.constants_folded += 1
                            return BoolLiteral(
                                not bool(value),
                                node.line,
                                node.col,
                            )

                        if node.op == "~":
                            self.stats.constants_folded += 1
                            return IntLiteral(
                                ~value,
                                node.line,
                                node.col,
                            )

                    except (TypeError, ValueError):
                        pass

            return node

        # --------------------------------------------------------------------
        # FUNCTION CALL
        # --------------------------------------------------------------------

        if isinstance(node, FunctionCall):

            node.args = [
                self._opt_expr(
                    arg,
                    constants,
                )
                for arg in node.args
            ]

            # Do not fold calls.
            # Calls may have observable side effects.
            return node

        # --------------------------------------------------------------------
        # ASSIGNMENT
        # --------------------------------------------------------------------

        if isinstance(node, Assignment):

            node.value = self._opt_expr(
                node.value,
                constants,
            )

            self._invalidate_assignment_constants(
                node,
                constants,
            )

            return node

        # --------------------------------------------------------------------
        # INDEX
        # --------------------------------------------------------------------

        if isinstance(node, IndexAccess):

            node.target = self._opt_expr(
                node.target,
                constants,
            )

            node.index = self._opt_expr(
                node.index,
                constants,
            )

            return node

        # --------------------------------------------------------------------
        # DOT ACCESS
        # --------------------------------------------------------------------

        if isinstance(node, DotAccess):

            node.target = self._opt_expr(
                node.target,
                constants,
            )

            return node

        # --------------------------------------------------------------------
        # TERNARY
        # --------------------------------------------------------------------

        if isinstance(node, TernaryExpr):

            node.cond = self._opt_expr(
                node.cond,
                constants,
            )

            condition = self._evaluate_constant(
                node.cond,
                constants,
            )

            if condition is True:
                return self._opt_expr(
                    node.then_expr,
                    constants,
                )

            if condition is False:
                return self._opt_expr(
                    node.else_expr,
                    constants,
                )

            node.then_expr = self._opt_expr(
                node.then_expr,
                constants,
            )

            node.else_expr = self._opt_expr(
                node.else_expr,
                constants,
            )

            return node

        # --------------------------------------------------------------------
        # CAST
        # --------------------------------------------------------------------

        if isinstance(node, CastExpr):

            value = (
                node.value
                if hasattr(node, "value")
                else node.operand
            )

            value = self._opt_expr(
                value,
                constants,
            )

            if hasattr(node, "value"):
                node.value = value
            else:
                node.operand = value

            return node

        # --------------------------------------------------------------------
        # COLLECTIONS
        # --------------------------------------------------------------------

        if isinstance(node, ListLiteral):

            node.elements = [
                self._opt_expr(
                    element,
                    constants,
                )
                for element in node.elements
            ]

            return node

        if isinstance(node, TupleExpr):

            node.elements = [
                self._opt_expr(
                    element,
                    constants,
                )
                for element in node.elements
            ]

            return node

        if isinstance(node, MapLiteral):

            optimized_pairs = []

            for pair in node.pairs:

                if isinstance(pair, tuple):
                    key, value = pair[:2]

                    optimized_pairs.append(
                        (
                            self._opt_expr(value, constants),
                            self._opt_expr(key, constants),
                        )
                    )

                elif isinstance(pair, dict):
                    key = pair.get("key")
                    value = pair.get("value")

                    optimized_pairs.append(
                        {
                            "key": self._opt_expr(key, constants),
                            "value": self._opt_expr(value, constants),
                        }
                    )

                else:
                    optimized_pairs.append(pair)

            node.pairs = optimized_pairs

            return node

        if isinstance(node, StructLiteral):

            node.fields = [
                (
                    name,
                    self._opt_expr(value, constants),
                )
                for name, value in node.fields
            ]

            return node

        return node

    # ========================================================================
    # CONSTANT EVALUATION
    # ========================================================================

    def _evaluate_constant(
        self,
        node: Optional[ASTNode],
        constants: Dict[str, ConstantInfo],
    ) -> Any:

        if node is None:
            return _UNKNOWN

        value = self._literal_value(node)

        if value is not _UNKNOWN:
            return value

        if isinstance(node, Identifier):
            info = constants.get(node.name)
            return (
                info.value
                if info is not None
                else _UNKNOWN
            )

        if isinstance(node, UnaryOp):

            operand = self._evaluate_constant(
                node.operand,
                constants,
            )

            if operand is _UNKNOWN:
                return _UNKNOWN

            try:
                if node.op == "-":
                    return -operand

                if node.op == "!":
                    return not bool(operand)

                if node.op == "~":
                    return ~operand

            except (TypeError, ValueError):
                return _UNKNOWN

            return _UNKNOWN

        if isinstance(node, BinaryOp):

            left = self._evaluate_constant(
                node.left,
                constants,
            )

            if node.op in ("&&", "and"):
                if left is not _UNKNOWN and not bool(left):
                    return False

            if node.op in ("||", "or"):
                if left is not _UNKNOWN and bool(left):
                    return True

            right = self._evaluate_constant(
                node.right,
                constants,
            )

            if left is _UNKNOWN or right is _UNKNOWN:
                return _UNKNOWN

            return self._evaluate_binary(
                left,
                node.op,
                right,
            )

        return _UNKNOWN

    def _evaluate_binary(
        self,
        left: Any,
        op: str,
        right: Any,
    ) -> Any:

        try:

            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right

            if op == "/":
                if right == 0:
                    return _UNKNOWN

                if isinstance(left, int) and isinstance(right, int):
                    return left // right

                return left / right

            if op == "%":
                if right == 0:
                    return _UNKNOWN

                return left % right

            if op == "**":
                return left ** right

            if op == "==":
                return left == right

            if op == "!=":
                return left != right

            if op == "<":
                return left < right

            if op == ">":
                return left > right

            if op == "<=":
                return left <= right

            if op == ">=":
                return left >= right

            if op in ("&&", "and"):
                return bool(left) and bool(right)

            if op in ("||", "or"):
                return bool(left) or bool(right)

            if op == "&":
                return left & right

            if op == "|":
                return left | right

            if op == "^":
                return left ^ right

            if op == "<<":
                return left << right

            if op == ">>":
                return left >> right

        except (
            TypeError,
            ValueError,
            OverflowError,
            ZeroDivisionError,
        ):
            return _UNKNOWN

        return _UNKNOWN

    # ========================================================================
    # FOLDING
    # ========================================================================

    def _try_fold(
        self,
        left: ASTNode,
        op: str,
        right: ASTNode,
    ) -> Optional[ASTNode]:

        lv = self._literal_value(left)
        rv = self._literal_value(right)

        if lv is _UNKNOWN or rv is _UNKNOWN:
            return None

        result = self._evaluate_binary(
            lv,
            op,
            rv,
        )

        if result is _UNKNOWN:
            return None

        return self._make_literal(
            result,
            getattr(left, "line", 0),
            getattr(left, "col", 0),
        )

    # ========================================================================
    # ALGEBRAIC SIMPLIFICATION
    # =================================================================