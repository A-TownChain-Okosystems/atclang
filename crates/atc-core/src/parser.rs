// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Recursive-Descent-Parser — Canonical Core (SCR-0085, Fortschreibung SCR-0128
//! Stufe 1). Programm-Ebene = let/const/fn; Bloecke = let/return/if/else/while/
//! ExprStatement. Praezedenz: Vergleich (< == >) unter Addition, Addition unter
//! Multiplikation (linksassoziativ, keine Kurzschluss-Booleans).
//! Referenz-Semantiken bewusst uebernommen: Parameter MIT Pflicht-Typ,
//! 'return' nur ohne Semikolon vor '}' (return; wirft wie Referenz Fehler),
//! nackte Ausdruecke werden als ExprStatement gewrappt.

use crate::ast::{Expr, FunctionDef, LetStmt, Param, Program, Stmt, TypeHint};
use crate::lexer::{tokenize, Token};

#[derive(Debug, Clone, PartialEq)]
pub struct ParseError {
    pub message: String,
}

pub fn parse_program(src: &str) -> Result<Program, ParseError> {
    let toks = tokenize(src).map_err(|e| ParseError {
        message: format!("Lex-Fehler bei Position {}: {:?}", e.pos, e.ch),
    })?;
    let mut p = Parser { toks, pos: 0 };
    p.program()
}

struct Parser {
    toks: Vec<Token>,
    pos: usize,
}

impl Parser {
    fn cur(&self) -> Token {
        self.toks.get(self.pos).cloned().unwrap_or(Token::Eof)
    }

    fn program(&mut self) -> Result<Program, ParseError> {
        let mut statements = Vec::new();
        while self.cur() != Token::Eof {
            let s = match self.cur() {
                Token::Let | Token::Const => Stmt::Let(self.let_stmt()?),
                Token::Fn => Stmt::Fn(self.function()?),
                Token::Use => self.use_decl()?,
                Token::Struct => self.struct_decl()?,
                Token::Enum => self.enum_decl()?,
                Token::Contract => self.contract_decl()?,
                // File-level annotations (for example @version and @name) are
                // metadata, not executable statements. Consume them up to the
                // next recognized declaration without changing runtime semantics.
                Token::At => {
                    self.skip_file_annotations();
                    continue;
                }
                other => {
                    return Err(ParseError {
                        message: format!("Deklaration am Top-Level erwartet, fand {:?}", other),
                    })
                }
            };
            statements.push(s);
        }
        Ok(Program { statements })
    }

    fn simple_type(&mut self) -> Result<TypeHint, ParseError> {
        let mut name = match self.cur() {
            Token::Ident(n) => {
                self.pos += 1;
                n
            }
            other => {
                return Err(ParseError {
                    message: format!("Typ erwartet, fand {:?}", other),
                })
            }
        };

        // Preserve generic types such as Map<Address, Map<Address, u128>>.
        if self.cur() == Token::Lt {
            name.push('<');
            self.pos += 1;
            let mut depth = 1usize;
            while depth > 0 {
                let token = self.cur();
                if token == Token::Eof {
                    return Err(ParseError {
                        message: "Unvollständiger generischer Typ".to_string(),
                    });
                }
                self.pos += 1;
                match token {
                    Token::Lt => {
                        depth += 1;
                        name.push('<');
                    }
                    Token::Gt => {
                        depth -= 1;
                        name.push('>');
                    }
                    _ => name.push_str(&Self::token_text(&token)),
                }
            }
        }
        Ok(TypeHint { name })
    }

    fn token_text(token: &Token) -> String {
        match token {
            Token::Ident(value) => value.clone(),
            Token::Int(value) => value.to_string(),
            Token::String(value) => format!("{:?}", value),
            Token::Let => "let".into(),
            Token::Const => "const".into(),
            Token::Return => "return".into(),
            Token::Fn => "fn".into(),
            Token::If => "if".into(),
            Token::Else => "else".into(),
            Token::While => "while".into(),
            Token::Contract => "contract".into(),
            Token::State => "state".into(),
            Token::Function => "function".into(),
            Token::Capability => "capability".into(),
            Token::Policy => "policy".into(),
            Token::Require => "require".into(),
            Token::Use => "use".into(),
            Token::Struct => "struct".into(),
            Token::Enum => "enum".into(),
            Token::Pipe => "|".into(),
            Token::Ampersand => "&".into(),
            Token::Assign => "=".into(),
            Token::Eq => "==".into(),
            Token::NotEq => "!=".into(),
            Token::Bang => "!".into(),
            Token::Lt => "<".into(),
            Token::Gt => ">".into(),
            Token::LtEq => "<=".into(),
            Token::GtEq => ">=".into(),
            Token::Plus => "+".into(),
            Token::Minus => "-".into(),
            Token::Arrow => "->".into(),
            Token::Star => "*".into(),
            Token::Slash => "/".into(),
            Token::Percent => "%".into(),
            Token::Colon => ":".into(),
            Token::LParen => "(".into(),
            Token::RParen => ")".into(),
            Token::LBracket => "[".into(),
            Token::RBracket => "]".into(),
            Token::LBrace => "{".into(),
            Token::RBrace => "}".into(),
            Token::Comma => ", ".into(),
            Token::Semi => ";".into(),
            Token::At => "@".into(),
            Token::Dot => ".".into(),
            Token::Question => "?".into(),
            Token::Eof => String::new(),
        }
    }

    fn expect_name(&mut self, what: &str) -> Result<String, ParseError> {
        match self.cur() {
            Token::Ident(name) => {
                self.pos += 1;
                Ok(name)
            }
            other => Err(ParseError {
                message: format!("{what} erwartet, fand {:?}", other),
            }),
        }
    }

    fn use_decl(&mut self) -> Result<Stmt, ParseError> {
        self.pos += 1;
        let mut path = self.expect_name("Importpfad")?;
        while self.cur() == Token::Colon {
            self.pos += 1;
            if self.cur() != Token::Colon {
                return Err(ParseError { message: "':' erwartet in Importpfad '::'".into() });
            }
            self.pos += 1;
            path.push_str("::");
            path.push_str(&self.expect_name("Importpfadsegment")?);
        }
        if self.cur() == Token::Semi {
            self.pos += 1;
        }
        Ok(Stmt::Use { path })
    }

    fn struct_decl(&mut self) -> Result<Stmt, ParseError> {
        self.pos += 1;
        let name = self.expect_name("Struct-Name")?;
        if self.cur() != Token::LBrace {
            return Err(ParseError { message: "'{' nach struct erwartet".into() });
        }
        self.pos += 1;
        let mut fields = Vec::new();
        while self.cur() != Token::RBrace {
            if self.cur() == Token::Eof {
                return Err(ParseError { message: "'}' in struct erwartet".into() });
            }
            let field = self.expect_name("Struct-Feld")?;
            if self.cur() != Token::Colon {
                return Err(ParseError { message: "':' nach Struct-Feld erwartet".into() });
            }
            self.pos += 1;
            let ty = self.simple_type()?;
            fields.push((field, ty));
            match self.cur() {
                Token::Comma | Token::Semi => self.pos += 1,
                Token::RBrace => {}
                other => return Err(ParseError { message: format!("',' oder '}}' nach Struct-Feld erwartet, fand {:?}", other) }),
            }
        }
        self.pos += 1;
        if self.cur() == Token::Semi { self.pos += 1; }
        Ok(Stmt::Struct { name, fields })
    }

    fn enum_decl(&mut self) -> Result<Stmt, ParseError> {
        self.pos += 1;
        let name = self.expect_name("Enum-Name")?;
        if self.cur() != Token::LBrace {
            return Err(ParseError { message: "'{' nach enum erwartet".into() });
        }
        self.pos += 1;
        let mut variants = Vec::new();
        while self.cur() != Token::RBrace {
            if self.cur() == Token::Eof {
                return Err(ParseError { message: "'}' in enum erwartet".into() });
            }
            variants.push(self.expect_name("Enum-Variante")?);
            if self.cur() == Token::LParen {
                let mut depth = 0usize;
                while self.cur() != Token::Eof {
                    let token = self.cur();
                    self.pos += 1;
                    if token == Token::LParen { depth += 1; }
                    if token == Token::RParen {
                        depth = depth.saturating_sub(1);
                        if depth == 0 { break; }
                    }
                }
            }
            match self.cur() {
                Token::Comma | Token::Semi => self.pos += 1,
                Token::RBrace => {}
                other => return Err(ParseError { message: format!("',' oder '}}' nach Enum-Variante erwartet, fand {:?}", other) }),
            }
        }
        self.pos += 1;
        if self.cur() == Token::Semi { self.pos += 1; }
        Ok(Stmt::Enum { name, variants })
    }

    fn contract_decl(&mut self) -> Result<Stmt, ParseError> {
        self.pos += 1;
        let name = self.expect_name("Contract-Name")?;
        if self.cur() != Token::LBrace {
            return Err(ParseError { message: "'{' nach contract erwartet".into() });
        }
        self.pos += 1;
        let mut depth = 1usize;
        let mut body_tokens = Vec::new();
        while depth > 0 {
            let token = self.cur();
            if token == Token::Eof {
                return Err(ParseError { message: "Nicht geschlossener contract-Block".into() });
            }
            self.pos += 1;
            match token {
                Token::LBrace => {
                    depth += 1;
                    body_tokens.push(Self::token_text(&Token::LBrace));
                }
                Token::RBrace => {
                    depth -= 1;
                    if depth > 0 { body_tokens.push(Self::token_text(&Token::RBrace)); }
                }
                _ => body_tokens.push(Self::token_text(&token)),
            }
        }
        Ok(Stmt::Contract { name, body_tokens })
    }

    fn skip_file_annotations(&mut self) {
        while self.cur() != Token::Eof {
            if matches!(self.cur(), Token::Let | Token::Const | Token::Fn | Token::Use | Token::Struct | Token::Enum | Token::Contract) {
                break;
            }
            self.pos += 1;
        }
    }

    fn let_stmt(&mut self) -> Result<LetStmt, ParseError> {
        let is_const = self.cur() == Token::Const;
        self.pos += 1;
        let name = match self.cur() {
            Token::Ident(n) => n,
            other => {
                return Err(ParseError {
                    message: format!("Name erwartet, fand {:?}", other),
                })
            }
        };
        self.pos += 1;
        let mut type_hint = None;
        if self.cur() == Token::Colon {
            self.pos += 1;
            type_hint = Some(self.simple_type()?);
        }
        let mut value = None;
        if self.cur() == Token::Assign {
            self.pos += 1;
            value = Some(self.expr()?);
        }
        if self.cur() == Token::Semi {
            self.pos += 1;
        }
        Ok(LetStmt {
            name,
            is_const,
            type_hint,
            value,
        })
    }

    fn function(&mut self) -> Result<FunctionDef, ParseError> {
        self.pos += 1; // 'fn'
        let name = match self.cur() {
            Token::Ident(n) => n,
            other => {
                return Err(ParseError {
                    message: format!("Fn-Name erwartet, fand {:?}", other),
                })
            }
        };
        self.pos += 1;
        if self.cur() != Token::LParen {
            return Err(ParseError {
                message: "'(' erwartet".to_string(),
            });
        }
        self.pos += 1;
        let mut params = Vec::new();
        while self.cur() != Token::RParen {
            let pname = match self.cur() {
                Token::Ident(n) => n,
                other => {
                    return Err(ParseError {
                        message: format!("Parametername erwartet, fand {:?}", other),
                    })
                }
            };
            self.pos += 1;
            if self.cur() != Token::Colon {
                return Err(ParseError {
                    message: "Parameter-Typ ist Pflicht (': typ'), Referenz-Regel".to_string(),
                });
            }
            self.pos += 1;
            let t = self.simple_type()?;
            params.push(Param {
                name: pname,
                type_hint: t,
            });
            if self.cur() == Token::Comma {
                self.pos += 1;
            } else {
                break;
            }
        }
        if self.cur() != Token::RParen {
            return Err(ParseError {
                message: "')' erwartet".to_string(),
            });
        }
        self.pos += 1;
        let mut return_type = None;
        if self.cur() == Token::Arrow {
            self.pos += 1;
            return_type = Some(self.simple_type()?);
        }
        if self.cur() != Token::LBrace {
            return Err(ParseError {
                message: "'{' erwartet".to_string(),
            });
        }
        self.pos += 1;
        let body = self.block()?;
        Ok(FunctionDef {
            name,
            params,
            return_type,
            body,
        })
    }

    fn block(&mut self) -> Result<Vec<Stmt>, ParseError> {
        let mut stmts = Vec::new();
        while self.cur() != Token::RBrace && self.cur() != Token::Eof {
            stmts.push(self.statement()?);
        }
        if self.cur() != Token::RBrace {
            return Err(ParseError {
                message: "'}' erwartet".to_string(),
            });
        }
        self.pos += 1;
        Ok(stmts)
    }

    fn statement(&mut self) -> Result<Stmt, ParseError> {
        match self.cur() {
            Token::Let | Token::Const => Ok(Stmt::Let(self.let_stmt()?)),
            Token::If => self.if_stmt(),
            Token::While => self.while_stmt(),
            Token::Return => {
                self.pos += 1;
                let value = if self.cur() == Token::RBrace || self.cur() == Token::Eof {
                    None
                } else {
                    Some(self.expr()?)
                };
                if self.cur() == Token::Semi {
                    self.pos += 1;
                }
                Ok(Stmt::Return { value })
            }
            _ => {
                let e = self.expr()?;
                if self.cur() == Token::Semi {
                    self.pos += 1;
                }
                Ok(Stmt::Expr(e))
            }
        }
    }

    /// if <expr> { ... } [else { ... } | else if ...] — SCR-0128 Stufe 1.
    fn if_stmt(&mut self) -> Result<Stmt, ParseError> {
        self.pos += 1; // 'if'
        let cond = self.expr()?;
        if self.cur() != Token::LBrace {
            return Err(ParseError {
                message: "'{' nach if-Bedingung erwartet".to_string(),
            });
        }
        self.pos += 1;
        let then_body = self.block()?;
        let else_body = if self.cur() == Token::Else {
            self.pos += 1;
            match self.cur() {
                Token::LBrace => {
                    self.pos += 1;
                    Some(self.block()?)
                }
                // else if = else { if ... } (Zucker, kanonisch verschachtelt)
                Token::If => Some(vec![self.if_stmt()?]),
                other => {
                    return Err(ParseError {
                        message: format!("'{{' oder 'if' nach else erwartet, fand {:?}", other),
                    })
                }
            }
        } else {
            None
        };
        Ok(Stmt::If {
            cond,
            then_body,
            else_body,
        })
    }

    /// while <expr> { ... } — SCR-0128 Stufe 1.
    fn while_stmt(&mut self) -> Result<Stmt, ParseError> {
        self.pos += 1; // 'while'
        let cond = self.expr()?;
        if self.cur() != Token::LBrace {
            return Err(ParseError {
                message: "'{' nach while-Bedingung erwartet".to_string(),
            });
        }
        self.pos += 1;
        let body = self.block()?;
        Ok(Stmt::While { cond, body })
    }

    fn expr(&mut self) -> Result<Expr, ParseError> {
        self.comparison()
    }

    /// Vergleiche: linksassoziativ, unter der Addition (SCR-0128 Stufe 1).
    fn comparison(&mut self) -> Result<Expr, ParseError> {
        let mut left = self.addition()?;
        loop {
            let op = match self.cur() {
                Token::Eq => "==",
                Token::NotEq => "!=",
                Token::Lt => "<",
                Token::Gt => ">",
                Token::LtEq => "<=",
                Token::GtEq => ">=",
                _ => break,
            };
            self.pos += 1;
            let right = self.addition()?;
            left = Expr::Binary {
                op: op.to_string(),
                left: Box::new(left),
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn addition(&mut self) -> Result<Expr, ParseError> {
        let mut left = self.multiplication()?;
        loop {
            let op = match self.cur() {
                Token::Plus => "+",
                Token::Minus => "-",
                _ => break,
            };
            self.pos += 1;
            let right = self.multiplication()?;
            left = Expr::Binary {
                op: op.to_string(),
                left: Box::new(left),
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn multiplication(&mut self) -> Result<Expr, ParseError> {
        let mut left = self.unary()?;
        loop {
            let op = match self.cur() {
                Token::Star => "*",
                Token::Slash => "/",
                _ => break,
            };
            self.pos += 1;
            let right = self.unary()?;
            left = Expr::Binary {
                op: op.to_string(),
                left: Box::new(left),
                right: Box::new(right),
            };
        }
        Ok(left)
    }

    fn unary(&mut self) -> Result<Expr, ParseError> {
        if self.cur() == Token::Minus {
            self.pos += 1;
            let operand = self.unary()?;
            return Ok(Expr::Unary {
                op: "-".to_string(),
                operand: Box::new(operand),
            });
        }
        self.postfix()
    }

    fn postfix(&mut self) -> Result<Expr, ParseError> {
        let mut node = self.primary()?;
        while self.cur() == Token::LParen {
            self.pos += 1;
            let mut args = Vec::new();
            if self.cur() != Token::RParen {
                loop {
                    args.push(self.expr()?);
                    if self.cur() == Token::Comma {
                        self.pos += 1;
                    } else {
                        break;
                    }
                }
            }
            if self.cur() != Token::RParen {
                return Err(ParseError {
                    message: "')' erwartet".to_string(),
                });
            }
            self.pos += 1;
            node = Expr::Call {
                target: Box::new(node),
                args,
            };
        }
        Ok(node)
    }

    fn primary(&mut self) -> Result<Expr, ParseError> {
        match self.cur() {
            Token::Int(v) => {
                self.pos += 1;
                if v <= i64::MAX as u128 {
                    Ok(Expr::Int(v as i64))
                } else {
                    Ok(Expr::BigInt(v))
                }
            }
            Token::Ident(n) => {
                self.pos += 1;
                Ok(Expr::Ident(n))
            }
            Token::LParen => {
                self.pos += 1;
                let e = self.expr()?;
                if self.cur() != Token::RParen {
                    return Err(ParseError {
                        message: "')' erwartet".to_string(),
                    });
                }
                self.pos += 1;
                Ok(e)
            }
            other => Err(ParseError {
                message: format!("Ausdruck erwartet, fand {:?}", other),
            }),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn praecedenz_und_assoziativitaet() {
        let p = parse_program("let r = 1 + 2 * 3 - 4 / 5;").unwrap();
        let j = p.to_json();
        assert!(j.contains("\"op\":\"*\""));
        assert!(j.contains("\"op\":\"-\""));
    }

    #[test]
    fn fn_definition_mit_return() {
        let p = parse_program("fn add(a: u64, b: u64) -> u64 { return a + b; }").unwrap();
        let j = p.to_json();
        assert!(j.contains("\"kind\":\"FunctionDef\""));
        assert!(j.contains("\"kind\":\"ReturnStatement\""));
        assert!(j.contains("\"kind\":\"Parameter\""));
        assert!(j.contains("\"return_type\":{\"kind\":\"TypeAnnotation\",\"name\":\"u64\""));
    }

    #[test]
    fn fn_body_let_expr_bare_return() {
        let p = parse_program("fn f(x: u64) { let y = x; add(y, 1); return }").unwrap();
        let j = p.to_json();
        assert!(j.contains("\"kind\":\"LetStatement\""));
        assert!(j.contains("\"kind\":\"ExprStatement\""));
        assert!(j.contains("\"value\":null"));
    }

    #[test]
    fn referenz_semantik_return_mit_semi_vor_klammer() {
        // Referenz: 'return;' vor '}' wirft Fehler (parse_expr auf ';')
        assert!(parse_program("fn f() { return; }").is_err());
    }

    #[test]
    fn if_else_und_while_json() {
        let p = parse_program(
            "fn f(x: u64) { if x < 1 { return 1; } else { while x < 2 { let x = x + 1; } } return 0; }",
        )
        .unwrap();
        let j = p.to_json();
        assert!(j.contains("\"kind\":\"IfStatement\""));
        assert!(j.contains("\"kind\":\"WhileStatement\""));
        assert!(j.contains("\"op\":\"<\""));
        // Alphabetische Keys (kanonisch): cond vor else_body vor kind vor then_body
        let idx = j.find("\"kind\":\"IfStatement\"").unwrap();
        assert!(j[..idx].contains("\"cond\":"));
        let idx2 = j.find("\"kind\":\"WhileStatement\"").unwrap();
        assert!(j[..idx2].rfind("\"cond\":").unwrap() > j[..idx2].find("\"body\":").unwrap());
    }

    #[test]
    fn else_if_zucker_verschachtelt() {
        let p = parse_program(
            "fn f(x: u64) { if x < 1 { return 1; } else if x < 2 { return 2; } return 0; }",
        )
        .unwrap();
        let j = p.to_json();
        // Genau EIN else_body mit genau EINEM IfStatement darin
        assert_eq!(j.matches("\"kind\":\"IfStatement\"").count(), 2);
        assert!(j.contains("\"else_body\":[{\"cond\":"));
    }

    #[test]
    fn vergleichs_praezedenz_unter_addition() {
        let p = parse_program("fn f(a: u64) { return a + 1 < 2; }").unwrap();
        let j = p.to_json();
        assert!(j.contains("\"op\":\"<\""));
        assert!(j.find("\"op\":\"<\"").unwrap() > j.find("\"op\":\"+\"").unwrap());
    }

    #[test]
    fn native_import_struct_enum_and_contract_ast() {
        let source = r#"
            use ATC::Types::Address
            enum Status { Open, Closed }
            struct Entry { owner: Address, balances: Map<Address, u128> }
            contract Vault {
                state balances: Map<Address, u128>
                fn transfer(to: Address, amount: u128) -> bool {
                    if amount > 0 { self.balances[to] += amount }
                    return true
                }
            }
        "#;
        let program = parse_program(source).expect("native declarations must parse");
        let json = program.to_json();
        assert!(json.contains("\"kind\":\"UseDeclaration\",\"path\":\"ATC::Types::Address\""));
        assert!(json.contains("\"kind\":\"EnumDeclaration\",\"name\":\"Status\""));
        assert!(json.contains("\"kind\":\"StructDeclaration\",\"name\":\"Entry\""));
        assert!(json.contains("\"name\":\"Map<Address, u128>\""));
        assert!(json.contains("\"kind\":\"ContractDeclaration\",\"name\":\"Vault\""));
    }

    #[test]
    fn large_contract_integer_is_preserved_without_i64_wraparound() {
        let program = parse_program(
            "const MAX_SUPPLY: u128 = 100_000_000_000_000_000_000_000_000",
        ).expect("u128 contract literal must parse");
        assert!(program.to_json().contains("\"value\":100000000000000000000000000"));
    }

    #[test]
    fn fehlerfaelle() {
        assert!(parse_program("let $ = 1;").is_err());
        assert!(parse_program("let x = ;").is_err());
        assert!(parse_program("return 42;").is_err()); // Subset: nur let/const/fn am Top-Level
        assert!(parse_program("fn f(a) { }").is_err()); // Parameter-Typ ist Pflicht
    }
}
