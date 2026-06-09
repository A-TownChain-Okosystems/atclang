# ATCLang Compiler v0.2.0
# Vollständige Implementierung → atclang/compiler/compiler.py

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
        raise CompileError(f"[ATCCompi