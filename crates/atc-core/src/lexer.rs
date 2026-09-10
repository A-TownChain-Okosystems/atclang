// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Lexer-MVP: Tokens fuer eine ATCLang-Teilmenge.
//! Token-Modell am Python-Referenz-Lexer (src/atclang/frontend/lexer/lexer.py)
//! ausgerichtet (SCR-0084). Hinweis: '=' ist im Referenz-Modell EQ und dient
//! im let-Kontext als Zuweisung; ':' ist COLON. '%' wird geparst, gehoert aber
//! NICHT zum Operator-Subset des Referenz-Parsers (Differential-Befund).

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Token {
    Int(u64),
    Ident(String),
    Let,
    Const,
    Return,
    Fn,
    Assign,
    Plus,
    Minus,
    Star,
    Slash,
    Percent,
    Colon,
    LParen,
    RParen,
    LBrace,
    RBrace,
    Comma,
    Semi,
    Eof,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LexError {
    pub pos: usize,
    pub ch: char,
}

pub fn tokenize(src: &str) -> Result<Vec<Token>, LexError> {
    let mut tokens = Vec::new();
    let mut chars = src.chars().enumerate().peekable();
    while let Some((pos, ch)) = chars.next() {
        match ch {
            ' ' | '\t' | '\n' | '\r' => {}
            '=' => tokens.push(Token::Assign),
            '+' => tokens.push(Token::Plus),
            '-' => tokens.push(Token::Minus),
            '*' => tokens.push(Token::Star),
            '/' => tokens.push(Token::Slash),
            '%' => tokens.push(Token::Percent),
            ':' => tokens.push(Token::Colon),
            '(' => tokens.push(Token::LParen),
            ')' => tokens.push(Token::RParen),
            '{' => tokens.push(Token::LBrace),
            '}' => tokens.push(Token::RBrace),
            ',' => tokens.push(Token::Comma),
            ';' => tokens.push(Token::Semi),
            '0'..='9' => {
                let mut n: u64 = (ch as u64) - ('0' as u64);
                while let Some(&(_, c)) = chars.peek() {
                    if c.is_ascii_digit() {
                        n = (n * 10) + ((c as u64) - ('0' as u64));
                        chars.next();
                    } else {
                        break;
                    }
                }
                tokens.push(Token::Int(n));
            }
            _ if ch.is_alphabetic() || ch == '_' => {
                let mut ident = String::new();
                ident.push(ch);
                while let Some(&(_, c)) = chars.peek() {
                    if c.is_alphanumeric() || c == '_' {
                        ident.push(c);
                        chars.next();
                    } else {
                        break;
                    }
                }
                match ident.as_str() {
                    "let" => tokens.push(Token::Let),
                    "const" => tokens.push(Token::Const),
                    "return" => tokens.push(Token::Return),
                    "fn" => tokens.push(Token::Fn),
                    _ => tokens.push(Token::Ident(ident)),
                }
            }
            _ => return Err(LexError { pos, ch }),
        }
    }
    tokens.push(Token::Eof);
    Ok(tokens)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn let_zuweisung() {
        let ts = tokenize("let x = 42;").unwrap();
        assert_eq!(ts, vec![
            Token::Let,
            Token::Ident("x".to_string()),
            Token::Assign,
            Token::Int(42),
            Token::Semi,
            Token::Eof,
        ]);
    }

    #[test]
    fn const_mit_typ() {
        let ts = tokenize("const pi: u64 = 3;").unwrap();
        assert_eq!(ts, vec![
            Token::Const,
            Token::Ident("pi".to_string()),
            Token::Colon,
            Token::Ident("u64".to_string()),
            Token::Assign,
            Token::Int(3),
            Token::Semi,
            Token::Eof,
        ]);
    }

    #[test]
    fn ungültiges_zeichen() {
        assert_eq!(tokenize("let $ = 1"), Err(LexError { pos: 4, ch: '$' }));
    }
}
