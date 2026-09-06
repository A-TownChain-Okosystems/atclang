# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang AST-Nodes — Abstract Syntax Tree
Alle Knoten-Typen der ATCLang Grammatik
Version: 0.1.0-alpha
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any


# ── Basis-Knoten ─────────────────────────────────────────
class ASTNode:
    line: int = 0
    col:  int = 0


# ── Ausdrücke (Expressions) ──────────────────────────────
@dataclass
class IntLiteral(ASTNode):
    value: int
    line:  int = 0
    col:   int = 0

@dataclass
class FloatLiteral(ASTNode):
    value: float
    line:  int = 0
    col:   int = 0

@dataclass
class StringLiteral(ASTNode):
    value: str
    line:  int = 0
    col:   int = 0

@dataclass
class BoolLiteral(ASTNode):
    value: bool
    line:  int = 0
    col:   int = 0

@dataclass
class ListLiteral(ASTNode):
    elements: List[ASTNode] = field(default_factory=list)
    line:     int = 0
    col:      int = 0

@dataclass
class MapLiteral(ASTNode):
    pairs:    List[tuple] = field(default_factory=list)
    line:     int = 0
    col:      int = 0

@dataclass
class NullLiteral(ASTNode):
    line:  int = 0
    col:   int = 0

@dataclass
class Identifier(ASTNode):
    name: str
    line: int = 0
    col:  int = 0

@dataclass
class BinaryOp(ASTNode):
    left:  Any
    op:    str
    right: Any
    line:  int = 0
    col:   int = 0

@dataclass
class UnaryOp(ASTNode):
    op:      str
    operand: Any
    line:    int = 0
    col:     int = 0

@dataclass
class Assignment(ASTNode):
    target: Any
    value:  Any
    line:   int = 0
    col:    int = 0

@dataclass
class IndexAccess(ASTNode):
    target: Any
    index:  Any
    line:   int = 0
    col:    int = 0

@dataclass
class DotAccess(ASTNode):
    target: Any
    field_name: str
    line:   int = 0
    col:    int = 0

@dataclass
class NamespaceAccess(ASTNode):
    parts: List[str]
    line:  int = 0
    col:   int = 0

@dataclass
class FunctionCall(ASTNode):
    target: Any
    args:   List[Any] = field(default_factory=list)
    line:   int = 0
    col:    int = 0

@dataclass
class TypeAnnotation(ASTNode):
    name:   str
    params: List[Any] = field(default_factory=list)
    line:   int = 0
    col:    int = 0



@dataclass
class StructLiteral(ASTNode):
    struct_name: str = ""
    fields: list = field(default_factory=list)
    line: int = 0
    col: int = 0


# ── Statements ───────────────────────────────────────────
@dataclass
class LetStatement(ASTNode):
    name:      str
    type_hint: Any
    value:     Any
    is_const:  bool = False
    line:      int = 0
    col:       int = 0

@dataclass
class ReturnStatement(ASTNode):
    value: Any = None
    line:  int = 0
    col:   int = 0

@dataclass
class EmitStatement(ASTNode):
    event: str
    args:  List[Any] = field(default_factory=list)
    line:  int = 0
    col:   int = 0

@dataclass
class RequireStatement(ASTNode):
    condition: Any
    message:   Any = None
    line:      int = 0
    col:       int = 0

@dataclass
class IfStatement(ASTNode):
    condition:   Any
    then_block:  List[Any]
    elif_blocks: List[Any] = field(default_factory=list)
    else_block:  Any = None
    line:        int = 0
    col:         int = 0

@dataclass
class ForStatement(ASTNode):
    var:      str
    iterable: Any
    body:     List[Any] = field(default_factory=list)
    line:     int = 0
    col:      int = 0

@dataclass
class WhileStatement(ASTNode):
    condition: Any
    body:      List[Any] = field(default_factory=list)
    line:      int = 0
    col:       int = 0

@dataclass
class BreakStatement(ASTNode):
    line: int = 0
    col:  int = 0

@dataclass
class ContinueStatement(ASTNode):
    line: int = 0
    col:  int = 0

@dataclass
class ExprStatement(ASTNode):
    expr: Any
    line: int = 0
    col:  int = 0


# ── Top-Level Definitionen ───────────────────────────────
@dataclass
class Parameter(ASTNode):
    name:      str
    type_hint: Any
    line:      int = 0
    col:       int = 0

@dataclass
class FunctionDef(ASTNode):
    name:        str
    params:      List[Any]
    return_type: Any
    body:        List[Any]
    is_pub:      bool = False
    decorators:  List[str] = field(default_factory=list)
    line:        int = 0
    col:         int = 0

@dataclass
class StateField(ASTNode):
    name:      str
    type_hint: Any
    value:     Any = None
    line:      int = 0
    col:       int = 0

@dataclass
class EventDef(ASTNode):
    name:   str
    params: List[Any] = field(default_factory=list)
    line:   int = 0
    col:    int = 0

@dataclass
class ErrorDef(ASTNode):
    name: str
    line: int = 0
    col:  int = 0

@dataclass
class ContractDef(ASTNode):
    name:      str
    standards: List[str]
    states:    List[Any]
    events:    List[Any]
    errors:    List[Any]
    functions: List[Any]
    line:      int = 0
    col:       int = 0

@dataclass
class WalletDef(ASTNode):
    name:  str
    value: Any
    line:  int = 0
    col:   int = 0

@dataclass
class ImportStatement(ASTNode):
    path:  List[str]
    alias: Any = None
    line:  int = 0
    col:   int = 0

@dataclass
class StructDef(ASTNode):
    name:   str
    fields: List[Any] = field(default_factory=list)
    line:   int = 0
    col:    int = 0

@dataclass
class EnumDef(ASTNode):
    name:     str
    variants: List[str] = field(default_factory=list)
    line:     int = 0
    col:      int = 0

@dataclass
class Program(ASTNode):
    statements: List[Any] = field(default_factory=list)
    line:       int = 0
    col:        int = 0

class MatchStatement(ASTNode):
    def __init__(self, subject, arms, line=0, col=0):
        self.subject = subject
        self.arms = arms  # list of (pattern, body)
        self.line = line
        self.col = col

    def __repr__(self):
        return f"MatchStatement(arms={len(self.arms)})"

    def children(self):
        return [self.subject] + [stmt for _, body in self.arms for stmt in body]

class SliceExpr(ASTNode):
    def __init__(self, start, end, line=0, col=0):
        self.start = start
        self.end = end
        self.line = line
        self.col = col
    def __repr__(self):
        return f'SliceExpr({self.start}:{self.end})'
    def children(self):
        return [x for x in [self.start, self.end] if x is not None]

class RangeExpr(ASTNode):
    def __init__(self, start, end, line=0, col=0):
        self.start = start
        self.end = end
        self.line = line
        self.col = col
    def __repr__(self):
        return f'RangeExpr({self.start}..{self.end})'
    def children(self):
        return [self.start, self.end]

class TupleExpr(ASTNode):
    def __init__(self, elements, line=0, col=0):
        self.elements = elements
        self.line = line
        self.col = col
    def __repr__(self):
        return f'TupleExpr({len(self.elements)})'
    def children(self):
        return self.elements
