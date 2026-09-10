// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Recursive-Descent-Parser — Stage 3 des Canonical Cores (SCR-0085).
//! Subset exakt nach Python-Referenz (src/atclang/frontend/parser/parser.py):
//! Programmebene = let/const/fn; Funktionskoerper = let/return/ExprStatement.
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
                other => {
                    return Err(ParseError {
                        message: format!("let/const/fn am Top-Level erwartet, fand {:?}", other),
                    })
                }
            };
            statements.push(s);
        }
        Ok(Program { statements })
    }

    fn simple_type(&mut self) -> Result<TypeHint, ParseError> {
        match self.cur() {
            Token::Ident(n) => {
                self.pos += 1;
                Ok(TypeHint { name: n })
            }
            other => Err(ParseError { message: format!("Typ erwartet, fand {:?}", other) }),
        }
    }

    fn let_stmt(&mut self) -> Result<LetStmt, ParseError> {
        let is_const = self.cur() == Token::Const;
        self.pos += 1;
        let name = match self.cur() {
            Token::Ident(n) => n,
            other => {
                return Err(ParseError { message: format!("Name erwartet, fand {:?}", other) })
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
        Ok(LetStmt { name, is_const, type_hint, value })
    }

    fn function(&mut self) -> Result<FunctionDef, ParseError> {
        self.pos += 1; // 'fn'
        let name = match self.cur() {
            Token::Ident(n) => n,
            other => return Err(ParseError { message: format!("Fn-Name erwartet, fand {:?}", other) }),
        };
        self.pos += 1;
        if self.cur() != Token::LParen {
            return Err(ParseError { message: "'(' erwartet".to_string() });
        }
        self.pos += 1;
        let mut params = Vec::new();
        while self.cur() != Token::RParen {
            let pname = match self.cur() {
                Token::Ident(n) => n,
                other => {
                    return Err(ParseError { message: format!("Parametername erwartet, fand {:?}", other) })
                }
            };
            self.pos += 1;
            if self.cur() != Token::Colon {
                return Err(ParseError { message: "Parameter-Typ ist Pflicht (': typ'), Referenz-Regel".to_string() });
            }
            self.pos += 1;
            let t = self.simple_type()?;
            params.push(Param { name: pname, type_hint: t });
            if self.cur() == Token::Comma {
                self.pos += 1;
            } else {
                break;
            }
        }
        if self.cur() != Token::RParen {
            return Err(ParseError { message: "')' erwartet".to_string() });
        }
        self.pos += 1;
        let mut return_type = None;
        if self.cur() == Token::Arrow {
            self.pos += 1;
            return_type = Some(self.simple_type()?);
        }
        if self.cur() != Token::LBrace {
            return Err(ParseError { message: "'{' erwartet".to_string() });
        }
        self.pos += 1;
        let body = self.block()?;
        Ok(FunctionDef { name, params, return_type, body })
    }

    fn block(&mut self) -> Result<Vec<Stmt>, ParseError> {
        let mut stmts = Vec::new();
        while self.cur() != Token::RBrace && self.cur() != Token::Eof {
            stmts.push(self.statement()?);
        }
        if self.cur() != Token::RBrace {
            return Err(ParseError { message: "'}' erwartet".to_string() });
        }
        self.pos += 1;
        Ok(stmts)
    }

    fn statement(&mut self) -> Result<Stmt, ParseError> {
        match self.cur() {
            Token::Let | Token::Const => Ok(Stmt::Let(self.let_stmt()?)),
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

    fn expr(&mut self) -> Result<Expr, ParseError> {
        self.addition()
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
                return Err(ParseError { message: "')' erwartet".to_string() });
            }
            self.pos += 1;
            node = Expr::Call { target: Box::new(node), args };
        }
        Ok(node)
    }

    fn primary(&mut self) -> Result<Expr, ParseError> {
        match self.cur() {
            Token::Int(v) => {
                self.pos += 1;
                Ok(Expr::Int(v as i64))
            }
            Token::Ident(n) => {
                self.pos += 1;
                Ok(Expr::Ident(n))
            }
            Token::LParen => {
                self.pos += 1;
                let e = self.expr()?;
                if self.cur() != Token::RParen {
                    return Err(ParseError { message: "')' erwartet".to_string() });
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
    fn fehlerfaelle() {
        assert!(parse_program("let $ = 1;").is_err());
        assert!(parse_program("let x = ;").is_err());
        assert!(parse_program("return 42;").is_err()); // Subset: nur let/const/fn am Top-Level
        assert!(parse_program("fn f(a) { }").is_err()); // Parameter-Typ ist Pflicht
    }
}
