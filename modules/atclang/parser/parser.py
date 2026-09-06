# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
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
        # Tuple type: (A, B, C)
        if self.check(TT.LPAREN):
            self.advance()
            types = [self.parse_type()]
            while self.match(TT.COMMA):
                types.append(self.parse_type())
            self.expect(TT.RPAREN)
            if len(types) == 1:
                return types[0]
            # Return as tuple type
            return TypeAnnotation("Tuple", types, 0, 0)
        # Accept both built-in TYPE tokens and user-defined IDENT types
        if self.check(TT.TYPE):
            tok = self.advance()
        elif self.check(TT.IDENT):
            tok = self.advance()
        else:
            self.error("Erwartet TYPE")
        node = TypeAnnotation(tok.value, [], tok.line, tok.col)
        if self.match(TT.LT):
            while not self.check(TT.GT):
                node.params.append(self.parse_type())
                if not self.match(TT.COMMA):
                    break
            if not self.match(TT.GT):
                # Allow RSHIFT (>>) as nested generic close
                if self.check(TT.RSHIFT):
                    self.advance()
                    # Split >> into > + > — push back a GT
                    from dataclasses import replace
                    self.tokens.insert(self.pos, replace(self.tokens[self.pos-1], type=TT.GT, value='>'))
                else:
                    self.expect(TT.GT)
            return node

    # ── Expressions ───────────────────────────────────────
    def parse_expr(self) -> ASTNode:
        return self.parse_logical()

    def parse_logical(self) -> ASTNode:
        left = self.parse_comparison()
        while self.current().type in (TT.AND, TT.OR):
            op = self.advance().value
            right = self.parse_comparison()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

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
        if self.current().type == TT.NOT:
            tok = self.advance()
            return UnaryOp('!', self.parse_unary(), tok.line, tok.col)
        if self.check(TT.KEYWORD, 'true') or self.check(TT.KEYWORD, 'false'):
            tok = self.advance()
            return BoolLiteral(tok.value == 'true', tok.line, tok.col)
        return self.parse_postfix()

    def parse_postfix(self) -> ASTNode:
        node = self.parse_primary()
        while True:
            if self.match(TT.LBRACKET):
                # Slice/Range: [a:b], [:b], [a:], [a..], [a..b], [a..=b]
                if self.check(TT.COLON):
                    self.advance()
                    if self.check(TT.RBRACKET):
                        self.advance()
                        node = SliceExpr(None, None, node.line, node.col)
                    else:
                        end = self.parse_expr()
                        self.expect(TT.RBRACKET)
                        node = SliceExpr(None, end, node.line, node.col)
                elif self.check(TT.DOTDOT) or self.check(TT.DOTDOTEQ):
                    self.advance()
                    if self.check(TT.RBRACKET):
                        self.advance()
                        node = SliceExpr(None, None, node.line, node.col)
                    else:
                        end = self.parse_expr()
                        self.expect(TT.RBRACKET)
                        node = SliceExpr(None, end, node.line, node.col)
                else:
                    idx = self.parse_expr()
                    if self.match(TT.COLON):
                        if self.check(TT.RBRACKET):
                            self.advance()
                            node = SliceExpr(idx, None, node.line, node.col)
                        else:
                            end = self.parse_expr()
                            self.expect(TT.RBRACKET)
                            node = SliceExpr(idx, end, node.line, node.col)
                    elif self.match(TT.DOTDOT) or self.match(TT.DOTDOTEQ):
                        if self.check(TT.RBRACKET):
                            self.advance()
                            node = SliceExpr(idx, None, node.line, node.col)
                        else:
                            end = self.parse_expr()
                            self.expect(TT.RBRACKET)
                            node = SliceExpr(idx, end, node.line, node.col)
                    else:
                        self.expect(TT.RBRACKET)
                        node = IndexAccess(node, idx, node.line, node.col)
            elif self.match(TT.DOT):
                # Accept keywords as field names (emit, transfer, etc.)
                if self.current().type == TT.KEYWORD:
                    field_tok = self.advance()
                elif self.current().type == TT.IDENT or self.current().type == TT.TYPE:
                    field_tok = self.advance()
                else:
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

        # Map/List literal: {} or {k: v, ...} or [a, b, ...]
        if tok.type == TT.LBRACE:
            self.advance()
            # Empty map
            if self.check(TT.RBRACE):
                self.advance()
                return MapLiteral([], tok.line, tok.col)
            # Map entries
            pairs = []
            while not self.check(TT.RBRACE) and not self.check(TT.EOF):
                key = self.parse_expr()
                self.expect(TT.COLON)
                val = self.parse_expr()
                pairs.append((key, val))
                if not self.match(TT.COMMA):
                    break
            self.expect(TT.RBRACE)
            return MapLiteral(pairs, tok.line, tok.col)

        # List literal: [a, b, ...]
        if tok.type == TT.LBRACKET:
            self.advance()
            elements = []
            while not self.check(TT.RBRACKET) and not self.check(TT.EOF):
                elements.append(self.parse_expr())
                if not self.match(TT.COMMA):
                    break
            self.expect(TT.RBRACKET)
            return ListLiteral(elements, tok.line, tok.col)

        if tok.type == TT.BOOL:
            self.advance()
            return BoolLiteral(tok.value, tok.line, tok.col)

        if self.check(TT.KEYWORD, 'null'):
            self.advance()
            return NullLiteral(tok.line, tok.col)

        # Match expression: match x { pattern => body, ... }
        if self.check(TT.KEYWORD, 'match'):
            return self.parse_match_expr()

        # TYPE used as namespace/identifier (Vec::new(), Command::List, etc.)
        if tok.type == TT.TYPE:
            parts = [tok.value]
            self.advance()
            while self.check(TT.DCOLON):
                self.advance()
                if self.current().type == TT.KEYWORD and self.current().value in ('new', 'delete', 'deploy', 'call'):
                    parts.append(self.advance().value)
                elif self.check(TT.IDENT) or self.check(TT.ATC_STD) or self.check(TT.TYPE):
                    parts.append(self.advance().value)
                else:
                    break
            if len(parts) > 1:
                node = NamespaceAccess(parts, tok.line, tok.col)
            else:
                node = Identifier(parts[0], tok.line, tok.col)
            # Named struct literal check (same as IDENT path)
            if self.check(TT.LBRACE) and parts[0][0].isupper() and len(parts[0]) > 1:
                save_pos = self.pos
                self.advance()
                if self.check(TT.RBRACE):
                    self.advance()
                    return StructLiteral(parts[0], [], tok.line, tok.col)
                if (self.current().type in (TT.IDENT, TT.TYPE, TT.KEYWORD) and 
                    self.peek().type == TT.COLON):
                    fields = []
                    while not self.check(TT.RBRACE) and not self.check(TT.EOF):
                        if self.current().type == TT.KEYWORD and self.current().value in (
                            'event', 'error', 'state', 'transfer', 'mint', 'burn', 'stake',
                            'unstake', 'vote', 'approve', 'delegate', 'process', 'channel',
                            'node', 'consensus', 'kernel', 'spawn'
                        ):
                            fname = self.advance().value
                        else:
                            fname = self.expect(TT.IDENT).value
                        self.expect(TT.COLON)
                        fval = self.parse_expr()
                        fields.append((fname, fval))
                        if not self.match(TT.COMMA):
                            break
                    self.expect(TT.RBRACE)
                    return StructLiteral(parts[0], fields, tok.line, tok.col)
                else:
                    self.pos = save_pos
                    return node
            return node

        # Namespace: ATC::Wallet::new (ATC_STD token)
        if tok.type == TT.ATC_STD:
            parts = tok.value.split('::')
            self.advance()
            while self.check(TT.DCOLON):
                self.advance()
                if self.current().type == TT.KEYWORD and self.current().value in ('new', 'delete', 'deploy', 'call'):
                    parts.append(self.advance().value)
                elif self.check(TT.IDENT) or self.check(TT.ATC_STD):
                    parts.append(self.advance().value)
                else:
                    break
            node = NamespaceAccess(parts, tok.line, tok.col)
            return node

        # Namespace: ATC::Wallet::new (IDENT token)
        if tok.type == TT.IDENT:
            parts = [tok.value]
            self.advance()
            while self.check(TT.DCOLON):
                self.advance()
                if self.current().type == TT.KEYWORD and self.current().value in ('new', 'delete', 'deploy', 'call'):
                    parts.append(self.advance().value)
                elif self.check(TT.IDENT) or self.check(TT.TYPE) or self.check(TT.ATC_STD):
                    parts.append(self.advance().value)
                else:
                    break
            if len(parts) > 1:
                node = NamespaceAccess(parts, tok.line, tok.col)
            else:
                node = Identifier(parts[0], tok.line, tok.col)
            # Named struct literal: TypeName { field: value, ... }
            # Only for PascalCase identifiers (struct types), not camelCase variables
            if self.check(TT.LBRACE) and parts[0][0].isupper() and len(parts[0]) > 1:
                save_pos = self.pos
                self.advance()  # consume {
                if self.check(TT.RBRACE):
                    self.advance()
                    return StructLiteral(parts[0], [], tok.line, tok.col)
                # Only treat as struct literal if next is IDENT/KEYWORD followed by COLON
                if (self.current().type in (TT.IDENT, TT.TYPE, TT.KEYWORD) and 
                    self.peek().type == TT.COLON):
                    fields = []
                    while not self.check(TT.RBRACE) and not self.check(TT.EOF):
                        if self.current().type == TT.KEYWORD and self.current().value in (
                            'event', 'error', 'state', 'transfer', 'mint', 'burn', 'stake',
                            'unstake', 'vote', 'approve', 'delegate', 'process', 'channel',
                            'node', 'consensus', 'kernel', 'spawn'
                        ):
                            fname = self.advance().value
                        else:
                            fname = self.expect(TT.IDENT).value
                        self.expect(TT.COLON)
                        fval = self.parse_expr()
                        fields.append((fname, fval))
                        if not self.match(TT.COMMA):
                            break
                    self.expect(TT.RBRACE)
                    return StructLiteral(parts[0], fields, tok.line, tok.col)
                else:
                    self.pos = save_pos
                    return node
            return node
            return node

        if tok.type == TT.LPAREN:
            self.advance()
            expr = self.parse_expr()
            # Tuple: (a, b, c)
            if self.match(TT.COMMA):
                elements = [expr]
                while not self.check(TT.RPAREN) and not self.check(TT.EOF):
                    elements.append(self.parse_expr())
                    if not self.match(TT.COMMA):
                        break
                self.expect(TT.RPAREN)
                return TupleExpr(elements, tok.line, tok.col)
            self.expect(TT.RPAREN)
            return expr

        # Kontextuelle Keywords als Identifier: caller, self, block, tx, now, super
        # Plus blockchain-native keywords used as function names: emit, mint, burn, etc.
        if tok.type == TT.KEYWORD and tok.value in (
            'caller', 'self', 'block', 'tx', 'now', 'super',
            'event', 'error', 'state', 'transfer', 'mint', 'burn', 'stake',
            'unstake', 'vote', 'approve', 'delegate', 'emit',
            'process', 'channel', 'node', 'consensus', 'kernel', 'spawn',
            'new', 'delete', 'deploy', 'call'
        ):
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
        # Compound assignment: +=, -=, *=, /=
        if self.current().type in (TT.PLUSEQ, TT.MINUSEQ, TT.STAREQ, TT.SLASHEQ):
            op = self.advance().value
            value = self.parse_expr()
            # Desugar: x += y → x = x + y
            import re
            bin_op = re.sub(r'=$', '', op)  # += → +
            rhs = BinaryOp(expr, bin_op, value, expr.line, expr.col)
            return Assignment(expr, rhs, expr.line, expr.col)
        self.match(TT.SEMICOLON)
        return ExprStatement(expr, expr.line, expr.col)

    def parse_let(self) -> LetStatement:
        tok      = self.advance()
        is_const = tok.value == 'const'
        # Accept keywords as variable names (state, etc.)
        if self.current().type == TT.KEYWORD and self.current().value in (
            'event', 'error', 'state', 'transfer', 'mint', 'burn', 'stake',
            'process', 'channel', 'node', 'consensus', 'kernel', 'spawn'
        ):
            name = self.advance().value
        else:
            name = self.expect(TT.IDENT).value
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
            # 'else if' → treat as elif
            if self.check(TT.KEYWORD, 'if'):
                self.advance()
                ec = self.parse_expr()
                self.expect(TT.LBRACE)
                eb = self.parse_block()
                elif_blocks.append((ec, eb))
                # Chain further elif/else if
                while self.check(TT.KEYWORD, 'elif') or (self.check(TT.KEYWORD, 'else') and self.peek().type == TT.KEYWORD and self.peek().value == 'if'):
                    if self.check(TT.KEYWORD, 'else'):
                        self.advance()  # else
                        self.advance()  # if
                    else:
                        self.advance()  # elif
                    ec = self.parse_expr()
                    self.expect(TT.LBRACE)
                    eb = self.parse_block()
                    elif_blocks.append((ec, eb))
                if self.check(TT.KEYWORD, 'else'):
                    self.advance()
                    self.expect(TT.LBRACE)
                    else_block = self.parse_block()
            else:
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
        # Accept keywords as parameter names (event, state, etc.)
        if self.current().type == TT.KEYWORD and self.current().value in (
            'event', 'error', 'state', 'transfer', 'mint', 'burn', 'stake',
            'process', 'channel', 'node', 'consensus', 'kernel'
        ):
            name = self.advance().value
        else:
            name = self.expect(TT.IDENT).value
        self.expect(TT.COLON)
        typ  = self.parse_type()
        return Parameter(name, typ)

    def parse_function(self) -> FunctionDef:
        tok    = self.advance()  # 'fn'
        # Accept blockchain keywords as function names (transfer, mint, burn, etc.)
        if self.current().type == TT.KEYWORD and self.current().value in (
            'transfer', 'mint', 'burn', 'stake', 'unstake', 'vote', 'approve', 'delegate',
            'emit', 'node', 'process', 'spawn', 'channel', 'consensus', 'kernel',
            'deploy', 'call', 'new', 'delete'
        ):
            name = self.advance().value
        else:
            name = self.expect(TT.IDENT).value
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
            elif self.check(TT.KEYWORD, 'pub') and self.peek().type == TT.KEYWORD and self.peek().value == 'fn':
                self.advance()  # 'pub'
                functions.append(self.parse_function())
            else:
                self.advance()  # skip unknown
        self.expect(TT.RBRACE)
        return ContractDef(name, standards, states, events, errors, functions, tok.line, tok.col)



    def parse_match_expr(self):
        tok = self.advance()  # 'match'
        subject = self.parse_expr()
        self.expect(TT.LBRACE)
        arms = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            # Pattern: IDENT, STRING, INT, EnumValue::Variant, or '_'
            if self.check(TT.IDENT) and self.current().value == '_':
                self.advance()
                pattern = '_'
            elif self.check(TT.IDENT) or self.check(TT.ATC_STD) or self.check(TT.TYPE):
                pattern_parts = [self.advance().value]
                while self.match(TT.DCOLON):
                    if self.check(TT.IDENT) or self.check(TT.TYPE) or self.check(TT.ATC_STD):
                        pattern_parts.append(self.advance().value)
                    else:
                        break
                pattern = '::'.join(pattern_parts)
            elif self.check(TT.STRING):
                pattern = self.advance().value
            elif self.check(TT.INT):
                pattern = str(self.advance().value)
            else:
                pattern = str(self.advance().value)
            # Expect => or :
            if self.match(TT.FAT_ARROW):
                pass
            elif self.match(TT.COLON):
                pass
            # Body: single expr or block
            if self.check(TT.LBRACE):
                self.advance()
                body = self.parse_block()
            else:
                body = [ExprStatement(self.parse_expr(), tok.line, tok.col)]
            arms.append((pattern, body))
            if not self.match(TT.COMMA) and not self.check(TT.RBRACE):
                pass
        self.expect(TT.RBRACE)
        return MatchStatement(subject, arms, tok.line, tok.col)

    def parse_struct(self) -> StructDef:
        tok = self.advance()  # 'struct'
        if self.check(TT.IDENT) or self.check(TT.TYPE):
            name = self.advance().value
        else:
            name = self.expect(TT.IDENT).value
        self.expect(TT.LBRACE)
        fields = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            # Skip 'event' declarations (event Name(...)) but NOT 'event' as field name (event: type)
            if self.check(TT.KEYWORD, 'event') and self.peek().type == TT.IDENT:
                self.advance()
                self.expect(TT.IDENT)  # event name
                if self.match(TT.LPAREN):
                    while not self.check(TT.RPAREN) and not self.check(TT.EOF):
                        self.advance()
                    self.expect(TT.RPAREN)
                self.match(TT.COMMA)
                continue
            if self.check(TT.KEYWORD, 'error') and self.peek().type == TT.IDENT:
                self.advance()
                self.expect(TT.IDENT)
                self.match(TT.COMMA)
                continue
            # Handle 'pub' prefix
            if self.check(TT.KEYWORD, 'pub'):
                self.advance()
            # Accept keywords as field names (event, error, state, etc.)
            if self.current().type == TT.KEYWORD and self.current().value in (
                'event', 'error', 'state', 'transfer', 'mint', 'burn', 'stake',
                'unstake', 'vote', 'approve', 'delegate', 'process', 'channel',
                'node', 'consensus', 'kernel', 'spawn'
            ):
                fname = self.advance().value
            elif self.current().type == TT.IDENT or self.current().type == TT.TYPE:
                fname = self.advance().value
            else:
                fname = self.expect(TT.IDENT).value
            self.expect(TT.COLON)
            ftype = self.parse_type()
            fields.append((fname, ftype))
            if not self.match(TT.COMMA) and not self.check(TT.RBRACE):
                pass
        self.expect(TT.RBRACE)
        return StructDef(name, fields, tok.line, tok.col)

    def parse_enum(self) -> EnumDef:
        tok = self.advance()  # 'enum'
        name = self.expect(TT.IDENT).value
        self.expect(TT.LBRACE)
        variants = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            variants.append(self.expect(TT.IDENT).value)
            if not self.match(TT.COMMA):
                break
        self.expect(TT.RBRACE)
        return EnumDef(name, variants, tok.line, tok.col)

    def parse_module(self):
        """Parse 'module name { ... }' — treats it as a namespace wrapper."""
        tok = self.advance()  # 'module'
        name = self.expect(TT.IDENT).value
        self.expect(TT.LBRACE)
        body = self.parse_block()
        # Store as a StructDef-like node (module is a container)
        return StructDef(name, body, tok.line, tok.col)

    def parse_match_stmt(self):
        """Parse 'match expr { pattern => body, ... }'"""
        tok = self.advance()  # 'match'
        subject = self.parse_expr()
        self.expect(TT.LBRACE)
        arms = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            # Pattern: IDENT, STRING, INT, EnumValue::Variant, or '_'
            if self.check(TT.IDENT) and self.current().value == '_':
                self.advance()
                pattern = '_'
            elif self.check(TT.IDENT) or self.check(TT.ATC_STD) or self.check(TT.TYPE):
                pattern_parts = [self.advance().value]
                while self.match(TT.DCOLON):
                    if self.check(TT.IDENT) or self.check(TT.TYPE) or self.check(TT.ATC_STD) or self.check(TT.KEYWORD):
                        pattern_parts.append(self.advance().value)
                    else:
                        break
                pattern = '::'.join(pattern_parts)
            elif self.check(TT.STRING):
                pattern = self.advance().value
            elif self.check(TT.INT):
                pattern = str(self.advance().value)
            else:
                pattern = str(self.advance().value)
            # Expect => or :
            if self.match(TT.FAT_ARROW):
                pass
            elif self.match(TT.COLON):
                pass
            # Body: single expr or block
            if self.check(TT.LBRACE):
                self.advance()
                body = self.parse_block()
            else:
                body = [self.parse_statement()]
            arms.append((pattern, body))
            if not self.match(TT.COMMA) and not self.check(TT.RBRACE):
                pass
        self.expect(TT.RBRACE)
        return MatchStatement(subject, arms, tok.line, tok.col)

    def parse_class(self) -> ClassDef:
        tok = self.advance()  # 'class'
        name = self.expect(TT.IDENT).value
        implements = ""
        if self.check(TT.KEYWORD, 'implements') or self.check(TT.IDENT, 'implements'):
            self.advance()
            implements = self.expect(TT.IDENT).value
        self.expect(TT.LBRACE)
        fields = []
        functions = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            if self.check(TT.KEYWORD, 'fn'):
                functions.append(self.parse_function())
            elif self.check(TT.KEYWORD, 'pub'):
                self.advance()
                if self.check(TT.KEYWORD, 'fn'):
                    functions.append(self.parse_function())
                else:
                    fname = self.expect(TT.IDENT).value
                    self.expect(TT.COLON)
                    ftype = self.parse_type()
                    fields.append((fname, ftype))
            else:
                fname = self.expect(TT.IDENT).value
                self.expect(TT.COLON)
                ftype = self.parse_type()
                fields.append((fname, ftype))
                self.match(TT.COMMA)
        self.expect(TT.RBRACE)
        return ClassDef(name, implements, fields, functions, tok.line, tok.col)

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
            elif self.check(TT.KEYWORD, 'import') or self.check(TT.KEYWORD, 'use'):
                tok  = self.advance()
                # Handle ATC_STD tokens (ATC::Namespace::Module)
                if self.check(TT.ATC_STD):
                    parts = self.advance().value.split('::')
                else:
                    parts = [self.expect(TT.IDENT).value]
                while self.match(TT.DCOLON):
                    if self.current().type == TT.KEYWORD and self.current().value in ('new', 'delete', 'deploy', 'call'):
                        parts.append(self.advance().value)
                    elif self.check(TT.IDENT) or self.check(TT.ATC_STD):
                        parts.append(self.advance().value)
                    else:
                        break
                # Handle {A, B, C} group imports: use ATC::Types::{ A, B, C }
                alias = None
                if self.match(TT.LBRACE):
                    # Group import: collect all identifiers
                    group_items = []
                    while not self.check(TT.RBRACE) and not self.check(TT.EOF):
                        if self.check(TT.IDENT) or self.check(TT.ATC_STD):
                            group_items.append(self.advance().value)
                        if not self.match(TT.COMMA):
                            break
                    self.expect(TT.RBRACE)
                    # Store group as alias (list of items)
                    alias = group_items
                elif self.check(TT.KEYWORD, 'as'):
                    self.advance()
                    alias = self.expect(TT.IDENT).value
                prog.statements.append(ImportStatement(parts, alias, tok.line, tok.col))
            elif self.check(TT.KEYWORD, 'struct'):
                prog.statements.append(self.parse_struct())
            elif self.check(TT.KEYWORD, 'enum'):
                prog.statements.append(self.parse_enum())
            elif self.check(TT.KEYWORD, 'module'):
                prog.statements.append(self.parse_module())
            elif self.check(TT.KEYWORD, 'match'):
                prog.statements.append(self.parse_match_stmt())
            elif self.check(TT.KEYWORD, 'class'):
                prog.statements.append(self.parse_class())
            else:
                prog.statements.append(self.parse_statement())
        return prog


def parse(source: str) -> Program:
    """Hilfsfunktion: Quellcode → AST"""
    lexer  = ATCLexer(source)
    tokens = lexer.tokenize()
    parser = ATCParser(tokens)
    return parser.parse_program()
