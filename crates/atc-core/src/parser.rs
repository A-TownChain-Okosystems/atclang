// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Recursive-Descent-Parser — Stage 2 des Canonical Cores (SCR-0084).
//! Subset exakt nach Python-Referenz (src/atclang/frontend/parser/parser.py):
//! Programmebene = let/const-Anweisungen; Ausdruecke: + - * / (KEIN % —
//! Referenz-Befund), unaeres Minus, Klammern, Funktionsaufrufe (Postfix).
//! Assoziativitaet: links (wie Referenz), Praezedenz: * / vor + -.

use crate::ast::{Expr, LetStmt, Program, TypeHint};
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
            if self.cur() == Token::Let || self.cur() == Token::Const {
                statements.push(self.let_stmt()?);
            } else {
                return Err(ParseError {
                    message: format!("let/const am Top-Level erwartet, fand {:?}", self.cur()),
                });
            }
        }
        Ok(Program { statements })
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
            match self.cur() {
                Token::Ident(n) => {
                    type_hint = Some(TypeHint { name: n });
                    self.pos += 1;
                }
                other => {
                    return Err(ParseError { message: format!("Typ erwartet, fand {:?}", other) })
                }
            }
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
        // 1 + 2 * 3 - 4 / 5
        let p = parse_program("let r = 1 + 2 * 3 - 4 / 5;").unwrap();
        let j = p.to_json();
        assert!(j.contains("\"op\":\"*\""));
        assert!(j.contains("\"op\":\"-\""));
    }

    #[test]
    fn calls_und_unaer() {
        let p = parse_program("let s = add(1, 2);\nlet n = -5;").unwrap();
        let j = p.to_json();
        assert!(j.contains("\"kind\":\"FunctionCall\""));
        assert!(j.contains("\"kind\":\"UnaryOp\""));
    }

    #[test]
    fn fehlerfaelle() {
        assert!(parse_program("let $ = 1;").is_err());
        assert!(parse_program("let x = ;").is_err());
        assert!(parse_program("return 42;").is_err()); // Subset: nur let/const am Top-Level
    }
}
