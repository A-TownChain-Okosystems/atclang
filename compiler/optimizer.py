# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Optimizer — Constant Folding & Dead Code Elimination.
ATC-92 | Sprint 2.1

Optimierungen:
1. Constant Folding: const x = 2 + 3 → const x = 5
2. Constant Propagation: const a = 5; let b = a + 1 → let b = 6
3. Dead Code Elimination: unreachable code after return/break/continue
4. Dead Store Elimination: let x = 1; x = 2 → let x = 2 (if x not read between)
5. Jump Threading: JUMP to JUMP → JUMP to final target
6. Algebraic Simplification: x * 1 → x, x + 0 → x, x * 0 → 0
"""
from typing import List, Dict, Set, Optional, Any
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
from atclang.vm.atcvm import OP, Instruction


class ATCOptimizer:
    """ATCLang AST + Bytecode Optimizer."""

    def __init__(self, level: int = 1):
        """
        Optimization level:
        0 = None
        1 = Constant folding + dead code (default)
        2 = + Constant propagation + algebraic simplification
        """
        self.level = level
        self.stats = {
            "constants_folded": 0,
            "dead_code_removed": 0,
            "dead_stores_removed": 0,
            "jumps_threaded": 0,
            "algebraic_simplified": 0,
            "constants_propagated": 0,
        }

    # ════════════════════════════════════════════════════
    # AST Optimization (pre-compile)
    # ════════════════════════════════════════════════════

    def optimize_ast(self, program: Program) -> Program:
        """Optimize AST before compilation."""
        if self.level == 0:
            return program

        # First pass: collect constants
        constants: Dict[str, Any] = {}
        for stmt in program.statements:
            if isinstance(stmt, LetStatement) and stmt.is_const:
                val = self._try_eval(stmt.value, constants)
                if val is not None:
                    constants[stmt.name] = val

        # Second pass: fold constants and eliminate dead code
        new_stmts: List[ASTNode] = []
        for stmt in program.statements:
            optimized = self._opt_stmt(stmt, constants)
            if optimized is not None:
                new_stmts.append(optimized)

        program.statements = new_stmts
        return program

    def _opt_stmt(self, node: ASTNode, constants: Dict[str, Any]) -> Optional[ASTNode]:
        """Optimize a single statement. Returns None if dead code."""

        if isinstance(node, LetStatement):
            # Constant propagation
            if self.level >= 2 and node.is_const:
                val = self._try_eval(node.value, constants)
                if val is not None:
                    constants[node.name] = val
                    self.stats["constants_propagated"] += 1

            # Fold expression
            node.value = self._opt_expr(node.value, constants)
            return node

        if isinstance(node, ReturnStatement):
            if node.value:
                node.value = self._opt_expr(node.value, constants)
            return node

        if isinstance(node, IfStatement):
            node.condition = self._opt_expr(node.condition, constants)

            # If condition is always true → keep only then block
            cond_val = self._try_eval(node.condition, constants)
            if cond_val is not None:
                if cond_val is True:
                    self.stats["dead_code_removed"] += 1
                    # Return first statement of then_block (wrapped)
                    return self._opt_block(node.then_block, constants)
                elif cond_val is False:
                    self.stats["dead_code_removed"] += 1
                    if node.else_block:
                        return self._opt_block(
                            node.else_block if isinstance(node.else_block, list) else [node.else_block],
                            constants
                        )
                    return None  # Dead code

            node.then_block = self._opt_block(node.then_block, constants)
            if node.elif_blocks:
                new_elif = []
                for cond, block in node.elif_blocks:
                    cond = self._opt_expr(cond, constants)
                    block = self._opt_block(block, constants)
                    new_elif.append((cond, block))
                node.elif_blocks = new_elif
            if node.else_block:
                node.else_block = self._opt_block(
                    node.else_block if isinstance(node.else_block, list) else [node.else_block],
                    constants
                )
            return node

        if isinstance(node, WhileStatement):
            node.condition = self._opt_expr(node.condition, constants)
            cond_val = self._try_eval(node.condition, constants)
            if cond_val is False:
                self.stats["dead_code_removed"] += 1
                return None  # while false → dead code
            node.body = self._opt_block(node.body, constants)
            return node

        if isinstance(node, ForStatement):
            node.iterable = self._opt_expr(node.iterable, constants)
            node.body = self._opt_block(node.body, constants)
            return node

        if isinstance(node, RequireStatement):
            node.condition = self._opt_expr(node.condition, constants)
            if node.message:
                node.message = self._opt_expr(node.message, constants)
            return node

        if isinstance(node, EmitStatement):
            node.args = [self._opt_expr(a, constants) for a in node.args]
            return node

        if isinstance(node, ExprStatement):
            node.expr = self._opt_expr(node.expr, constants)
            return node

        if isinstance(node, FunctionDef):
            node.body = self._opt_block(node.body, constants)
            return node

        if isinstance(node, ContractDef):
            node.functions = [self._opt_stmt(f, constants) for f in node.functions if f is not None]
            return node

        if isinstance(node, BreakStatement) or isinstance(node, ContinueStatement):
            return node

        return node

    def _opt_block(self, block: List[ASTNode], constants: Dict[str, Any]) -> List[ASTNode]:
        """Optimize a block, eliminating dead code after return/break/continue."""
        result: List[ASTNode] = []
        for stmt in block:
            opt = self._opt_stmt(stmt, constants)
            if opt is not None:
                result.append(opt)
                # Dead code after return/break/continue
                if isinstance(opt, (ReturnStatement, BreakStatement, ContinueStatement)):
                    removed = len(block) - len(result)
                    if removed > 0:
                        self.stats["dead_code_removed"] += removed
                    break  # Rest is unreachable
        return result

    def _opt_expr(self, node: ASTNode, constants: Dict[str, Any]) -> ASTNode:
        """Optimize an expression with constant folding and algebraic simplification."""

        if node is None:
            return node

        if isinstance(node, BinaryOp):
            left = self._opt_expr(node.left, constants)
            right = self._opt_expr(node.right, constants)
            node.left = left
            node.right = right

            # Constant folding: both sides are literals
            result = self._try_fold(left, node.op, right)
            if result is not None:
                self.stats["constants_folded"] += 1
                return result

            # Algebraic simplification (level 2+)
            if self.level >= 2:
                simplified = self._algebraic_simplify(left, node.op, right)
                if simplified is not None:
                    self.stats["algebraic_simplified"] += 1
                    return simplified

            return node

        if isinstance(node, UnaryOp):
            node.operand = self._opt_expr(node.operand, constants)
            # Constant folding for unary
            if isinstance(node.operand, IntLiteral):
                if node.op == "-":
                    self.stats["constants_folded"] += 1
                    return IntLiteral(-node.operand.value, node.line, node.col)
                if node.op == "~":
                    self.stats["constants_folded"] += 1
                    return IntLiteral(~node.operand.value, node.line, node.col)
            if isinstance(node.operand, BoolLiteral):
                if node.op == "!":
                    self.stats["constants_folded"] += 1
                    return BoolLiteral(not node.operand.value, node.line, node.col)
            return node

        if isinstance(node, Identifier):
            # Constant propagation
            if self.level >= 2 and node.name in constants:
                val = constants[node.name]
                self.stats["constants_propagated"] += 1
                return self._make_literal(val, node.line, node.col)
            return node

        if isinstance(node, FunctionCall):
            node.args = [self._opt_expr(a, constants) for a in node.args]
            return node

        if isinstance(node, Assignment):
            node.value = self._opt_expr(node.value, constants)
            return node

        if isinstance(node, IndexAccess):
            node.target = self._opt_expr(node.target, constants)
            node.index = self._opt_expr(node.index, constants)
            return node

        if isinstance(node, DotAccess):
            node.target = self._opt_expr(node.target, constants)
            return node

        return node

    def _try_fold(self, left: ASTNode, op: str, right: ASTNode) -> Optional[ASTNode]:
        """Try to fold a binary operation on two literals."""
        lv = self._literal_value(left)
        rv = self._literal_value(right)
        if lv is None or rv is None:
            return None

        try:
            if op == "+":
                return self._make_literal(lv + rv, left.line, left.col)
            elif op == "-":
                return self._make_literal(lv - rv, left.line, left.col)
            elif op == "*":
                return self._make_literal(lv * rv, left.line, left.col)
            elif op == "/":
                if rv == 0: return None
                if isinstance(lv, int) and isinstance(rv, int):
                    return IntLiteral(lv // rv, left.line, left.col)
                return self._make_literal(lv / rv, left.line, left.col)
            elif op == "%":
                if rv == 0: return None
                return IntLiteral(lv % rv, left.line, left.col)
            elif op == "**":
                return IntLiteral(lv ** rv, left.line, left.col)
            elif op == "==":
                return BoolLiteral(lv == rv, left.line, left.col)
            elif op == "!=":
                return BoolLiteral(lv != rv, left.line, left.col)
            elif op == "<":
                return BoolLiteral(lv < rv, left.line, left.col)
            elif op == ">":
                return BoolLiteral(lv > rv, left.line, left.col)
            elif op == "<=":
                return BoolLiteral(lv <= rv, left.line, left.col)
            elif op == ">=":
                return BoolLiteral(lv >= rv, left.line, left.col)
            elif op == "&&":
                return BoolLiteral(bool(lv) and bool(rv), left.line, left.col)
            elif op == "||":
                return BoolLiteral(bool(lv) or bool(rv), left.line, left.col)
            elif op == "&":
                return IntLiteral(lv & rv, left.line, left.col)
            elif op == "|":
                return IntLiteral(lv | rv, left.line, left.col)
            elif op == "^":
                return IntLiteral(lv ^ rv, left.line, left.col)
        except (TypeError, OverflowError, ZeroDivisionError):
            pass
        return None

    def _algebraic_simplify(self, left: ASTNode, op: str, right: ASTNode) -> Optional[ASTNode]:
        """Algebraic simplification rules."""
        # x + 0 → x
        if op == "+" and self._is_literal_value(right, 0):
            return left
        # 0 + x → x
        if op == "+" and self._is_literal_value(left, 0):
            return right
        # x - 0 → x
        if op == "-" and self._is_literal_value(right, 0):
            return left
        # x * 1 → x
        if op == "*" and self._is_literal_value(right, 1):
            return left
        # 1 * x → x
        if op == "*" and self._is_literal_value(left, 1):
            return right
        # x * 0 → 0
        if op == "*" and (self._is_literal_value(right, 0) or self._is_literal_value(left, 0)):
            return IntLiteral(0, left.line, left.col)
        # x / 1 → x
        if op == "/" and self._is_literal_value(right, 1):
            return left
        # x ** 0 → 1
        if op == "**" and self._is_literal_value(right, 0):
            return IntLiteral(1, left.line, left.col)
        # x ** 1 → x
        if op == "**" and self._is_literal_value(right, 1):
            return left
        # x && true → x
        if op == "&&" and self._is_literal_value(right, True):
            return left
        # true && x → x
        if op == "&&" and self._is_literal_value(left, True):
            return right
        # x || false → x
        if op == "||" and self._is_literal_value(right, False):
            return left
        # false || x → x
        if op == "||" and self._is_literal_value(left, False):
            return right
        # x & 0xFF..FF → x (mask with all ones)
        if op == "&" and self._is_literal_value(right, -1):
            return left
        # x | 0 → x
        if op == "|" and self._is_literal_value(right, 0):
            return left
        # x ^ 0 → x
        if op == "^" and self._is_literal_value(right, 0):
            return left
        return None

    def _try_eval(self, node: ASTNode, constants: Dict[str, Any]) -> Optional[Any]:
        """Try to evaluate an expression to a Python value."""
        if isinstance(node, IntLiteral): return node.value
        if isinstance(node, FloatLiteral): return node.value
        if isinstance(node, StringLiteral): return node.value
        if isinstance(node, BoolLiteral): return node.value
        if isinstance(node, NullLiteral): return None
        if isinstance(node, Identifier) and node.name in constants:
            return constants[node.name]
        if isinstance(node, BinaryOp):
            lv = self._try_eval(node.left, constants)
            rv = self._try_eval(node.right, constants)
            if lv is not None and rv is not None:
                try:
                    ops = {"+": lambda a,b: a+b, "-": lambda a,b: a-b, "*": lambda a,b: a*b,
                           "/": lambda a,b: a//b if isinstance(a,int) and isinstance(b,int) else a/b,
                           "%": lambda a,b: a%b, "**": lambda a,b: a**b,
                           "==": lambda a,b: a==b, "!=": lambda a,b: a!=b,
                           "<": lambda a,b: a<b, ">": lambda a,b: a>b,
                           "<=": lambda a,b: a<=b, ">=": lambda a,b: a>=b,
                           "&&": lambda a,b: bool(a) and bool(b),
                           "||": lambda a,b: bool(a) or bool(b),
                           "&": lambda a,b: a&b, "|": lambda a,b: a|b, "^": lambda a,b: a^b}
                    if node.op in ops:
                        return ops[node.op](lv, rv)
                except (TypeError, ZeroDivisionError):
                    pass
        if isinstance(node, UnaryOp):
            val = self._try_eval(node.operand, constants)
            if val is not None:
                if node.op == "-": return -val
                if node.op == "!": return not val
                if node.op == "~": return ~val
        return None

    def _literal_value(self, node: ASTNode) -> Optional[Any]:
        """Extract literal value from AST node."""
        if isinstance(node, IntLiteral): return node.value
        if isinstance(node, FloatLiteral): return node.value
        if isinstance(node, StringLiteral): return node.value
        if isinstance(node, BoolLiteral): return node.value
        if isinstance(node, NullLiteral): return None
        return None

    def _is_literal_value(self, node: ASTNode, val: Any) -> bool:
        """Check if node is a literal with a specific value."""
        return self._literal_value(node) == val

    def _make_literal(self, val: Any, line: int = 0, col: int = 0) -> ASTNode:
        """Create a literal AST node from a Python value."""
        if isinstance(val, bool):
            return BoolLiteral(val, line, col)
        if isinstance(val, int):
            return IntLiteral(val, line, col)
        if isinstance(val, float):
            return FloatLiteral(val, line, col)
        if isinstance(val, str):
            return StringLiteral(val, line, col)
        if val is None:
            return NullLiteral(line, col)
        return IntLiteral(0, line, col)  # Fallback

    # ════════════════════════════════════════════════════
    # Bytecode Optimization (post-compile)
    # ════════════════════════════════════════════════════

    def optimize_bytecode(self, instructions: List[Instruction]) -> List[Instruction]:
        """Optimize compiled bytecode."""
        if self.level == 0:
            return instructions

        # Pass 1: Jump threading
        instructions = self._thread_jumps(instructions)

        # Pass 2: Remove dead code (unreachable instructions after HALT/RETURN)
        instructions = self._remove_dead_bytecode(instructions)

        # Pass 3: Peephole optimization
        instructions = self._peephole(instructions)

        return instructions

    def _thread_jumps(self, instructions: List[Instruction]) -> List[Instruction]:
        """Thread jumps: JUMP to JUMP → JUMP to final target."""
        changed = True
        while changed:
            changed = False
            for i, inst in enumerate(instructions):
                if inst.op in (OP.JUMP, OP.JUMP_IF, OP.JUMP_NOT) and inst.args:
                    target = inst.args[0]
                    if 0 <= target < len(instructions):
                        target_inst = instructions[target]
                        if target_inst.op == OP.JUMP and target_inst.args:
                            # Thread to final target
                            inst.args[0] = target_inst.args[0]
                            self.stats["jumps_threaded"] += 1
                            changed = True
        return instructions

    def _remove_dead_bytecode(self, instructions: List[Instruction]) -> List[Instruction]:
        """Remove instructions that are unreachable after RETURN/HALT."""
        if not instructions:
            return instructions

        reachable = set()
        queue = [0]  # Start from first instruction

        while queue:
            ip = queue.pop(0)
            if ip in reachable or ip < 0 or ip >= len(instructions):
                continue
            reachable.add(ip)
            inst = instructions[ip]

            if inst.op in (OP.HALT, OP.RETURN):
                continue  # No fallthrough
            elif inst.op == OP.JUMP and inst.args:
                queue.append(inst.args[0])
            elif inst.op in (OP.JUMP_IF, OP.JUMP_NOT) and inst.args:
                queue.append(inst.args[0])  # Jump target
                queue.append(ip + 1)        # Fallthrough
            else:
                queue.append(ip + 1)  # Next instruction

        # Keep only reachable instructions, reindex jumps
        old_to_new: Dict[int, int] = {}
        new_instructions: List[Instruction] = []
        for i, inst in enumerate(instructions):
            if i in reachable:
                old_to_new[i] = len(new_instructions)
                new_instructions.append(inst)

        # Update jump targets
        for inst in new_instructions:
            if inst.op in (OP.JUMP, OP.JUMP_IF, OP.JUMP_NOT) and inst.args:
                old_target = inst.args[0]
                if old_target in old_to_new:
                    inst.args[0] = old_to_new[old_target]

        removed = len(instructions) - len(new_instructions)
        if removed > 0:
            self.stats["dead_code_removed"] += removed

        return new_instructions

    def _peephole(self, instructions: List[Instruction]) -> List[Instruction]:
        """Peephole optimizations on bytecode."""
        if len(instructions) < 2:
            return instructions

        result: List[Instruction] = []
        i = 0
        while i < len(instructions):
            inst = instructions[i]

            # POP after PUSH → remove both (dead code)
            if (i + 1 < len(instructions) and
                inst.op == OP.PUSH and
                instructions[i + 1].op == OP.POP):
                self.stats["dead_code_removed"] += 2
                i += 2
                continue

            # PUSH 0 + ADD → NOP (x + 0 = x)
            if (i + 1 < len(instructions) and
                inst.op == OP.PUSH and inst.args == [0] and
                instructions[i + 1].op == OP.ADD):
                self.stats["algebraic_simplified"] += 1
                i += 2
                continue

            # PUSH 1 + MUL → NOP (x * 1 = x)
            if (i + 1 < len(instructions) and
                inst.op == OP.PUSH and inst.args == [1] and
                instructions[i + 1].op == OP.MUL):
                self.stats["algebraic_simplified"] += 1
                i += 2
                continue

            # Two consecutive NOPs → one NOP
            if (inst.op == OP.NOP and
                i + 1 < len(instructions) and
                instructions[i + 1].op == OP.NOP):
                i += 1
                continue

            result.append(inst)
            i += 1

        return result

    # ════════════════════════════════════════════════════
    # Reporting
    # ════════════════════════════════════════════════════

    def get_stats(self) -> Dict[str, int]:
        return self.stats

    def reset_stats(self):
        self.stats = {k: 0 for k in self.stats}
