//! Syntax gate for the existing .atc contract corpus.
//! It checks lexical validity, balanced delimiters and the contract/member
//! declaration skeleton without lowering legacy contract bodies to bytecode.
use crate::lexer::{tokenize, Token};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConformanceError { pub message: String }

pub fn validate_contract_source(src: &str) -> Result<(), ConformanceError> {
    let tokens = tokenize(src).map_err(|e| ConformanceError {
        message: format!("Lex-Fehler bei Position {}: {:?}", e.pos, e.ch),
    })?;
    let mut stack: Vec<Token> = Vec::new();
    for token in &tokens {
        match token {
            Token::LParen | Token::LBrace | Token::LBracket => stack.push(token.clone()),
            Token::RParen | Token::RBrace | Token::RBracket => {
                let expected = match token {
                    Token::RParen => Token::LParen,
                    Token::RBrace => Token::LBrace,
                    _ => Token::LBracket,
                };
                if stack.pop().as_ref() != Some(&expected) {
                    return Err(ConformanceError { message: format!("nicht passendes Abschluss-Token: {token:?}") });
                }
            }
            _ => {}
        }
    }
    if let Some(open) = stack.last() {
        return Err(ConformanceError { message: format!("nicht geschlossene Klammer: {open:?}") });
    }
    let contract_positions: Vec<usize> = tokens.iter().enumerate()
        .filter_map(|(i, t)| (*t == Token::Contract).then_some(i)).collect();
    if contract_positions.is_empty() {
        return Err(ConformanceError { message: "kein contract-Deklaration gefunden".into() });
    }
    for pos in contract_positions {
        if !matches!(tokens.get(pos + 1), Some(Token::Ident(_))) {
            return Err(ConformanceError { message: "Contract-Name erwartet".into() });
        }
        if !tokens[pos + 2..].iter().any(|t| *t == Token::LBrace) {
            return Err(ConformanceError { message: "Contract-Body erwartet".into() });
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn accepts_legacy_contract_and_generic_types() {
        assert!(validate_contract_source("contract C { state values: Map<Address, u128> fn f() -> (Address, bool) { let x = [1, 2] } }").is_ok());
    }
    #[test] fn rejects_unbalanced_contract() {
        assert!(validate_contract_source("contract C { fn f() {").is_err());
    }
    #[test] fn rejects_missing_contract() { assert!(validate_contract_source("let x = 1;").is_err()); }
}
