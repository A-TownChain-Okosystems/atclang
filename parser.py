# ATCLang Parser v0.2.0
# Vollständige Implementierung → atclang/parser/parser.py

"""
ATCLang Parser — Recursive Descent Parser
Wandelt Token-Liste in einen AST um
Version: 0.1.0-alpha
"""

from typing import List, Optional
from .ast_nodes import *
from ..lexer.lexer import ATCLexer, Token, TT


class ATCParser:
    """
    Recursive Descent Parser für ATCLang.
    Produziert einen vollständigen AST.
    """

    def __init__(self, tokens: List[Token]):
        self.tokens  = [t for t in tokens if t.type not in (TT.NEWLINE, TT.COMMENT)]
        self.pos     = 0

    def error(self, msg: str):
        tok = self.current()
        raise SyntaxError(f"[ATCLang Parser] {msg} @ Zeile {tok.line}:{tok.col} (bekam: {tok.type.name} = {tok.value!r})")

    def current(self) -> Token:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else self.tokens[-1]

    def peek(self, offset=1) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def advance(self) -> Token:
        tok = self.current()
        self.pos += 1
        return tok

    def check(self, ttype: TT, value=None) -> bool:
        tok = self.current()
        if tok.type != ttype:
            return False
        if value is not None and tok.value != value:
            return False
        return True

    def expect(self, ttype: TT, value=None) -> Token:
        if not self.check(ttype, value):
            exp = f"{ttype.name}" + (f"('{value}')" if value else "")
            self.error(f"Erwartet {exp}")
        return self.advance()

    def match(self, ttype: TT, value=None) -> Optional[Token]:
        if self.check(ttype, value):
            return self.advance()
        return None

    # ── Typ-Annotation ────────────────────────────────────
    def parse_type(self) -> TypeAnnotation:
        tok = self.expect(TT.TYPE)
        node = TypeAnnotation(tok.value, [], tok.line, tok.col)
        if self.match(TT.LT):
            while not self.check(TT.GT):
                node.params.append(self.parse_type())
                if not self.match(TT.COMMA):
                    break
            self.expect(TT.GT)
        return node

    # ── Expressions ───────────────────────────────────────
    def parse_expr(self) -> ASTNode:
        return self.parse_comparison()

    def parse_comparison(self) -> ASTNode:
        left = self.parse_addition()
        while self.current().type in (TT.EQEQ, TT.NEQ, TT.LT, TT.GT, TT.LTE, TT.GTE):
            op  = self.advance().value
            right = self.parse_addition()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_addition(self) -> ASTNode:
        left = self.parse_multiplication()
        while self.current().type in (TT.PLUS, TT.MINUS):
            op    = self.advance().value
            right = self.parse_multiplication()
            left  = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_multiplication(self) -> ASTNode:
        left = self.parse_unary()
 