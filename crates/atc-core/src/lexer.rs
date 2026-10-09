// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Lexer: Tokens fuer die ATCLang-Teilmenge (SCR-0128 Stufe 1: if/else/while
//! und Vergleichsoperatoren ==, !=, <, >, <=, >=; Booleans kodiert als i64 0/1).
//! Token-Modell am Python-Referenz-Lexer (src/atclang/frontend/lexer/lexer.py)
//! ausgerichtet (SCR-0084/0085). Hinweis: '=' ist im Referenz-Modell EQ und dient
//! im let-Kontext als Zuweisung; ':' ist COLON; '->' ist ARROW (Return-Type).
//! '%' wird geparst, gehoert aber NICHT zum Operator-Subset des Referenz-Parsers.

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Token {
    Int(u64),
    Ident(String),
    Let,
    Const,
    Return,
    Fn,
    If,
    Else,
    While,
    Contract,
    State,
    Function,
    Capability,
    Policy,
    Require,
    Assign,
    Eq,
    NotEq,
    Bang,
    Lt,
    Gt,
    LtEq,
    GtEq,
    Plus,
    Minus,
    Arrow,
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
    At,
    Dot,
    String(String),
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
            '=' => {
                if chars.peek().is_some_and(|&(_, c)| c == '=') {
                    chars.next();
                    tokens.push(Token::Eq);
                } else {
                    tokens.push(Token::Assign);
                }
            }
            '!' => {
                if chars.peek().is_some_and(|&(_, c)| c == '=') {
                    chars.next();
                    tokens.push(Token::NotEq);
                } else {
                    tokens.push(Token::Bang);
                }
            }
            '<' => {
                if chars.peek().is_some_and(|&(_, c)| c == '=') {
                    chars.next();
                    tokens.push(Token::LtEq);
                } else {
                    tokens.push(Token::Lt);
                }
            }
            '>' => {
                if chars.peek().is_some_and(|&(_, c)| c == '=') {
                    chars.next();
                    tokens.push(Token::GtEq);
                } else {
                    tokens.push(Token::Gt);
                }
            }
            '+' => tokens.push(Token::Plus),
            '-' => {
                if chars.peek().is_some_and(|&(_, c)| c == '>') {
                    chars.next();
                    tokens.push(Token::Arrow);
                } else {
                    tokens.push(Token::Minus);
                }
            }
            '*' => tokens.push(Token::Star),
            '/' => {
                if chars.peek().is_some_and(|&(_, c)| c == '/') {
                    // Line comments are lexical trivia. Consume the complete
                    // line before tokenizing, including arbitrary Unicode text.
                    chars.next();
                    for (_, comment_ch) in chars.by_ref() {
                        if comment_ch == '\n' {
                            break;
                        }
                    }
                } else {
                    tokens.push(Token::Slash);
                }
            }
            '%' => tokens.push(Token::Percent),
            ':' => tokens.push(Token::Colon),
            '@' => tokens.push(Token::At),
            '.' => tokens.push(Token::Dot),
            '(' => tokens.push(Token::LParen),
            ')' => tokens.push(Token::RParen),
            '{' => tokens.push(Token::LBrace),
            '}' => tokens.push(Token::RBrace),
            ',' => tokens.push(Token::Comma),
            ';' => tokens.push(Token::Semi),
            '"' => {
                let mut value = String::new();
                loop {
                    match chars.next() {
                        Some((_, '"')) => break,
                        Some((pos, '\\')) => match chars.next() {
                            Some((_, 'n')) => value.push('\n'),
                            Some((_, 'r')) => value.push('\r'),
                            Some((_, 't')) => value.push('\t'),
                            Some((_, '"')) => value.push('"'),
                            Some((_, '\\')) => value.push('\\'),
                            Some((_, ch)) => return Err(LexError { pos, ch }),
                            None => return Err(LexError { pos, ch: '\\' }),
                        },
                        Some((_pos, ch)) => value.push(ch),
                        None => {
                            return Err(LexError {
                                pos: src.len(),
                                ch: '"',
                            })
                        }
                    }
                }
                tokens.push(Token::String(value));
            }
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
                    "if" => tokens.push(Token::If),
                    "else" => tokens.push(Token::Else),
                    "while" => tokens.push(Token::While),
                    "contract" => tokens.push(Token::Contract),
                    "state" => tokens.push(Token::State),
                    "function" => tokens.push(Token::Function),
                    "capability" => tokens.push(Token::Capability),
                    "policy" => tokens.push(Token::Policy),
                    "require" => tokens.push(Token::Require),
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
        assert_eq!(
            ts,
            vec![
                Token::Let,
                Token::Ident("x".to_string()),
                Token::Assign,
                Token::Int(42),
                Token::Semi,
                Token::Eof,
            ]
        );
    }

    #[test]
    fn fn_signatur_mit_arrow() {
        let ts = tokenize("fn add(a: u64) -> u64 { }").unwrap();
        assert_eq!(
            ts,
            vec![
                Token::Fn,
                Token::Ident("add".to_string()),
                Token::LParen,
                Token::Ident("a".to_string()),
                Token::Colon,
                Token::Ident("u64".to_string()),
                Token::RParen,
                Token::Arrow,
                Token::Ident("u64".to_string()),
                Token::LBrace,
                Token::RBrace,
                Token::Eof,
            ]
        );
    }

    #[test]
    fn minus_nicht_arrow() {
        let ts = tokenize("let n = -5;").unwrap();
        assert_eq!(ts[3], Token::Minus);
        assert_eq!(ts[4], Token::Int(5));
    }

    #[test]
    fn native_tokens() {
        let ts = tokenize("@version 1.0 @name \"ATC\" contract C { @capability mint function f(to: Address) -> TokenId { require(true, \"ok\"); } }").unwrap();
        assert!(ts.contains(&Token::At));
        assert!(ts.contains(&Token::Dot));
        assert!(ts.contains(&Token::String("ATC".into())));
        assert!(ts.contains(&Token::Contract));
        assert!(ts.contains(&Token::Capability));
        assert!(ts.contains(&Token::Function));
        assert!(ts.contains(&Token::Require));
    }

    #[test]
    fn line_comments_ignore_unicode_text() {
        let tokens = tokenize("// ───────────── Unicode comment\nlet x = 1;").unwrap();
        assert_eq!(
            tokens,
            vec![
                Token::Let,
                Token::Ident("x".to_string()),
                Token::Assign,
                Token::Int(1),
                Token::Semi,
                Token::Eof,
            ]
        );
    }

    #[test]
    fn ungültiges_zeichen() {
        assert_eq!(tokenize("let $ = 1"), Err(LexError { pos: 4, ch: '$' }));
    }
}
