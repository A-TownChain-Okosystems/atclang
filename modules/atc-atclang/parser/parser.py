# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
# STUB: Temporärer Python-Stub — wird in Sprint 2.1 durch ATCLang ersetzt (ATCLang First Policy, AD-006)
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
        # Unterdrueckt Struct-Literal-Parsing (TypeName { ... }) waehrend
        # if/while/for-Bedingungen geparst werden -- sonst wird das '{' des
        # Blocks faelschlich als Struct-Literal-Oeffnung interpretiert.
        self._no_struct_literal = 0

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
        # &mut Type or &Type — Rust-style reference types
        if self.check(TT.AMP):
            self.advance()
            if self.check(TT.KEYWORD, 'mut') or (self.check(TT.IDENT) and self.current().value == 'mut'):
                self.advance()
        # Funktionszeiger-Typ als Feld/Parameter-Typ: fn() -> Bool, fn(Int, String) -> Bool
        if self.check(TT.KEYWORD, 'fn'):
            tok = self.advance()
            self.expect(TT.LPAREN)
            arg_types = []
            while not self.check(TT.RPAREN):
                arg_types.append(self.parse_type())
                if not self.match(TT.COMMA): break
            self.expect(TT.RPAREN)
            ret = TypeAnnotation('Unit', [])
            if self.match(TT.ARROW):
                ret = self.parse_type()
            return TypeAnnotation('Fn', arg_types + [ret], tok.line, tok.col)
        # Unit-Typ: () -- z.B. als Generic-Parameter Result<()>
        if self.check(TT.LPAREN) and self.peek().type == TT.RPAREN:
            tok = self.advance()  # '('
            self.advance()        # ')'
            return TypeAnnotation('Unit', [], tok.line, tok.col)
        # Tuple-Typ: (A, B) -- z.B. Option<(CurrencyType, Decimal)>
        if self.check(TT.LPAREN):
            tok = self.advance()
            elems = [self.parse_type()]
            while self.match(TT.COMMA):
                elems.append(self.parse_type())
            self.expect(TT.RPAREN)
            return TypeAnnotation('Tuple', elems, tok.line, tok.col)
        # Accept TYPE tokens (Int, UInt256, Address, ...) and IDENT fallback (custom types)
        if self.check(TT.TYPE):
            tok = self.advance()
        elif self.check(TT.IDENT):
            tok = self.advance()
        else:
            tok = self.expect(TT.TYPE)  # Will produce error
        type_name = tok.value
        # Qualifizierter Typ-Pfad: Module::Type (z.B. PoW::PoWState)
        while self.check(TT.DCOLON):
            self.advance()
            if self.current().type in (TT.TYPE, TT.IDENT):
                type_name += "::" + self.advance().value
            else:
                self.error("Erwartet TYPE nach '::'")
        node = TypeAnnotation(type_name, [], tok.line, tok.col)
        # Generic with <>: Map<String, Int> or nested Map<String, Map<String, Int>>
        if self.match(TT.LT):
            while not self.check(TT.GT) and not (self.current().type == TT.RSHIFT):
                node.params.append(self.parse_type())
                # After parsing a param, check if inner consumed >> (closing both generics)
                if getattr(self, '_skip_outer_gt', False):
                    self._skip_outer_gt = False
                    return node  # Our > was already consumed by inner >>
                if not self.match(TT.COMMA):
                    break
            # Handle >>: it closes two nested generics at once
            if self.current().type == TT.RSHIFT:
                self.advance()
                self._skip_outer_gt = True
            else:
                self.expect(TT.GT)
        # Generic with []: List[Int], Map[String, Int]
        if self.match(TT.LBRACKET):
            while not self.check(TT.RBRACKET):
                node.params.append(self.parse_type())
                if not self.match(TT.COMMA):
                    break
            self.expect(TT.RBRACKET)
        return node

    # ── Expressions (Full Operator Precedence) ───────────
    # Precedence (low → high):
    #   || → && → | → ^ → & → == != < > <= >= → + - → * / % → ** → unary → postfix

    def parse_expr(self) -> ASTNode:
        # Ternary-Ausdruck: if COND then A else B  (nicht zu verwechseln mit
        # dem Statement 'if COND { ... }' -- hier folgt kein '{' sondern 'then')
        if self.check(TT.KEYWORD, 'if') and self.peek().type not in (TT.LBRACE,):
            save = self.pos
            tok = self.advance()
            self._no_struct_literal += 1
            try:
                cond = self.parse_logical_or()
            finally:
                self._no_struct_literal -= 1
            if self.check(TT.KEYWORD, 'then'):
                self.advance()
                then_expr = self.parse_expr()
                self.expect(TT.KEYWORD, 'else')
                else_expr = self.parse_expr()
                return TernaryExpr(cond, then_expr, else_expr, tok.line, tok.col)
            # Kein 'then' -- kein Ternary, zuruecksetzen (z.B. normales if-Statement
            # taucht hier normalerweise nicht auf, da parse_expr nur fuer Ausdruecke
            # aufgerufen wird, aber sicherheitshalber zuruecksetzen)
            self.pos = save
        expr = self.parse_logical_or()
        # Python-Stil Ternary (Postfix): EXPR if COND else EXPR2
        # WICHTIG: nur wenn 'if' auf derselben Quellzeile wie das Ende von expr
        # steht -- sonst wird ein neues, separates if-Statement in der naechsten
        # Zeile faelschlich als Teil des Ternarys verschluckt (NEWLINE-Tokens
        # werden vom Lexer/Parser nicht als Statement-Trenner gehalten).
        prev_line = self.tokens[self.pos - 1].line if self.pos > 0 else -1
        if self.check(TT.KEYWORD, 'if') and self.current().line == prev_line:
            self.advance()
            self._no_struct_literal += 1
            try:
                cond = self.parse_logical_or()
            finally:
                self._no_struct_literal -= 1
            self.expect(TT.KEYWORD, 'else')
            else_expr = self.parse_expr()
            return TernaryExpr(cond, expr, else_expr, expr.line, expr.col)
        return expr

    def parse_logical_or(self) -> ASTNode:
        left = self.parse_logical_and()
        while self.current().type == TT.OR or self.check(TT.KEYWORD, 'or'):
            self.advance()
            right = self.parse_logical_and()
            left = BinaryOp(left, '||', right, left.line, left.col)
        return left

    def parse_logical_and(self) -> ASTNode:
        left = self.parse_bitwise_or()
        while self.current().type == TT.AND or self.check(TT.KEYWORD, 'and'):
            self.advance()
            right = self.parse_bitwise_or()
            left = BinaryOp(left, '&&', right, left.line, left.col)
        return left

    def parse_bitwise_or(self) -> ASTNode:
        left = self.parse_bitwise_xor()
        while self.current().type == TT.PIPE:
            op = self.advance().value
            right = self.parse_bitwise_xor()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_bitwise_xor(self) -> ASTNode:
        left = self.parse_bitwise_and()
        while self.current().type == TT.CARET:
            op = self.advance().value
            right = self.parse_bitwise_and()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_bitwise_and(self) -> ASTNode:
        left = self.parse_shift()
        while self.current().type == TT.AMP:
            op = self.advance().value
            right = self.parse_shift()
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_shift(self) -> ASTNode:
        left = self.parse_comparison()
        while self.current().type in (TT.LSHIFT, TT.RSHIFT):
            op = '<<' if self.current().type == TT.LSHIFT else '>>'
            self.advance()
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
            if self.current().type == TT.PLUS and self.peek().type == TT.PLUS:
                self.advance(); self.advance()  # consume both +
                right = self.parse_multiplication()
                left = BinaryOp(left, '++', right, left.line, left.col)
            else:
                op    = self.advance().value
                right = self.parse_multiplication()
                left  = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_multiplication(self) -> ASTNode:
        left = self.parse_power()
        while self.current().type in (TT.STAR, TT.SLASH, TT.PERCENT):
            op    = self.advance().value
            right = self.parse_power()
            left  = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_power(self) -> ASTNode:
        left = self.parse_unary()
        if self.current().type == TT.STARSTAR:
            op = self.advance().value
            right = self.parse_power()  # right-associative
            left = BinaryOp(left, op, right, left.line, left.col)
        return left

    def parse_unary(self) -> ASTNode:
        if self.check(TT.AMP):
            tok = self.advance()
            if self.check(TT.KEYWORD, 'mut') or (self.check(TT.IDENT) and self.current().value == 'mut'):
                self.advance()
            return UnaryOp('&', self.parse_unary(), tok.line, tok.col)
        if self.current().type == TT.MINUS:
            tok = self.advance()
            return UnaryOp('-', self.parse_unary(), tok.line, tok.col)
        if self.current().type == TT.TILDE:
            tok = self.advance()
            return UnaryOp('~', self.parse_unary(), tok.line, tok.col)
        if self.current().type == TT.AND and self.peek().type == TT.KEYWORD and self.peek().value == 'not':
            # 'and not' — skip, handled by logical_and
            pass
        if self.current().type == TT.NOT:
            tok = self.advance()
            return UnaryOp('!', self.parse_unary(), tok.line, tok.col)
        if self.check(TT.KEYWORD, 'not'):
            tok = self.advance()
            return UnaryOp('!', self.parse_unary(), tok.line, tok.col)
        if self.check(TT.KEYWORD, 'true') or self.check(TT.KEYWORD, 'false'):
            tok = self.advance()
            return BoolLiteral(tok.value == 'true', tok.line, tok.col)
        return self.parse_postfix()

    def parse_postfix(self) -> ASTNode:
        node = self.parse_primary()
        while True:
            if self.check(TT.KEYWORD, 'as'):
                self.advance()
                target_type = self.parse_type()
                node = CastExpr(node, target_type, node.line, node.col)
                continue
            if self.match(TT.LBRACKET):
                # Handle slice: [start:end], [:end], [start:]
                from atclang.parser.ast_nodes import SliceExpr
                if self.check(TT.COLON) or self.check(TT.DOTDOT):
                    self.advance()
                    if self.check(TT.RBRACKET):
                        self.advance()
                        idx = SliceExpr(None, None)
                    else:
                        end = self.parse_expr()
                        self.expect(TT.RBRACKET)
                        idx = SliceExpr(None, end)
                else:
                    idx = self.parse_expr()
                    if self.check(TT.COLON) or self.check(TT.DOTDOT):
                        self.advance()
                        if self.check(TT.RBRACKET):
                            self.advance()
                            idx = SliceExpr(idx, None)
                        else:
                            end = self.parse_expr()
                            self.expect(TT.RBRACKET)
                            idx = SliceExpr(idx, end)
                    else:
                        self.expect(TT.RBRACKET)
                node = IndexAccess(node, idx, node.line, node.col)
            elif self.match(TT.DOT):
                # Accept both IDENT and KEYWORD after dot (obj.stake, obj.transfer)
                if self.current().type == TT.IDENT or self.current().type == TT.KEYWORD:
                    field_tok = self.advance()
                elif self.current().type in (TT.INT, TT.HEX_INT, TT.OCTAL_INT, TT.BIN_INT):
                    # Tuple numeric field access: b.0, b.1 (Rust-style)
                    field_tok = self.advance()
                else:
                    field_tok = self.expect(TT.IDENT)
                # Turbofish: method::<T>() — consume ::<Type> and discard
                if self.check(TT.DCOLON) and self.peek().type == TT.LT:
                    self.advance()  # ::
                    self.advance()  # <
                    depth = 1
                    while depth > 0 and not self.check(TT.EOF):
                        if self.current().type == getattr(TT, 'RSHIFT', None):
                            depth -= 2
                        elif self.check(TT.LT):
                            depth += 1
                        elif self.check(TT.GT):
                            depth -= 1
                        self.advance()
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

        if self.check(TT.KEYWORD, 'match'):
            return self.parse_match()

        # Closure/Lambda: |a, b| expr  (Rust-Stil, z.B. sort_by(|a, b| ...))
        if self.check(TT.PIPE):
            self.advance()
            params = []
            while not self.check(TT.PIPE):
                if self.check(TT.LPAREN):
                    # Tuple pattern: |(id, _)| or |(a, b)|
                    self.advance()
                    while not self.check(TT.RPAREN) and not self.check(TT.EOF):
                        if self.current().type in (TT.IDENT, TT.KEYWORD):
                            params.append(self.advance().value)
                        else:
                            self.advance()  # skip _, etc.
                    self.expect(TT.RPAREN)
                elif self.current().type in (TT.IDENT, TT.KEYWORD):
                    params.append(self.advance().value)
                if not self.match(TT.COMMA): break
            self.expect(TT.PIPE)
            if self.check(TT.LBRACE):
                self.advance()
                body = self.parse_block()
            else:
                body = self.parse_expr()
            return LambdaExpr(params, body, tok.line, tok.col)

        # Closure/Lambda: fn a, b => expr  ODER  fn(a, b) => expr  (nur als
        # Ausdruck, z.B. als Callback-Argument .sort(fn a, b => ...))
        if self.check(TT.KEYWORD, 'fn') and self.peek().type != TT.LBRACE:
            save = self.pos
            self.advance()
            params = []
            if self.match(TT.LPAREN):
                while not self.check(TT.RPAREN):
                    if self.current().type in (TT.IDENT, TT.KEYWORD):
                        params.append(self.advance().value)
                        if self.match(TT.COLON):
                            self.parse_type()  # optionale Typannotation verwerfen
                    if not self.match(TT.COMMA): break
                self.expect(TT.RPAREN)
            else:
                while self.current().type in (TT.IDENT, TT.KEYWORD) and self.current().value != 'fn':
                    params.append(self.advance().value)
                    if not self.match(TT.COMMA): break
            # Optionaler Rueckgabetyp: fn(x: Int) -> Bool { ... }
            if self.match(TT.ARROW):
                self.parse_type()  # Rueckgabetyp verwerfen (kein Typsystem im Interpreter)
            if self.match(TT.FAT_ARROW):
                body = self.parse_expr()
                return LambdaExpr(params, body, tok.line, tok.col)
            if self.check(TT.LBRACE):
                self.advance()
                block = self.parse_block()
                return LambdaExpr(params, block, tok.line, tok.col)
            self.pos = save

        if tok.type in (TT.INT, TT.HEX_INT, TT.OCTAL_INT, TT.BIN_INT):
            self.advance()
            # Typed integer literal: 0u32, 1i64, 0u8, etc. — consume type suffix
            _type_suffixes = {'u8','u16','u32','u64','usize','i8','i16','i32','i64','isize','f32','f64'}
            if self.check(TT.IDENT) and self.current().value in _type_suffixes:
                self.advance()
            if tok.type == TT.HEX_INT:
                return IntLiteral(tok.value, tok.line, tok.col)
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

        # map { k => v } syntax — must be before IDENT branch
        if tok.type == TT.IDENT and tok.value == 'map' and self.peek().type == TT.LBRACE:
            self.advance()
            self.advance()
            pairs = []
            while not self.check(TT.RBRACE):
                if self.check(TT.EOF): break
                k = self.parse_expr()
                if self.match(TT.FAT_ARROW):
                    v = self.parse_expr()
                elif self.match(TT.COLON):
                    v = self.parse_expr()
                else:
                    v = self.parse_expr()
                pairs.append((k, v))
                if not self.match(TT.COMMA): break
            self.expect(TT.RBRACE)
            return MapLiteral(pairs, tok.line, tok.col)

        # Namespace: ATC::Wallet::new
        # TYPE tokens used as identifiers (e.g., Process, FileHandle in expressions)
        if tok.type == TT.TYPE:
            self.advance()
            # Namespace: Vec::new(), Type::method()
            if self.check(TT.DCOLON):
                _reserved = {'let', 'const', 'if', 'else', 'elif', 'for', 'while',
                             'return', 'break', 'continue', 'fn', 'struct', 'enum',
                             'contract', 'trait', 'emit', 'require', 'import',
                             'use', 'match', 'module', 'interface'}
                parts = [tok.value]
                while self.check(TT.DCOLON):
                    self.advance()
                    if self.current().type == TT.KEYWORD and self.current().value not in _reserved:
                        parts.append(self.advance().value)
                    elif self.current().type in (TT.IDENT, TT.TYPE):
                        parts.append(self.advance().value)
                    else:
                        parts.append(self.expect(TT.IDENT).value)
                # Check for struct literal after qualified path: Type::Variant { ... }
                if self.check(TT.LBRACE) and not self._no_struct_literal:
                    last = parts[-1]
                    if last and last[0].isupper():
                        self.advance()
                        fields = []
                        while not self.check(TT.RBRACE):
                            if self.check(TT.EOF): break
                            fname = self.current()
                            if fname.type in (TT.IDENT, TT.KEYWORD, TT.TYPE):
                                self.advance()
                            else:
                                self.expect(TT.IDENT)
                            if self.match(TT.COLON):
                                fval = self.parse_expr()
                            else:
                                from atclang.parser.ast_nodes import Identifier as _Ident
                                fval = _Ident(fname.value, fname.line, fname.col)
                            fields.append((fname.value, fval))
                            if not self.match(TT.COMMA): break
                        self.expect(TT.RBRACE)
                        return StructLiteral(struct_name="::".join(parts), fields=fields, line=tok.line, col=tok.col)
                return NamespaceAccess(parts, tok.line, tok.col)
            # Check for struct literal: TypeName { field: value }
            if self.check(TT.LBRACE) and not self._no_struct_literal:
                self.advance()
                fields = []
                while not self.check(TT.RBRACE):
                    if self.check(TT.EOF): break
                    fname = self.current()
                    if fname.type in (TT.IDENT, TT.KEYWORD, TT.TYPE):
                        self.advance()
                    else:
                        self.expect(TT.IDENT)
                    if self.match(TT.COLON) or self.match(TT.EQ):
                        fval = self.parse_expr()
                    else:
                        # Shorthand-Feld: { project_id } == { project_id: project_id }
                        from atclang.parser.ast_nodes import Identifier as _Ident
                        fval = _Ident(fname.value, fname.line, fname.col)
                    fields.append((fname.value, fval))
                    if not self.match(TT.COMMA): break
                self.expect(TT.RBRACE)
                return StructLiteral(struct_name=tok.value, fields=fields, line=tok.line, col=tok.col)
            return Identifier(tok.value, tok.line, tok.col)

        # Rust-artige Makros: name!(...) oder name![...]
        # - vec![a, b] / [...] -> Listenliteral
        # - format!(...), assert!(...), println!(...) etc. -> normaler Funktionsaufruf
        #   (das '!' wird einfach verworfen, Postfix-Parser haengt '(' danach an)
        if tok.type == TT.IDENT and self.peek().type == TT.NOT:
            if self.peek(2).type == TT.LBRACKET if hasattr(self, 'peek') else False:
                pass
            nxt2 = self.tokens[self.pos + 2] if self.pos + 2 < len(self.tokens) else None
            if nxt2 is not None and nxt2.type == TT.LBRACKET:
                self.advance()  # name
                self.advance()  # !
                self.expect(TT.LBRACKET)
                elements = []
                while not self.check(TT.RBRACKET):
                    if self.check(TT.EOF): break
                    elements.append(self.parse_expr())
                    if not self.match(TT.COMMA): break
                self.expect(TT.RBRACKET)
                return ListLiteral(elements, tok.line, tok.col)
            elif nxt2 is not None and nxt2.type == TT.LPAREN:
                self.advance()  # name
                self.advance()  # !
                return Identifier(tok.value, tok.line, tok.col)

        if tok.type == TT.IDENT:
            parts = [tok.value]
            self.advance()
            while self.check(TT.DCOLON):
                self.advance()
                if self.current().type in (TT.IDENT, TT.KEYWORD, TT.TYPE):
                    parts.append(self.advance().value)
                else:
                    parts.append(self.expect(TT.IDENT).value)
            if len(parts) > 1:
                node = NamespaceAccess(parts, tok.line, tok.col)
            else:
                node = Identifier(parts[0], tok.line, tok.col)
            # Struct literal: Foo { field: value, ... } — for PascalCase OR all-uppercase names
            # Also: Path::Type { ... } when last part starts uppercase
            _last = parts[-1] if parts else ''
            _is_struct_name = (_last and _last[0].isupper())  # PascalCase or ALL_UPPER
            if (self.check(TT.LBRACE) and _is_struct_name
                    and not self._no_struct_literal):
                self.advance()
                fields = []
                while not self.check(TT.RBRACE):
                    if self.check(TT.EOF): break
                    fname = self.current()
                    if fname.type in (TT.IDENT, TT.KEYWORD, TT.TYPE):
                        self.advance()
                    else:
                        self.expect(TT.IDENT)
                    if self.match(TT.COLON) or self.match(TT.EQ):
                        fval = self.parse_expr()
                    else:
                        from atclang.parser.ast_nodes import Identifier as _Ident
                        fval = _Ident(fname.value, fname.line, fname.col)
                    fields.append((fname.value, fval))
                    if not self.match(TT.COMMA): break
                self.expect(TT.RBRACE)
                return StructLiteral(struct_name="::".join(parts), fields=fields, line=tok.line, col=tok.col)
            return node

        if tok.type == TT.LPAREN:
            self.advance()
            if self.check(TT.RPAREN):
                self.advance()
                return NullLiteral(tok.line, tok.col)
            expr = self.parse_expr()
            # Tuple expression: (a, b, c)
            if self.check(TT.COMMA):
                values = [expr]
                while self.match(TT.COMMA):
                    if self.check(TT.RPAREN):
                        break  # trailing comma
                    values.append(self.parse_expr())
                self.expect(TT.RPAREN)
                from atclang.parser.ast_nodes import TupleExpr
                return TupleExpr(values)
            self.expect(TT.RPAREN)
            return expr

        # ATC Stdlib namespace: ATC::Crypto::sha256(...)
        if tok.type == TT.ATC_STD:
            self.advance()
            parts = tok.value.split("::")
            return NamespaceAccess(parts, tok.line, tok.col)

        # Kontextuelle Keywords als Identifier: most keywords can be variable names
        # EXCEPT control-flow keywords that start statements
        _reserved_as_stmt = {'let', 'const', 'if', 'else', 'elif', 'for', 'while',
                             'return', 'break', 'continue', 'fn', 'struct', 'enum',
                             'contract', 'trait', 'emit', 'require', 'import',
                             'use', 'match'}
        if tok.type == TT.KEYWORD and tok.value not in _reserved_as_stmt:
            self.advance()
            return Identifier(tok.value, tok.line, tok.col)

        # List literal: [1, 2, 3] or []
        if tok.type == TT.LBRACKET:
            self.advance()
            elements = []
            while not self.check(TT.RBRACKET):
                if self.check(TT.EOF): break
                elements.append(self.parse_expr())
                if not self.match(TT.COMMA): break
            self.expect(TT.RBRACKET)
            return ListLiteral(elements, tok.line, tok.col)

        # Map literal: {"key": "value"} or {} -- oder Shorthand {ident}
        if tok.type == TT.LBRACE:
            self.advance()
            pairs = []
            while not self.check(TT.RBRACE):
                if self.check(TT.EOF): break
                key = self.parse_expr()
                if self.match(TT.COLON):
                    val = self.parse_expr()
                else:
                    val = key  # Shorthand: {universe_id} == {universe_id: universe_id}
                pairs.append((key, val))
                if not self.match(TT.COMMA): break
            self.expect(TT.RBRACE)
            return MapLiteral(pairs, tok.line, tok.col)

        # If-expression: if cond { val } else { val }
        if tok.type == TT.KEYWORD and tok.value == 'if':
            return self.parse_if()
        
        self.error(f"Unerwartetes Token in Ausdruck: {tok.type.name}='{tok.value}'"  )


    def parse_match(self) -> 'MatchStatement':
        tok = self.advance()  # 'match'
        subject = self.parse_expr()
        self.advance()  # consume LBRACE
        arms = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            # Pattern: can be INT, STRING, IDENT, TYPE, or underscore (_)
            if self.check(TT.IDENT) and self.current().value == '_':
                self.advance()
                pattern = None  # wildcard
            elif self.current().type in (TT.INT, TT.STRING, TT.IDENT, TT.TYPE, TT.KEYWORD):
                pattern = self.advance().value
            else:
                pattern = self.advance().value
            self.expect(TT.FATARROW)
            # Arm body: single expression or block
            if self.check(TT.LBRACE):
                self.advance()
                body = self.parse_block()
            else:
                body = [self.parse_statement()]
            arms.append((pattern, body))
            if self.check(TT.COMMA): self.advance()
        self.expect(TT.RBRACE)
        from atclang.parser.ast_nodes import MatchStatement
        return MatchStatement(subject, arms, tok.line, tok.col)


    def parse_match(self):
        tok = self.advance()  # 'match'
        subject = self.parse_expr()
        self.advance()  # consume LBRACE
        arms = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            # Pattern: INT, STRING, IDENT, TYPE, KEYWORD, or wildcard '_'
            if self.current().type == TT.IDENT and self.current().value == '_':
                self.advance()
                pattern = None
            else:
                # Pattern can be: literal, Enum::Variant, or identifier
                # Also supports or-patterns: A | B | C
                patterns = []
                pattern_parts = [str(self.advance().value)]
                while self.check(TT.DCOLON):
                    self.advance()
                    pattern_parts.append(str(self.advance().value))
                patterns.append('::'.join(pattern_parts))
                # Or-pattern: pat1 | pat2
                while self.check(TT.PIPE):
                    self.advance()
                    p2 = [str(self.advance().value)]
                    while self.check(TT.DCOLON):
                        self.advance()
                        p2.append(str(self.advance().value))
                    patterns.append('::'.join(p2))
                pattern = ' | '.join(patterns)
            self.expect(TT.FAT_ARROW)
            if self.check(TT.LBRACE):
                self.advance()
                body = self.parse_block()
            else:
                body = [self.parse_statement()]
            arms.append((pattern, body))
            if self.check(TT.COMMA): self.advance()
        self.expect(TT.RBRACE)
        from atclang.parser.ast_nodes import MatchStatement
        return MatchStatement(subject, arms, tok.line, tok.col)

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
        if self.check(TT.KEYWORD, 'match'):
            return self.parse_match()
        if self.check(TT.KEYWORD, 'break'):
            self.advance(); return BreakStatement(tok.line, tok.col)
        if self.check(TT.KEYWORD, 'continue'):
            self.advance(); return ContinueStatement(tok.line, tok.col)

        # Compound assignment (x += y, x -= y, x *= y, x /= y)
        if self.peek().type in (TT.PLUSEQ, TT.MINUSEQ, TT.STAREQ, TT.SLASHEQ, TT.OREQ, TT.AMPEQ):
            target_tok = self.advance()
            op_tok = self.advance()  # +=, -=, *=, /=
            val = self.parse_expr()
            from atclang.parser.ast_nodes import Identifier
            target_id = Identifier(target_tok.value, target_tok.line, target_tok.col)
            compound = BinaryOp(target_id, op_tok.value[0], val, target_tok.line, target_tok.col)
            return Assignment(target=target_id, value=compound, line=target_tok.line, col=target_tok.col)
        # Zuweisung oder Ausdruck
        expr = self.parse_expr()
        if self.match(TT.EQ):
            value = self.parse_expr()
            self.match(TT.SEMICOLON)
            return Assignment(expr, value, expr.line, expr.col)
        # Compound assignment: x += y, x -= y, etc.
        if self.current().type in (TT.PLUSEQ, TT.MINUSEQ, TT.STAREQ, TT.SLASHEQ, TT.OREQ, TT.AMPEQ):
            op_tok = self.advance()
            val = self.parse_expr()
            compound = BinaryOp(expr, op_tok.value[0], val, expr.line, expr.col)
            return Assignment(expr, compound, expr.line, expr.col)
        self.match(TT.SEMICOLON)
        return ExprStatement(expr, expr.line, expr.col)

    def parse_let(self) -> LetStatement:
        tok      = self.advance()
        is_const = tok.value == 'const'
        # Handle tuple destructuring: let (a, b) = expr
        if self.check(TT.LPAREN):
            self.advance()
            names = []
            while not self.check(TT.RPAREN):
                if self.current().type in (TT.IDENT, TT.KEYWORD):
                    names.append(self.advance().value)
                else:
                    names.append(self.expect(TT.IDENT).value)
                if not self.match(TT.COMMA): break
            self.expect(TT.RPAREN)
            # No type hint for tuple destructuring
            value = None
            if self.match(TT.EQ):
                value = self.parse_expr()
            self.match(TT.SEMICOLON)
            # Return with tuple names joined
            from atclang.parser.ast_nodes import TupleExpr
            name = "(" + ", ".join(names) + ")"
            return LetStatement(name, None, value, is_const, tok.line, tok.col)
        # Skip 'mut' keyword (mutable binding, e.g. let mut x = ...)
        if (self.check(TT.KEYWORD, 'mut') or
            (self.check(TT.IDENT) and self.current().value == 'mut')):
            self.advance()
        if self.current().type in (TT.IDENT, TT.KEYWORD):
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
        if self.check(TT.RBRACE) or self.check(TT.EOF) or self.check(TT.SEMICOLON):
            if self.check(TT.SEMICOLON):
                self.advance()
            return ReturnStatement(None, tok.line, tok.col)
        # parse_expr handles both tuple (a, b) and grouped (a) / b naturally
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
        if self.match(TT.LPAREN):
            cond = self.parse_expr()
            msg  = None
            if self.match(TT.COMMA):
                msg = self.parse_expr()
            self.expect(TT.RPAREN)
        else:
            cond = self.parse_expr()
            msg  = None
        return RequireStatement(cond, msg, tok.line, tok.col)


    def parse_if(self) -> IfStatement:
        tok  = self.advance()
        # if let Pattern = expr { ... }
        if self.check(TT.KEYWORD, 'let'):
            self.advance()
            # Consume pattern: Some(var) or var
            if self.current().type in (TT.IDENT, TT.TYPE):
                self.advance()
                if self.check(TT.LPAREN):
                    self.advance()
                    while not self.check(TT.RPAREN) and not self.check(TT.EOF):
                        self.advance()
                    self.expect(TT.RPAREN)
            self.expect(TT.EQ)
            self._no_struct_literal += 1
            try:
                cond = self.parse_expr()
            finally:
                self._no_struct_literal -= 1
        else:
            self._no_struct_literal += 1
            try:
                cond = self.parse_expr()
            finally:
                self._no_struct_literal -= 1
        self.advance()  # consume LBRACE
        then = self.parse_block()
        elif_blocks = []
        else_block  = None
        while self.check(TT.KEYWORD, 'elif'):
            self.advance()
            self._no_struct_literal += 1
            try:
                ec = self.parse_expr()
            finally:
                self._no_struct_literal -= 1
            self.advance()  # consume LBRACE
            eb = self.parse_block()
            elif_blocks.append((ec, eb))
        if self.check(TT.KEYWORD, 'else'):
            self.advance()
            if self.check(TT.KEYWORD, 'if'):
                # "else if" → treat as nested elif
                inner = self.parse_if()  # returns IfStatement
                elif_blocks.append((inner.condition, inner.then_block))
                for ec, eb in inner.elif_blocks:
                    elif_blocks.append((ec, eb))
                else_block = inner.else_block
            else:
                self.advance()  # consume LBRACE
                else_block = self.parse_block()
        return IfStatement(condition=cond, then_block=then, elif_blocks=elif_blocks, else_block=else_block, line=tok.line, col=tok.col)

    def parse_for(self) -> ForStatement:
        tok = self.advance()
        # Tuple-Destrukturierung: for (id, tl) in map { ... }
        if self.check(TT.LPAREN):
            self.advance()
            names = []
            while not self.check(TT.RPAREN):
                names.append(self.expect(TT.IDENT).value if self.current().type not in (TT.IDENT, TT.KEYWORD) else self.advance().value)
                if not self.match(TT.COMMA): break
            self.expect(TT.RPAREN)
            var = names
        elif self.current().type in (TT.IDENT, TT.KEYWORD):
            # Check for comma-separated: for id, display in map
            names = [self.advance().value]
            while self.check(TT.COMMA):
                self.advance()
                if self.current().type in (TT.IDENT, TT.KEYWORD):
                    names.append(self.advance().value)
                else:
                    break
            if len(names) > 1:
                var = names
            else:
                var = names[0]
        else:
            var = self.expect(TT.IDENT).value
        if self.check(TT.KEYWORD, 'in'):
            self.advance()
        elif self.check(TT.IDENT) and self.current().value == 'in':
            self.advance()
        else:
            self.expect(TT.KEYWORD, 'in')
        self._no_struct_literal += 1
        try:
            iterable = self.parse_expr()
        finally:
            self._no_struct_literal -= 1
        # Range: 1..N [step S]  or  1..=N (inclusive)
        if self.current().type == TT.DOTDOT or self.current().type == getattr(TT, 'DOTDOTEQ', TT.DOTDOT):
            self.advance()
            end = self.parse_expr()
            from atclang.parser.ast_nodes import RangeExpr
            step = None
            if self.check(TT.KEYWORD, 'step'):
                self.advance()
                step = self.parse_expr()
            iterable = RangeExpr(iterable, end, step)
        self.advance()  # consume LBRACE
        body = self.parse_block()
        return ForStatement(var, iterable, body, tok.line, tok.col)

    def parse_while(self) -> WhileStatement:
        tok  = self.advance()
        self._no_struct_literal += 1
        try:
            cond = self.parse_expr()
        finally:
            self._no_struct_literal -= 1
        self.advance()  # consume LBRACE
        body = self.parse_block()
        return WhileStatement(cond, body, tok.line, tok.col)

    def parse_block(self) -> List[ASTNode]:
        stmts = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            # Leere Anweisungen / lose Semikolons zwischen Statements ueberspringen
            # (mehrere Statements auf einer Zeile: 'require(x); foo(); return y')
            while self.match(TT.SEMICOLON):
                pass
            if self.check(TT.RBRACE) or self.check(TT.EOF):
                break
            stmts.append(self.parse_statement())
        self.expect(TT.RBRACE)
        return stmts

    def parse_param(self) -> Parameter:
        if self.current().type in (TT.IDENT, TT.KEYWORD, TT.TYPE):
            name = self.advance().value
        else:
            self.error(f"Erwartet IDENT für Parametername")
        # Untypisierter Parameter (dynamisch, z.B. 'fn foo(f, name, dt)') --
        # kein ':' vorhanden -> impliziter 'Any'-Typ statt Fehler
        if not self.check(TT.COLON):
            return Parameter(name, TypeAnnotation('Any', []))
        self.expect(TT.COLON)
        typ  = self.parse_type()
        return Parameter(name, typ)

    def parse_function(self) -> FunctionDef:
        tok    = self.advance()  # 'fn'
        # Function name can be IDENT or KEYWORD (transfer, mint, burn, stake, etc.)
        if self.current().type in (TT.IDENT, TT.KEYWORD):
            name = self.advance().value
        else:
            self.error(f"Erwartet IDENT für Funktionsname")
        # Generische Typ-Parameter: fn get_bus<T>(...) -- geparst und verworfen
        if self.check(TT.LT):
            self.advance()
            while not self.check(TT.GT):
                if self.check(TT.EOF): break
                self.advance()
            self.match(TT.GT)
        self.expect(TT.LPAREN)
        params = []
        while not self.check(TT.RPAREN):
            params.append(self.parse_param())
            if not self.match(TT.COMMA): break
        self.expect(TT.RPAREN)
        ret_type = None
        if self.match(TT.ARROW):
            # Handle tuple return type: (A, B)
            if self.check(TT.LPAREN):
                self.advance()
                types = [self.parse_type()]
                while self.match(TT.COMMA):
                    types.append(self.parse_type())
                self.expect(TT.RPAREN)
                ret_type = TypeAnnotation('Tuple', types)
            else:
                ret_type = self.parse_type()
        if self.check(TT.LBRACE):
            self.advance()  # consume LBRACE
            body = self.parse_block()
        else:
            body = []  # Abstract/trait method — no body
        return FunctionDef(name, params, ret_type, body, False, [], tok.line, tok.col)

    def parse_contract(self, keyword_type: str = 'contract') -> ContractDef:
        tok  = self.advance()  # 'contract' or 'trait'
        # Accept both IDENT and TYPE as contract names
        if self.current().type in (TT.IDENT, TT.TYPE):
            name = self.advance().value
        else:
            name = self.expect(TT.IDENT).value
        standards = []
        if self.match(TT.COLON):
            std_parts = []
            while not self.check(TT.LBRACE) and not self.check(TT.EOF):
                std_parts.append(str(self.advance().value))
            if std_parts:
                standards.append("".join(std_parts))
        self.expect(TT.LBRACE)
        states, events, errors, functions = [], [], [], []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            if self.check(TT.KEYWORD, 'state'):
                self.advance()
                if self.current().type in (TT.IDENT, TT.KEYWORD):
                    fname = self.advance().value
                else:
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
                        # Event params can be type-only: event Transfer(String, String, Int)
                        # or named: event Transfer(from: String, to: String, amount: Int)
                        if self.current().type in (TT.TYPE, TT.IDENT, TT.KEYWORD) and self.peek() and self.peek().type == TT.COLON:
                            # Named param: name: Type
                            params.append(self.parse_param())
                        else:
                            # Type-only param
                            typ = self.parse_type()
                            params.append(Parameter("", typ))
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

    def parse_struct(self) -> StructDef:
        tok = self.advance()  # 'struct'
        # Accept both IDENT and TYPE as struct names (PascalCase types)
        if self.current().type in (TT.IDENT, TT.TYPE):
            name = self.advance().value
        else:
            name = self.expect(TT.IDENT).value
        # Generische Typ-Parameter: struct Query<T> { ... } -- werden geparst
        # und verworfen (kein generisches Typsystem im Interpreter noetig)
        if self.check(TT.LT):
            self.advance()
            while not self.check(TT.GT):
                if self.check(TT.EOF): break
                self.advance()
            self.match(TT.GT)
        self.expect(TT.LBRACE)
        fields = []
        while not self.check(TT.RBRACE):
            if self.check(TT.EOF): break
            # Accept both IDENT and KEYWORD as field names (stake, transfer, etc.)
            if self.current().type == TT.IDENT or self.current().type == TT.KEYWORD:
                field_name = self.advance().value
            else:
                field_name = self.expect(TT.IDENT).value
            if not self.match(TT.COLON):
                self.expect(TT.EQ)  # Alternative Syntax: field = Type
            field_type = self.parse_type()
            fields.append((field_name, field_type))
            if self.check(TT.COMMA): self.advance()
        self.expect(TT.RBRACE)
        return StructDef(name, fields, tok.line, tok.col)

    def parse_enum(self) -> EnumDef:
        tok = self.advance()  # 'enum'
        # Accept both IDENT and TYPE as enum names
        if self.current().type in (TT.IDENT, TT.TYPE):
            name = self.advance().value
        else:
            name = self.expect(TT.IDENT).value
        self.expect(TT.LBRACE)
        variants = []
        while not self.check(TT.RBRACE):
            if self.check(TT.EOF): break
            variants.append(self.expect(TT.IDENT).value)
            # Allow explicit enum values: LOW = 1, HIGH = 10
            if self.check(TT.EQ):
                self.advance()
                # Skip the value expression (just consume it)
                self.parse_expr()
            if self.check(TT.COMMA): self.advance()
        self.expect(TT.RBRACE)
        return EnumDef(name, variants, tok.line, tok.col)

    # ── Top-Level ─────────────────────────────────────────
    def parse_module_block(self, prog: Program):
        """module GCL.EventBus[AD-01] { ... } -- Namespace-Wrapper.
        Wird zur Laufzeit als reine Gruppierung behandelt: Inhalt wird
        in dasselbe Program-Statement-Array wie Top-Level-Deklarationen
        eingehaengt (flach), der Modul-Name selbst hat aktuell keine
        semantische Wirkung (kein Scoping-AST-Node noetig fuer v0.3).
        """
        self.advance()  # 'module'
        # Gepunkteter Namespace-Pfad: MetaFactory.IPEvolutionEngine
        parts = [self.expect(TT.IDENT).value]
        while self.check(TT.DOT) or self.check(TT.DCOLON):
            self.advance()
            parts.append(self.expect(TT.IDENT).value)
        # Optionaler Standard-Tag: [AD-45]
        if self.check(TT.LBRACKET):
            self.advance()
            while not self.check(TT.RBRACKET) and not self.check(TT.EOF):
                self.advance()
            self.expect(TT.RBRACKET)
        self.expect(TT.LBRACE)
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            _pos_before = self.pos
            self.parse_top_level_stmt(prog)
            if self.pos == _pos_before:
                # Sicherheitsventil: unbekanntes Konstrukt im module{}-Block
                # (z.B. 'class X implements Y' -- noch nicht unterstuetzt) --
                # ein Token ueberspringen statt endlos zu haengen.
                self.advance()
        self.expect(TT.RBRACE)

    def parse_interface_block(self):
        """interface IFoo { fn bar(x: Int) -> Result<Y> ... } -- reine
        Methoden-Signaturen ohne Body. Wird geparst und verworfen (kein
        Codegen-Ziel fuer v0.3); parse_function unterstuetzt bereits
        koerperlose (abstrakte) Funktionen."""
        self.advance()  # 'interface'
        self.expect(TT.IDENT)  # Name
        self.expect(TT.LBRACE)
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            if self.check(TT.KEYWORD, 'fn'):
                self.parse_function()
            else:
                self.advance()
        self.expect(TT.RBRACE)

    def parse_top_level_stmt(self, prog: Program):
        """Parst genau EINE Top-Level-Deklaration (auch innerhalb eines
        module{}-Blocks wiederverwendbar) und haengt sie an prog.statements."""
        if self.current().type == TT.IDENT and self.current().value == 'module':
            self.parse_module_block(prog)
            return
        if self.check(TT.KEYWORD, 'interface'):
            self.parse_interface_block()
            return
        # class X implements Y { ... } — wie contract behandeln
        if self.current().type == TT.IDENT and self.current().value == 'class':
            prog.statements.append(self.parse_class())
            return
        # storage { field: Type, ... } — Storage-Block
        if self.current().type == TT.IDENT and self.current().value == 'storage' and self.peek() and self.peek().type == TT.LBRACE:
            prog.statements.append(self.parse_storage_block())
            return
        # type Set<T> = Any — Type-Alias
        if self.check(TT.KEYWORD, 'type'):
            prog.statements.append(self.parse_type_alias())
            return
        # Original-Dispatch unveraendert als verschachtelter Block wiederverwendet
        # (Einrueckung der Original-Zeilen bewusst NICHT angepasst, um Diff-Risiko
        # zu minimieren -- dieser Wrapper macht die alte 12/16-Space-Einrueckung
        # wieder gueltig):
        if True:
            if self.check(TT.KEYWORD, 'contract') or self.check(TT.KEYWORD, 'trait'):
                prog.statements.append(self.parse_contract())
            elif self.check(TT.KEYWORD, 'wallet'):
                tok  = self.advance()
                name = self.expect(TT.IDENT).value
                self.expect(TT.EQ)
                val  = self.parse_expr()
                prog.statements.append(WalletDef(name, val, tok.line, tok.col))
            elif self.check(TT.KEYWORD, 'fn'):
                prog.statements.append(self.parse_function())
            elif self.check(TT.KEYWORD, 'struct'):
                prog.statements.append(self.parse_struct())
            elif self.check(TT.KEYWORD, 'event'):
                self.advance()
                ename = self.expect(TT.IDENT).value
                params = []
                if self.match(TT.LPAREN):
                    while not self.check(TT.RPAREN):
                        if self.check(TT.EOF): break
                        pname = self.current()
                        if pname.type in (TT.IDENT, TT.KEYWORD, TT.TYPE):
                            self.advance()
                        else:
                            self.expect(TT.IDENT)
                        self.expect(TT.COLON)
                        typ = self.parse_type()
                        params.append(Parameter(pname.value, typ))
                        if not self.match(TT.COMMA): break
                    self.expect(TT.RPAREN)
                elif self.match(TT.LBRACE):
                    while not self.check(TT.RBRACE):
                        if self.check(TT.EOF): break
                        pname = self.current()
                        if pname.type in (TT.IDENT, TT.KEYWORD, TT.TYPE):
                            self.advance()
                        else:
                            self.expect(TT.IDENT)
                        self.expect(TT.COLON)
                        typ = self.parse_type()
                        params.append(Parameter(pname.value, typ))
                        if not self.match(TT.COMMA): break
                    self.expect(TT.RBRACE)
                prog.statements.append(EventDef(ename, params))
            elif self.check(TT.KEYWORD, 'enum'):
                prog.statements.append(self.parse_enum())
            elif self.check(TT.KEYWORD, 'let') or self.check(TT.KEYWORD, 'const'):
                prog.statements.append(self.parse_let())
            elif self.check(TT.KEYWORD, 'import') or self.check(TT.KEYWORD, 'use'):
                tok  = self.advance()
                # String-Pfad-Import: import "std/crypto.atc" as Crypto
                if self.current().type == TT.STRING:
                    str_path = self.advance().value
                    parts = [p for p in str_path.replace('.atc', '').split('/') if p]
                    alias = None
                    if self.check(TT.KEYWORD, 'as'):
                        self.advance()
                        alias = self.expect(TT.IDENT).value
                    prog.statements.append(ImportStatement(parts, alias, tok.line, tok.col))
                    return
                # Accept both IDENT and ATC_STD (e.g., "import ATC::Crypto")
                if self.current().type == TT.ATC_STD:
                    parts = [self.advance().value]
                else:
                    parts = [self.expect(TT.IDENT).value]
                # Gepunkteter Pfad mit optionalem Bracket-Tag: import GCL.Core[AD-00]
                while self.check(TT.DOT):
                    self.advance()
                    parts.append(self.expect(TT.IDENT).value)
                if self.check(TT.LBRACKET):
                    self.advance()
                    while not self.check(TT.RBRACKET):
                        if self.check(TT.EOF): break
                        self.advance()
                    self.expect(TT.RBRACKET)
                while self.match(TT.DCOLON):
                    if self.current().type == TT.KEYWORD and self.current().value in ('new', 'delete', 'deploy', 'call'):
                        parts.append(self.advance().value)
                    elif self.current().type == TT.ATC_STD:
                        parts.append(self.advance().value)
                    else:
                        parts.append(self.expect(TT.IDENT).value)
                # Selective import: use ATC::Crypto::{ sha256, hmac }
                imported_names = []
                if self.check(TT.LBRACE):
                    self.advance()
                    while not self.check(TT.RBRACE):
                        if self.check(TT.EOF): break
                        if self.current().type in (TT.IDENT, TT.TYPE, TT.KEYWORD):
                            imported_names.append(self.advance().value)
                        else:
                            imported_names.append(self.expect(TT.IDENT).value)
                        if not self.match(TT.COMMA): break
                    self.expect(TT.RBRACE)
                alias = None
                if self.check(TT.KEYWORD, 'as'):
                    self.advance()
                    alias = self.expect(TT.IDENT).value
                prog.statements.append(ImportStatement(parts, alias, tok.line, tok.col))
            else:
                prog.statements.append(self.parse_statement())
        else:
            prog.statements.append(self.parse_statement())


    def parse_class(self) -> 'ClassDef':
        """class X implements Y { ... } — wird wie ContractDef behandelt.
        class ist ein IDENT (kein Keyword), daher per value-Check erkannt."""
        tok = self.advance()  # 'class'
        if self.current().type in (TT.IDENT, TT.TYPE):
            name = self.advance().value
        else:
            name = self.expect(TT.IDENT).value
        implements = ""
        # implements IFoo (optional, kann auch mehrfach mit Komma)
        if self.current().type == TT.IDENT and self.current().value == 'implements':
            self.advance()
            impl_names = []
            while not self.check(TT.LBRACE) and not self.check(TT.EOF):
                impl_names.append(str(self.advance().value))
            implements = "".join(impl_names).strip()
        self.expect(TT.LBRACE)
        fields, functions = [], []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            _pos_before = self.pos
            # Field declaration: name: Type
            if (self.current().type in (TT.IDENT, TT.KEYWORD, TT.TYPE) and
                self.peek() and self.peek().type == TT.COLON):
                fname = self.advance().value
                self.expect(TT.COLON)
                ftype = self.parse_type()
                fields.append((fname, ftype))
                self.match(TT.COMMA)
                self.match(TT.SEMICOLON)
            elif self.check(TT.KEYWORD, 'fn'):
                functions.append(self.parse_function())
            else:
                # Try as top-level stmt (for nested constructs)
                self.parse_top_level_stmt(type('', (), {'statements': []})())
                if self.pos == _pos_before:
                    self.advance()
        self.expect(TT.RBRACE)
        from atclang.parser.ast_nodes import ClassDef
        return ClassDef(name=name, implements=implements, fields=fields,
                        functions=functions, line=tok.line, col=tok.col)

    def parse_storage_block(self) -> 'StorageBlock':
        """storage { field: Type, field2: Type2, ... } — Storage-Deklaration.
        Felder mit Komma oder Semikolon getrennt."""
        tok = self.advance()  # 'storage'
        self.expect(TT.LBRACE)
        fields = []
        while not self.check(TT.RBRACE) and not self.check(TT.EOF):
            if self.current().type in (TT.IDENT, TT.KEYWORD, TT.TYPE):
                fname = self.advance().value
            else:
                self.expect(TT.IDENT)
            self.expect(TT.COLON)
            ftype = self.parse_type()
            fields.append((fname, ftype))
            # Akzeptiere Komma ODER Semikolon als Trenner
            self.match(TT.COMMA)
            self.match(TT.SEMICOLON)
        self.expect(TT.RBRACE)
        from atclang.parser.ast_nodes import StorageBlock
        return StorageBlock(fields=fields, line=tok.line, col=tok.col)

    def parse_type_alias(self) -> 'TypeAliasDef':
        """type Set<T> = Any — Type-Alias Deklaration."""
        tok = self.advance()  # 'type'
        if self.current().type in (TT.IDENT, TT.TYPE):
            name = self.advance().value
        else:
            name = self.expect(TT.IDENT).value
        # Generische Typ-Parameter: <T, U>
        type_params = []
        if self.check(TT.LT):
            self.advance()
            while not self.check(TT.GT):
                if self.check(TT.EOF): break
                type_params.append(str(self.advance().value))
                if not self.match(TT.COMMA): break
            self.match(TT.GT)
        self.expect(TT.EQ)
        target = self.parse_type()
        self.match(TT.SEMICOLON)
        from atclang.parser.ast_nodes import TypeAliasDef
        return TypeAliasDef(name=name, type_params=type_params, target=target,
                           line=tok.line, col=tok.col)

    def parse_program(self) -> Program:
        prog = Program([], 1, 1)
        while not self.check(TT.EOF):
            _pos_before = self.pos
            self.parse_top_level_stmt(prog)
            if self.pos == _pos_before:
                # Sicherheitsventil: kein Token konsumiert -> unbekanntes
                # Top-Level-Konstrukt. Ein Token ueberspringen statt haengen.
                self.advance()
        return prog

    # Alias für Kompatibilität
    parse = parse_program


def parse(source: str) -> Program:
    """Hilfsfunktion: Quellcode → AST"""
    lexer  = ATCLexer(source)
    tokens = lexer.tokenize()
    parser = ATCParser(tokens)
    return parser.parse_program()
