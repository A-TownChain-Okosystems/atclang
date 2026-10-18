//! Structural parser for native and legacy ATCLang contract source.
//! Expression bodies are preserved as token trees; declarations and delimiters
//! are checked here without changing the legacy compile/run frontend.
use crate::lexer::{tokenize, Token};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConformanceError { pub message: String }

type Result<T> = std::result::Result<T, ConformanceError>;

fn error(message: impl Into<String>) -> ConformanceError { ConformanceError { message: message.into() } }

fn matching(tokens: &[Token], start: usize) -> Result<usize> {
    let close = match tokens.get(start) {
        Some(Token::LParen) => Token::RParen,
        Some(Token::LBrace) => Token::RBrace,
        Some(Token::LBracket) => Token::RBracket,
        other => return Err(error(format!("Öffnendes Trennzeichen erwartet, gefunden {other:?}"))),
    };
    let mut stack = vec![close];
    for (i, token) in tokens.iter().enumerate().skip(start + 1) {
        match token {
            Token::LParen => stack.push(Token::RParen),
            Token::LBrace => stack.push(Token::RBrace),
            Token::LBracket => stack.push(Token::RBracket),
            Token::RParen | Token::RBrace | Token::RBracket => {
                if stack.pop().as_ref() != Some(token) {
                    return Err(error(format!("Nicht passendes Abschluss-Token bei Token {i}: {token:?}")));
                }
                if stack.is_empty() { return Ok(i); }
            }
            _ => {}
        }
    }
    Err(error(format!("Nicht geschlossenes Trennzeichen ab Token {start}")))
}

fn is_ident(token: Option<&Token>) -> bool { matches!(token, Some(Token::Ident(_))) }
fn ident(token: Option<&Token>) -> Option<&str> {
    if let Some(Token::Ident(s)) = token { Some(s) } else { None }
}

fn skip_type(tokens: &[Token], mut i: usize, terminators: &[Token]) -> Result<usize> {
    let mut angle = 0i32;
    while i < tokens.len() {
        if angle == 0 && (terminators.iter().any(|t| t == &tokens[i]) || ident(Some(&tokens[i])) == Some("event")) { break; }
        match tokens[i] {
            Token::Lt => angle += 1,
            Token::Gt if angle > 0 => angle -= 1,
            Token::LParen | Token::LBracket => i = matching(tokens, i)?,
            Token::RParen | Token::RBracket | Token::RBrace => break,
            _ => {}
        }
        i += 1;
    }
    if angle != 0 { return Err(error("Generischer Typ ist nicht geschlossen")); }
    Ok(i)
}

fn validate_parameter_list(tokens: &[Token], open: usize) -> Result<usize> {
    let end = matching(tokens, open)?;
    let mut i = open + 1;
    while i < end {
        if !is_ident(tokens.get(i)) { return Err(error(format!("Parametername erwartet bei Token {i}"))); }
        i += 1;
        if tokens.get(i) == Some(&Token::Colon) {
            i += 1;
            let next = skip_type(tokens, i, &[Token::Comma, Token::RParen])?;
            if next == i { return Err(error("Parametertyp fehlt")); }
            i = next;
        }
        if i < end {
            if tokens[i] != Token::Comma { return Err(error(format!("Komma oder ')' erwartet bei Token {i}"))); }
            i += 1;
        }
    }
    Ok(end)
}

fn validate_function(tokens: &[Token], start: usize, end: usize) -> Result<()> {
    let mut i = start + 1;
    if !is_ident(tokens.get(i)) { return Err(error("Funktionsname erwartet")); }
    i += 1;
    // Optional generic parameter list, e.g. fn map<T>(...)
    if tokens.get(i) == Some(&Token::Lt) {
        let mut depth = 0i32;
        while i < end {
            match tokens[i] { Token::Lt => depth += 1, Token::Gt => { depth -= 1; if depth == 0 { i += 1; break; } }, _ => {} }
            i += 1;
        }
        if depth != 0 { return Err(error("Generische Funktionsparameter sind nicht geschlossen")); }
    }
    if tokens.get(i) != Some(&Token::LParen) { return Err(error("Parameterliste nach Funktionsname erwartet")); }
    i = validate_parameter_list(tokens, i)? + 1;
    if tokens.get(i) == Some(&Token::Arrow) {
        i += 1;
        if tokens.get(i) == Some(&Token::LParen) {
            i = matching(tokens, i)? + 1;
        } else {
            i = skip_type(tokens, i, &[Token::LBrace, Token::Semi, Token::Comma])?;
        }
        if i == start + 2 { return Err(error("Rückgabetyp fehlt")); }
    }
    if tokens.get(i) == Some(&Token::LBrace) {
        let body_end = matching(tokens, i)?;
        if body_end > end { return Err(error("Funktionskörper überschreitet den umgebenden Block")); }
        Ok(())
    } else if tokens.get(i) == Some(&Token::Semi) || i == end {
        Ok(())
    } else {
        Err(error(format!("Funktionskörper oder ';' erwartet bei Token {i}")))
    }
}

pub fn validate_contract_source(src: &str) -> Result<()> {
    let tokens = tokenize(src).map_err(|e| error(format!("Lex-Fehler bei Position {}: {:?}", e.pos, e.ch)))?;
    if tokens.len() <= 1 { return Err(error("Leere Quelldatei")); }

    // Validate every delimiter pair, including delimiters in function bodies.
    let mut i = 0;
    while i < tokens.len() {
        match tokens[i] {
            Token::LParen | Token::LBrace | Token::LBracket => i = matching(&tokens, i)?,
            Token::RParen | Token::RBrace | Token::RBracket => return Err(error(format!("Unerwartetes Abschluss-Token bei Token {i}"))),
            _ => {}
        }
        i += 1;
    }

    let mut saw_contract = false;
    let mut i = 0;
    while i + 1 < tokens.len() {
        match &tokens[i] {
            Token::Contract => {
                saw_contract = true;
                if !is_ident(tokens.get(i + 1)) { return Err(error("Contract-Name erwartet")); }
                let open = (i + 2..tokens.len()).find(|&j| tokens[j] == Token::LBrace)
                    .ok_or_else(|| error("Contract-Body erwartet"))?;
                let close = matching(&tokens, open)?;
                validate_members(&tokens, open + 1, close)?;
                i = close;
            }
            _ => {}
        }
        i += 1;
    }
    if !saw_contract { return Err(error("Keine contract-Deklaration gefunden")); }
    Ok(())
}

fn validate_members(tokens: &[Token], start: usize, end: usize) -> Result<()> {
    let mut i = start;
    while i < end {
        match &tokens[i] {
            Token::State => {
                i += 1;
                if tokens.get(i) == Some(&Token::LBrace) {
                    i = matching(tokens, i)? + 1;
                    continue;
                }
                if !is_ident(tokens.get(i)) { return Err(error(format!("State-Feldname erwartet bei Token {i}"))); }
                i += 1;
                if tokens.get(i) == Some(&Token::Colon) {
                    i += 1;
                    let next = skip_type(tokens, i, &[Token::Semi, Token::Comma, Token::RBrace, Token::State, Token::Fn, Token::Function])?;
                    if next == i { return Err(error("State-Feldtyp fehlt")); }
                    i = next;
                }
                if tokens.get(i) == Some(&Token::Semi) || tokens.get(i) == Some(&Token::Comma) { i += 1; }
            }
            Token::Fn | Token::Function => {
                validate_function(tokens, i, end)?;
                // Function body is a token tree; skip it so nested declarations aren't mistaken for members.
                let open = (i + 1..end).find(|&j| tokens[j] == Token::LBrace);
                if let Some(open) = open { i = matching(tokens, open)? + 1; } else { i += 1; }
            }
            Token::Ident(name) if name == "event" => {
                if !is_ident(tokens.get(i + 1)) { return Err(error("Eventname erwartet")); }
                if tokens.get(i + 2) != Some(&Token::LParen) { return Err(error("Event-Parameterliste erwartet")); }
                i = matching(tokens, i + 2)? + 1;
                if tokens.get(i) == Some(&Token::Semi) { i += 1; }
            }
            Token::LBrace => { i = matching(tokens, i)? + 1; }
            Token::Semi | Token::Comma => i += 1,
            _ => {
                // Struct/enum/custom declarations and expressions are retained as
                // token trees; their delimiters were validated above.
                i += 1;
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test] fn accepts_state_event_fn_generics_and_tuple_return() {
        let source = "contract C { state balances: Map<Address, Vec<u128>>; event Transfer(Address, u128); fn get<T>(key: Address) -> (Address, bool) { let x = [1, 2]; return (key, true); } }";
        assert!(validate_contract_source(source).is_ok(), "{:?}", validate_contract_source(source));
    }
    #[test] fn accepts_state_block_and_legacy_fields() {
        assert!(validate_contract_source("contract C { state { owner: Address, count: u128 } fn init() {} }").is_ok());
    }
    #[test] fn accepts_realistic_semicolon_free_contract_members() {
        let source = r#"
            contract BaseContract {
                state owner: Address
                state events: List<Hash>
                event Paused(by: Address)
                fn init() {
                    self.owner = msg_sender()
                    self.events = []
                }
                fn info() -> (Address, bool, u64) {
                    return (self.owner, false, 0)
                }
            }
        "#;
        assert!(validate_contract_source(source).is_ok(), "{:?}", validate_contract_source(source));
    }
    #[test] fn rejects_unbalanced_contract() {
        assert!(validate_contract_source("contract C { fn f() {").is_err());
    }
    #[test] fn rejects_missing_contract() { assert!(validate_contract_source("let x = 1;").is_err()); }
    #[test] fn rejects_malformed_function() { assert!(validate_contract_source("contract C { fn () {} }").is_err()); }
}
