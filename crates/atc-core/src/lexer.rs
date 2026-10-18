// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Lexer for the ATCLang reference subset and native contract syntax.

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Token {
    Int(u64), Ident(String), Let, Const, Return, Fn, If, Else, While,
    Contract, State, Function, Capability, Policy, Require,
    Assign, Eq, NotEq, Bang, Lt, Gt, LtEq, GtEq,
    Plus, Minus, Arrow, Star, Slash, Percent,
    Colon, LParen, RParen, LBrace, RBrace, LBracket, RBracket,
    Comma, Semi, Eof, At, Dot, Pipe, Ampersand, String(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LexError { pub pos: usize, pub ch: char }

pub fn tokenize(src: &str) -> Result<Vec<Token>, LexError> {
    let mut tokens = Vec::new();
    let mut chars = src.chars().enumerate().peekable();
    while let Some((pos, ch)) = chars.next() {
        match ch {
            ' ' | '\t' | '\n' | '\r' => {}
            '=' => { if chars.peek().is_some_and(|&(_, c)| c == '=') { chars.next(); tokens.push(Token::Eq); } else { tokens.push(Token::Assign); } }
            '!' => { if chars.peek().is_some_and(|&(_, c)| c == '=') { chars.next(); tokens.push(Token::NotEq); } else { tokens.push(Token::Bang); } }
            '<' => { if chars.peek().is_some_and(|&(_, c)| c == '=') { chars.next(); tokens.push(Token::LtEq); } else { tokens.push(Token::Lt); } }
            '>' => { if chars.peek().is_some_and(|&(_, c)| c == '=') { chars.next(); tokens.push(Token::GtEq); } else { tokens.push(Token::Gt); } }
            '+' => tokens.push(Token::Plus),
            '-' => { if chars.peek().is_some_and(|&(_, c)| c == '>') { chars.next(); tokens.push(Token::Arrow); } else { tokens.push(Token::Minus); } }
            '*' => tokens.push(Token::Star),
            '/' => {
                if chars.peek().is_some_and(|&(_, c)| c == '/') {
                    chars.next();
                    for (_, comment_ch) in chars.by_ref() { if comment_ch == '\n' { break; } }
                } else { tokens.push(Token::Slash); }
            }
            '%' => tokens.push(Token::Percent),
            ':' => tokens.push(Token::Colon), '@' => tokens.push(Token::At), '.' => tokens.push(Token::Dot),
            '(' => tokens.push(Token::LParen), ')' => tokens.push(Token::RParen),
            '{' => tokens.push(Token::LBrace), '}' => tokens.push(Token::RBrace),
            '[' => tokens.push(Token::LBracket), ']' => tokens.push(Token::RBracket),
            '|' => tokens.push(Token::Pipe), '&' => tokens.push(Token::Ampersand),
            ',' => tokens.push(Token::Comma), ';' => tokens.push(Token::Semi),
            '"' => {
                let mut value = String::new();
                loop {
                    match chars.next() {
                        Some((_, '"')) => break,
                        Some((_, '\\')) => match chars.next() {
                            Some((_, 'n')) => value.push('\n'), Some((_, 'r')) => value.push('\r'),
                            Some((_, 't')) => value.push('\t'), Some((_, '"')) => value.push('"'),
                            Some((_, '\\')) => value.push('\\'),
                            Some((p, c)) => return Err(LexError { pos: p, ch: c }),
                            None => return Err(LexError { pos, ch: '\\' }),
                        },
                        Some((_, c)) => value.push(c),
                        None => return Err(LexError { pos: src.len(), ch: '"' }),
                    }
                }
                tokens.push(Token::String(value));
            }
            '0'..='9' => {
                let mut n = (ch as u64) - ('0' as u64);
                while let Some(&(_, c)) = chars.peek() {
                    if c.is_ascii_digit() { n = n.checked_mul(10).and_then(|x| x.checked_add((c as u64)-('0' as u64))).ok_or(LexError { pos, ch })?; chars.next(); }
                    else { break; }
                }
                tokens.push(Token::Int(n));
            }
            _ if ch.is_alphabetic() || ch == '_' => {
                let mut ident = String::new(); ident.push(ch);
                while let Some(&(_, c)) = chars.peek() { if c.is_alphanumeric() || c == '_' { ident.push(c); chars.next(); } else { break; } }
                tokens.push(match ident.as_str() {
                    "let" => Token::Let, "const" => Token::Const, "return" => Token::Return,
                    "fn" => Token::Fn, "if" => Token::If, "else" => Token::Else, "while" => Token::While,
                    "contract" => Token::Contract, "state" => Token::State, "function" => Token::Function,
                    "capability" => Token::Capability, "policy" => Token::Policy, "require" => Token::Require,
                    _ => Token::Ident(ident),
                });
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
    #[test] fn let_zuweisung() { assert_eq!(tokenize("let x = 42;").unwrap(), vec![Token::Let,Token::Ident("x".into()),Token::Assign,Token::Int(42),Token::Semi,Token::Eof]); }
    #[test] fn native_delimiter_tokens() {
        assert_eq!(tokenize("Map<Address, u128> [x] A | B & C").unwrap().iter().filter(|t| matches!(t, Token::LBracket|Token::RBracket|Token::Pipe|Token::Ampersand)).count(), 4);
    }
    #[test] fn comments_and_strings() { assert!(tokenize("// comment\n@name \"ATC\"").is_ok()); }
    #[test] fn rejects_invalid_char() { assert_eq!(tokenize("$"), Err(LexError { pos: 0, ch: '$' })); }
}
