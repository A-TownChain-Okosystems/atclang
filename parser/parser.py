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
        while self.current().type in (TT.STAR, TT.SLASH):
            op    = self.advance().value
            right = self.parse_unary()
            left  = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_unary(self) -> ASTNode:
        if self.current().type == TT.MINUS:
            tok = self.advance()
            return UnaryOp('-', self.parse_unary(), tok.line, tok.col)
        if self.check(TT.KEYWORD, 'true') or self.check(TT.KEYWORD, 'false'):
            tok = self.advance()
            return BoolLiteral(tok.value == 'true', tok.line, tok.col)
        return self.parse_postfix()

    def parse_postfix(self) -> ASTNode:
        node = self.parse_primary()
        while True:
            if self.match(TT.LBRACKET):
                idx  = self.parse_expr()
                self.expect(TT.RBRACKET)
                node = IndexAccess(node, idx, node.line, node.col)
            elif self.match(TT.DOT):
                field_tok = self.expect(TT.IDENT)
                node = DotAccess(node, field_tok.value, node.line, node.col)
            elif self.check(TT.LPAREN):
                self.advance()
                args = []
                while not self.check(TT.RPAREN):
                    args.append(self.parse_expr())
                    if not self.match(TT.COMMA):
                        break
                self.expect(TT.RPAREN)
                node = FunctionCall(node, args, node.line, node.col)
            else:
                break
        return node

    def parse_primary(self) -> ASTNode:
        tok = self.current()

        if tok.type == TT.INT:
            self.advance()
            return IntLiteral(tok.value, tok.line, tok.col)

        if tok.type == TT.FLOAT:
            self.advance()
            return FloatLiteral(tok.value, tok.line, tok.col)

        if tok.type == TT.STRING:
            self.advance()
            return StringLiteral(tok.value, tok.line, tok.col)

        if tok.type == TT.BOOL:
            self.advance()
            return BoolLiteral(tok.value, tok.line, tok.col)

        if self.check(TT.KEYWORD, 'null'):
            self.advance()
            return NullLiteral(tok.line, tok.col)

        # Namespace: ATC::Wallet::new
        if tok.type == TT.IDENT:
            parts = [tok.value]
            self.advance()
            while self.check(TT.DCOLON):
                self.advance()
                if self.current().type == TT.KEYWORD and self.current().value in ('new', 'delete', 'deploy', 'call'):
                    parts.append(self.advance().value)
                else:
                    parts.append(self.expect(TT.IDENT).value)
            if len(parts) > 1:
                node = NamespaceAccess(parts, tok.line, tok.col)
            else:
                node = Identifier(parts[0], tok.line, tok.col)
            return node

        if tok.type == TT.LPAREN:
            self.advance()
            expr = self.parse_expr()
            self.expect(TT.RPAREN)
            return expr

        # Kontextuelle Keywords als Identifier: caller, self, block, tx, now
        if tok.type == TT.KEYWORD and tok.value in ('caller', 'self', 'block', 'tx', 'now'):
            self.advance()
            return Identifier(tok.value, tok.line, tok.col)

        self.error(f"Unerwartetes Token in Ausdruck: {tok.type.name}='{tok.value}'"  )

    # ── Statements ────────────────────────────────────────
    def parse_statement(self) -> ASTNode:
        tok = self.current()

        if self.check(TT.KEYWORD, 'let') or self.check(TT.KEYWORD, 'const'):
            return self.parse_let()
        if self.check(TT.KEYWORD, 'return'):
            return self.parse_return()
        if self.check(TT.KEYWORD, 'emit'):
            return self.parse_emit()
        if self.check(TT.KEYWORD, 'require'):
            return self.parse_require()
        if self.check(TT.KEYWORD, 'if'):
            return self.parse_if()
        if self.check(TT.KEYWORD, 'for'):
            return self.parse_for()
        if self.check(TT.KEYWORD, 'while'):
            return self.parse_while()
        if self.check(TT.KEYWORD, 'break'):
            self.advance(); return BreakStatement(tok.line, tok.col)
        if self.check(TT.KEYWORD, 'continue'):
            self.advance(); return ContinueStatement(tok.line, tok.col)

        # Zuweisung oder Ausdruck
        expr = self.parse_expr()
        if self.match(TT.EQ):
            value = self.parse_expr()
            return Assignment(expr, value, expr.line, expr.col)
        self.match(TT.SEMICOLON)
        return ExprStatement(expr, expr.line, expr.col)

    def parse_let(self) -> LetStatement:
        tok      = self.advance()
        is_const = tok.value == 'const'
        name     = self.expect(TT.IDENT).value
        type_hint = None
        if self.match(TT.COLON):
            type_hint = self.parse_type()
        value = None
        if self.match(TT.EQ):
            value = self.parse_expr()
        self.match(TT.SEMICOLON)
        return LetStatement(name, type_hint, value, is_const, tok.line, tok.col)

    def parse_return(self) -> ReturnStatement:
        tok = self.advance()
        if self.check(TT.RBRACE) or self.check(TT.EOF):
            return ReturnStatement(None, tok.line, tok.col)
        value = self.parse_expr()
        self.match(TT.SEMICOLON)
        return ReturnStatement(value, tok.line, tok.col)

    def parse_emit(self) -> EmitStatement:
        tok   = self.advance()
        event = self.expect(TT.IDENT).value
        args  = []
        if self.match(TT.LPAREN):
            while not self.check(TT.RPAREN):
                args.append(self.parse_expr())
                if not self.match(TT.COMMA): break
            self.expect(TT.RPAREN)
        return EmitStatement(event, args, tok.line, tok.col)

    def parse_require(self) -> RequireStatement:
        tok  = self.advance()
        self.expect(TT.LPAREN)
        cond = self.parse_expr()
        msg  = None
        if self.match(TT.COMMA):
            msg = self.parse_expr()
        self.expect(TT.RPAREN)
        return RequireStatement(cond, msg, tok.line, tok.col)

    def parse_if(self) -> IfStatement:
        tok  = self.advance()
        cond = self.parse_expr()
        self.expect(TT.LBRACE)
        then = self.parse_block()
        elif_blocks = []
        else_block  = None
        while self.check(TT.KEYWORD, 'elif'):
            self.advance()
            ec = self.parse_expr()
            self.expect(TT.LBRACE)
            eb = self.parse_block()
            elif_blocks.append((ec, eb))
        if self.check(TT.KEYWORD, 'else'):
            self.advance()
            self.expect(TT.LBRACE)
            else_block = self.parse_block()
        return IfStatement(cond, then, elif_blocks, else_block, tok.line, tok.col)

    def parse_for(self) -> ForStatement:
        tok = self.advance()
        var = self.expect(TT.IDENT).value
        self.expect(TT.KEYWORD, 'in')
        iterable = self.parse_expr()
        self.expect(TT.LBRACE)
        body = self.parse_block()
        return ForStatement(var, iterable, body, tok.line, tok.col)

    def parse_while(self) -> WhileStatement:
        tok  = self.advance()
        cond = self.parse_expr()
        self.expect(TT.LBRACE)
        body = self.parse_block()
        return WhileStatement(cond, body, tok.line, tok.col)

    def parse_block(self) -> List[ASTNode]:
        stmts = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            stmts.append(self.parse_statement())
        self.expect(TT.RBRACE)
        return stmts

    def parse_param(self) -> Parameter:
        name = self.expect(TT.IDENT).value
        self.expect(TT.COLON)
        typ  = self.parse_type()
        return Parameter(name, typ)

    def parse_function(self) -> FunctionDef:
        tok    = self.advance()  # 'fn'
        name   = self.expect(TT.IDENT).value
        self.expect(TT.LPAREN)
        params = []
        while not self.check(TT.RPAREN):
            params.append(self.parse_param())
            if not self.match(TT.COMMA): break
        self.expect(TT.RPAREN)
        ret_type = None
        if self.match(TT.ARROW):
            ret_type = self.parse_type()
        self.expect(TT.LBRACE)
        body = self.parse_block()
        return FunctionDef(name, params, ret_type, body, False, [], tok.line, tok.col)

    def parse_contract(self) -> ContractDef:
        tok  = self.advance()  # 'contract'
        name = self.expect(TT.IDENT).value
        standards = []
        if self.match(TT.COLON):
            while self.current().type in (TT.IDENT, TT.TYPE):
                standards.append(self.advance().value)
                if not self.match(TT.COMMA): break
        self.expect(TT.LBRACE)
        states, events, errors, functions = [], [], [], []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            if self.check(TT.KEYWORD, 'state'):
                self.advance()
                fname = self.expect(TT.IDENT).value
                self.expect(TT.COLON)
                ftype = self.parse_type()
                val = None
                if self.match(TT.EQ):
                    val = self.parse_expr()
                states.append(StateField(fname, ftype, val))
            elif self.check(TT.KEYWORD, 'event'):
                self.advance()
                ename = self.expect(TT.IDENT).value
                params = []
                if self.match(TT.LPAREN):
                    while not self.check(TT.RPAREN):
                        params.append(self.parse_param())
                        if not self.match(TT.COMMA): break
                    self.expect(TT.RPAREN)
                events.append(EventDef(ename, params))
            elif self.check(TT.KEYWORD, 'error'):
                self.advance()
                ename = self.expect(TT.IDENT).value
                errors.append(ErrorDef(ename))
            elif self.check(TT.KEYWORD, 'fn'):
                functions.append(self.parse_function())
            else:
                self.advance()  # skip unknown
        self.expect(TT.RBRACE)
        return ContractDef(name, standards, states, events, errors, functions, tok.line, tok.col)

    # ── Top-Level ─────────────────────────────────────────
    def parse_program(self) -> Program:
        prog = Program([], 1, 1)
        while not self.check(TT.EOF):
            if self.check(TT.KEYWORD, 'contract'):
                prog.statements.append(self.parse_contract())
            elif self.check(TT.KEYWORD, 'wallet'):
                tok  = self.advance()
                name = self.expect(TT.IDENT).value
                self.expect(TT.EQ)
                val  = self.parse_expr()
                prog.statements.append(WalletDef(name, val, tok.line, tok.col))
            elif self.check(TT.KEYWORD, 'fn'):
                prog.statements.append(self.parse_function())
            elif self.check(TT.KEYWORD, 'let') or self.check(TT.KEYWORD, 'const'):
                prog.statements.append(self.parse_let())
            elif self.check(TT.KEYWORD, 'import'):
                tok  = self.advance()
                parts = [self.expect(TT.IDENT).value]
                while self.match(TT.DCOLON):
                    if self.current().type == TT.KEYWORD and self.current().value in ('new', 'delete', 'deploy', 'call'):
                        parts.append(self.advance().value)
                    else:
                        parts.append(self.expect(TT.IDENT).value)
                alias = None
                if self.check(TT.KEYWORD, 'as'):
                    self.advance()
                    alias = self.expect(TT.IDENT).value
                prog.statements.append(ImportStatement(parts, alias, tok.line, tok.col))
            else:
                prog.statements.append(self.parse_statement())
        return prog


def parse(source: str) -> Program:
    """Hilfsfunktion: Quellcode → AST"""
    lexer  = ATCLexer(source)
    tokens = lexer.tokenize()
    parser = ATCParser(tokens)
    return parser.parse_program()
