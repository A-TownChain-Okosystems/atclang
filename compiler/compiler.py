"""
ATCLang Compiler — AST → ATC-Bytecode
Version: 0.1.0-alpha | Komplett selbst geschrieben
Kein LLVM-Klon, kein GCC-Port — eigener Code-Generator
"""

import sys, os
sys.path.insert(0, '/app')

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from atclang.parser.ast_nodes import *
from atclang.vm.atcvm import Instruction, OP


# ══════════════════════════════════════════════════════════
#  BYTECODE-FORMAT (.atcb)
# ══════════════════════════════════════════════════════════

MAGIC     = b"ATCB"   # Magic Bytes
VERSION   = b"\x01\x00"  # v1.0

@dataclass
class CompiledModule:
    name:         str
    instructions: List[Instruction]
    constants:    List[object]
    functions:    Dict[str, List[Instruction]]
    exports:      List[str]
    source_map:   List[Tuple[int, int, int]]   # (instr_idx, line, col)

    def summary(self) -> str:
        return (
            f"Module '{self.name}' | "
            f"{len(self.instructions)} Instrs | "
            f"{len(self.functions)} Fns | "
            f"{len(self.constants)} Konstanten"
        )


# ══════════════════════════════════════════════════════════
#  SYMBOL-TABELLE
# ══════════════════════════════════════════════════════════

@dataclass
class Symbol:
    name:   str
    kind:   str    # "local" | "global" | "function" | "contract" | "state"
    index:  int
    typ:    str = ""

class SymbolTable:
    def __init__(self, parent=None):
        self.symbols: Dict[str, Symbol] = {}
        self.parent  = parent
        self._next   = 0

    def define(self, name: str, kind: str, typ: str = "") -> Symbol:
        sym = Symbol(name, kind, self._next, typ)
        self.symbols[name] = sym
        self._next += 1
        return sym

    def resolve(self, name: str) -> Optional[Symbol]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.resolve(name)
        return None

    def child(self) -> 'SymbolTable':
        return SymbolTable(parent=self)


# ══════════════════════════════════════════════════════════
#  COMPILER
# ══════════════════════════════════════════════════════════

class ATCCompiler:
    """
    Kompiliert ATCLang AST → ATC-Bytecode (Instruction-Liste).
    Eigener Code-Generator — keine externen Frameworks.
    """

    def __init__(self):
        self.instructions: List[Instruction] = []
        self.constants:    List[object]       = []
        self.functions:    Dict[str, List[Instruction]] = {}
        self.exports:      List[str]          = []
        self.source_map:   List[Tuple]        = []
        self.globals       = SymbolTable()
        self._label_count  = 0
        self._break_stack: List[int]  = []   # Für break-Sprünge
        self._loop_stack:  List[int]  = []   # Für continue-Sprünge

    def error(self, msg: str, node: ASTNode = None):
        loc = f" @ Zeile {node.line}" if node and hasattr(node, 'line') else ""
        raise CompileError(f"[ATCCompiler]{loc}: {msg}")

    def emit(self, op: OP, *args, line: int = 0, col: int = 0) -> int:
        idx = len(self.instructions)
        self.instructions.append(Instruction(op, list(args)))
        self.source_map.append((idx, line, col))
        return idx

    def patch(self, idx: int, *args):
        """Rückwärts-Patch für Sprünge."""
        self.instructions[idx].args = list(args)

    def new_label(self) -> int:
        self._label_count += 1
        return self._label_count

    def current_pos(self) -> int:
        return len(self.instructions)

    def add_constant(self, val: object) -> int:
        if val not in self.constants:
            self.constants.append(val)
        return self.constants.index(val)

    # ── Expression-Compiler ───────────────────────────────

    def compile_expr(self, node: ASTNode, scope: SymbolTable):
        if isinstance(node, IntLiteral):
            self.emit(OP.PUSH, node.value, line=node.line)

        elif isinstance(node, FloatLiteral):
            self.emit(OP.PUSH, node.value, line=node.line)

        elif isinstance(node, StringLiteral):
            self.emit(OP.PUSH, node.value, line=node.line)

        elif isinstance(node, BoolLiteral):
            self.emit(OP.PUSH, node.value, line=node.line)

        elif isinstance(node, NullLiteral):
            self.emit(OP.PUSH, None, line=node.line)

        elif isinstance(node, Identifier):
            sym = scope.resolve(node.name)
            if sym:
                self.emit(OP.LOAD, node.name, line=node.line)
            else:
                # Builtin / Globals
                self.emit(OP.LOAD, node.name, line=node.line)

        elif isinstance(node, NamespaceAccess):
            # ATC::Wallet::new → als String-Referenz
            name = "::".join(node.parts)
            self.emit(OP.PUSH, name, line=node.line)

        elif isinstance(node, BinaryOp):
            self.compile_expr(node.left, scope)
            self.compile_expr(node.right, scope)
            op_map = {
                '+': OP.ADD, '-': OP.SUB, '*': OP.MUL, '/': OP.DIV,
                '==': OP.EQ, '!=': OP.NEQ,
                '<': OP.LT,  '>': OP.GT,
                '<=': OP.LTE, '>=': OP.GTE,
            }
            op = op_map.get(node.op)
            if op:
                self.emit(op, line=node.line)
            else:
                self.error(f"Unbekannter Operator: '{node.op}'", node)

        elif isinstance(node, UnaryOp):
            self.compile_expr(node.operand, scope)
            if node.op == '-':
                self.emit(OP.NEG, line=node.line)
            elif node.op == '!':
                self.emit(OP.NOT, line=node.line)

        elif isinstance(node, IndexAccess):
            self.compile_expr(node.target, scope)
            self.compile_expr(node.index, scope)
            self.emit(OP.LOAD_IDX, line=node.line)

        elif isinstance(node, DotAccess):
            self.compile_expr(node.target, scope)
            self.emit(OP.GET_FIELD, node.field_name, line=node.line)

        elif isinstance(node, FunctionCall):
            # Args auf Stack pushen
            for arg in node.args:
                self.compile_expr(arg, scope)

            if isinstance(node.target, Identifier):
                fname = node.target.name
                if fname == 'print':
                    self.emit(OP.PRINT, line=node.line)
                else:
                    self.emit(OP.CALL, fname, len(node.args), line=node.line)

            elif isinstance(node.target, NamespaceAccess):
                fname = "::".join(node.target.parts)
                self.emit(OP.CALL_EXT, fname, len(node.args), line=node.line)

            elif isinstance(node.target, DotAccess):
                self.compile_expr(node.target.target, scope)
                self.emit(OP.CALL, node.target.field_name, len(node.args) + 1, line=node.line)

            else:
                self.compile_expr(node.target, scope)
                self.emit(OP.CALL, "__dynamic__", len(node.args), line=node.line)

        elif isinstance(node, Assignment):
            self.compile_expr(node.value, scope)
            if isinstance(node.target, Identifier):
                self.emit(OP.STORE, node.target.name, line=node.line)
            elif isinstance(node.target, IndexAccess):
                self.compile_expr(node.target.target, scope)
                self.compile_expr(node.target.index, scope)
                self.emit(OP.STORE_IDX, line=node.line)
            elif isinstance(node.target, DotAccess):
                self.compile_expr(node.target.target, scope)
                self.emit(OP.SET_FIELD, node.target.field_name, line=node.line)

        else:
            self.error(f"Unbekannter Ausdruck-Typ: {type(node).__name__}", node)

    # ── Statement-Compiler ────────────────────────────────

    def compile_stmt(self, node: ASTNode, scope: SymbolTable):

        if isinstance(node, LetStatement):
            if node.value:
                self.compile_expr(node.value, scope)
            else:
                self.emit(OP.PUSH, None)
            self.emit(OP.STORE, node.name, line=node.line)
            scope.define(node.name, "local", str(node.type_hint.name) if node.type_hint else "")

        elif isinstance(node, ReturnStatement):
            if node.value:
                self.compile_expr(node.value, scope)
            else:
                self.emit(OP.PUSH, None)
            self.emit(OP.RETURN, line=node.line)

        elif isinstance(node, EmitStatement):
            for arg in node.args:
                self.compile_expr(arg, scope)
            self.emit(OP.EMIT, node.event, len(node.args), line=node.line)

        elif isinstance(node, RequireStatement):
            self.compile_expr(node.condition, scope)
            msg = ""
            if node.message and isinstance(node.message, StringLiteral):
                msg = node.message.value
            self.emit(OP.REQUIRE, msg, line=node.line)

        elif isinstance(node, IfStatement):
            self.compile_expr(node.condition, scope)
            jump_if_false = self.emit(OP.JUMP_NOT, 0, line=node.line)   # Placeholder

            child_scope = scope.child()
            for s in node.then_block:
                self.compile_stmt(s, child_scope)

            elif_jumps = []
            if node.else_block or node.elif_blocks:
                jump_over = self.emit(OP.JUMP, 0)
                elif_jumps.append(jump_over)

            self.patch(jump_if_false, self.current_pos())

            for elif_cond, elif_body in node.elif_blocks:
                self.compile_expr(elif_cond, scope)
                jf = self.emit(OP.JUMP_NOT, 0)
                cs = scope.child()
                for s in elif_body:
                    self.compile_stmt(s, cs)
                jo = self.emit(OP.JUMP, 0)
                elif_jumps.append(jo)
                self.patch(jf, self.current_pos())

            if node.else_block:
                cs = scope.child()
                for s in node.else_block:
                    self.compile_stmt(s, cs)

            end_pos = self.current_pos()
            for j in elif_jumps:
                self.patch(j, end_pos)

        elif isinstance(node, WhileStatement):
            loop_start = self.current_pos()
            self._loop_stack.append(loop_start)

            self.compile_expr(node.condition, scope)
            jump_out = self.emit(OP.JUMP_NOT, 0)
            self._break_stack.append(jump_out)

            cs = scope.child()
            for s in node.body:
                self.compile_stmt(s, cs)

            self.emit(OP.JUMP, loop_start)
            end_pos = self.current_pos()
            self.patch(jump_out, end_pos)

            self._loop_stack.pop()
            self._break_stack.pop()

        elif isinstance(node, ForStatement):
            # for x in iterable { body }
            # → iter = iterable; i = 0; while i < len(iter): x = iter[i]; body; i++
            self.compile_expr(node.iterable, scope)
            self.emit(OP.STORE, f"__iter_{node.var}__")
            self.emit(OP.PUSH, 0)
            self.emit(OP.STORE, f"__i_{node.var}__")

            loop_start = self.current_pos()
            # Bedingung: i < len(iter) — vereinfacht mit PUSH len
            self.emit(OP.LOAD, f"__i_{node.var}__")
            self.emit(OP.LOAD, f"__iter_{node.var}__")
            self.emit(OP.CALL_EXT, "ATC::Std::len", 1)
            self.emit(OP.LT)
            jump_out = self.emit(OP.JUMP_NOT, 0)

            # x = iter[i]
            self.emit(OP.LOAD, f"__iter_{node.var}__")
            self.emit(OP.LOAD, f"__i_{node.var}__")
            self.emit(OP.LOAD_IDX)
            self.emit(OP.STORE, node.var)

            cs = scope.child()
            cs.define(node.var, "local")
            for s in node.body:
                self.compile_stmt(s, cs)

            # i += 1
            self.emit(OP.LOAD, f"__i_{node.var}__")
            self.emit(OP.PUSH, 1)
            self.emit(OP.ADD)
            self.emit(OP.STORE, f"__i_{node.var}__")
            self.emit(OP.JUMP, loop_start)
            self.patch(jump_out, self.current_pos())

        elif isinstance(node, BreakStatement):
            if self._break_stack:
                jmp = self.emit(OP.JUMP, 0)
                # Wir patchen beim Loop-Ende
                self._break_stack[-1] = jmp
            else:
                self.error("break außerhalb einer Schleife", node)

        elif isinstance(node, ExprStatement):
            self.compile_expr(node.expr, scope)
            # Ergebnis vom Stack räumen
            self.emit(OP.POP)

        else:
            self.error(f"Unbekanntes Statement: {type(node).__name__}", node)

    # ── Top-Level Compiler ────────────────────────────────

    def compile_function(self, fn: FunctionDef) -> List[Instruction]:
        """Funktion kompilieren → eigene Instruction-Liste."""
        saved_instrs = self.instructions
        self.instructions = []

        scope = self.globals.child()
        for p in fn.params:
            scope.define(p.name, "local", p.type_hint.name if p.type_hint else "")

        for stmt in fn.body:
            self.compile_stmt(stmt, scope)

        # Implizites return None
        if not self.instructions or self.instructions[-1].op != OP.RETURN:
            self.emit(OP.PUSH, None)
            self.emit(OP.RETURN)

        fn_instrs = self.instructions
        self.instructions = saved_instrs
        return fn_instrs

    def compile_contract(self, contract: ContractDef):
        """Contract kompilieren — States initialisieren, Fns registrieren."""
        # State-Felder als Globals initialisieren
        for state in contract.states:
            self.emit(OP.NEW_MAP if 'Map' in (state.type_hint.name if state.type_hint else '') else OP.PUSH,
                      *([] if 'Map' in (state.type_hint.name if state.type_hint else '') else [None]))
            self.emit(OP.STORE, f"{contract.name}.{state.name}")
            self.globals.define(f"{contract.name}.{state.name}", "state",
                                state.type_hint.name if state.type_hint else "")

        # Funktionen kompilieren
        for fn in contract.functions:
            fn_name  = f"{contract.name}.{fn.name}"
            fn_instrs = self.compile_function(fn)
            self.functions[fn_name] = fn_instrs
            self.exports.append(fn_name)

    def compile_program(self, program: Program) -> CompiledModule:
        """Vollständiges Programm kompilieren."""
        scope = self.globals

        for node in program.statements:
            if isinstance(node, ContractDef):
                self.compile_contract(node)

            elif isinstance(node, FunctionDef):
                fn_instrs = self.compile_function(node)
                self.functions[node.name] = fn_instrs
                if node.is_pub:
                    self.exports.append(node.name)

            elif isinstance(node, WalletDef):
                self.compile_expr(node.value, scope)
                self.emit(OP.STORE, node.name, line=node.line)
                scope.define(node.name, "global", "ATCWallet")

            elif isinstance(node, LetStatement):
                self.compile_stmt(node, scope)

            elif isinstance(node, ImportStatement):
                path = "::".join(node.path)
                self.emit(OP.CALL_EXT, f"ATC::Import::{path}", 0)
                if node.alias:
                    self.emit(OP.STORE, node.alias)

            else:
                self.compile_stmt(node, scope)

        self.emit(OP.HALT)

        return CompiledModule(
            name         = "main",
            instructions = self.instructions,
            constants    = self.constants,
            functions    = self.functions,
            exports      = self.exports,
            source_map   = self.source_map,
        )


class CompileError(Exception):
    pass


# ── Hilfsfunktion ────────────────────────────────────────
def compile_source(source: str) -> CompiledModule:
    """Quellcode → CompiledModule (Lexer + Parser + Compiler)."""
    from atclang.parser.parser import parse
    ast      = parse(source)
    compiler = ATCCompiler()
    return compiler.compile_program(ast)


def disassemble(module: CompiledModule) -> str:
    """Bytecode lesbar ausgeben."""
    lines = [f"=== ATC Bytecode: {module.name} ==="]
    lines.append(f"Instrs: {len(module.instructions)} | Fns: {len(module.functions)} | Exports: {module.exports}")
    lines.append("")
    lines.append("[MAIN]")
    for i, instr in enumerate(module.instructions):
        args = ' '.join(repr(a) for a in instr.args) if instr.args else ""
        lines.append(f"  {i:04d}  {instr.op.name:<12} {args}")

    for fn_name, fn_instrs in module.functions.items():
        lines.append(f"\n[FN: {fn_name}]")
        for i, instr in enumerate(fn_instrs):
            args = ' '.join(repr(a) for a in instr.args) if instr.args else ""
            lines.append(f"  {i:04d}  {instr.op.name:<12} {args}")

    return "\n".join(lines)
