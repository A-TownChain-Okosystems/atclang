// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Native ATC contract frontend.
//! Syntax/AST recognition only; lowering remains the existing ATCLang path.

use crate::lexer::{tokenize, LexError, Token};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NativeContract {
    pub version: String,
    pub standards: Vec<String>,
    pub asset_type: Option<String>,
    pub name: Option<String>,
    pub symbol: Option<String>,
    pub contract: ContractDef,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContractDef {
    pub name: String,
    pub members: Vec<ContractMember>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ContractMember {
    State(StateDef),
    Function(NativeFunction),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StateDef {
    pub fields: Vec<StateField>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StateField {
    pub name: String,
    pub type_name: String,
    pub initializer: Option<Vec<Token>>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NativeFunction {
    pub name: String,
    pub params: Vec<NativeParam>,
    pub return_type: Option<String>,
    pub capabilities: Vec<CapabilityDef>,
    pub policies: Vec<PolicyDef>,
    pub body: Vec<Token>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CapabilityDef {
    pub name: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PolicyDef {
    pub name: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NativeParam {
    pub name: String,
    pub type_name: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NativeParseError {
    pub message: String,
}

impl NativeParseError {
    fn new(message: impl Into<String>) -> Self {
        Self {
            message: message.into(),
        }
    }
}

pub fn parse_native_contract(src: &str) -> Result<NativeContract, NativeParseError> {
    let tokens = tokenize(src).map_err(|e| NativeParseError::new(format_lex_error(e)))?;
    let mut p = Parser { tokens, pos: 0 };
    p.parse()
}

pub fn validate_native_contract(contract: &NativeContract) -> Result<(), NativeParseError> {
    if contract.version.is_empty() {
        return Err(NativeParseError::new("@version ist erforderlich"));
    }
    if contract.standards.iter().any(|s| s.is_empty()) {
        return Err(NativeParseError::new("@standard darf nicht leer sein"));
    }
    if let Some(t) = &contract.asset_type {
        if !matches!(
            t.as_str(),
            "NFT721"
                | "NFT1155"
                | "Token20"
                | "Token777"
                | "Governance"
                | "Oracle"
                | "Bridge"
                | "Rental"
                | "Hybrid"
        ) {
            return Err(NativeParseError::new(format!(
                "unbekannter nativer @type: {t}"
            )));
        }
    }
    if contract.contract.name.is_empty() {
        return Err(NativeParseError::new("Contract-Name darf nicht leer sein"));
    }
    Ok(())
}

struct Parser {
    tokens: Vec<Token>,
    pos: usize,
}

impl Parser {
    fn cur(&self) -> &Token {
        self.tokens.get(self.pos).unwrap_or(&Token::Eof)
    }

    fn bump(&mut self) -> Token {
        let token = self.cur().clone();
        if self.pos < self.tokens.len() {
            self.pos += 1;
        }
        token
    }

    fn expect(&mut self, expected: Token) -> Result<(), NativeParseError> {
        if *self.cur() == expected {
            self.bump();
            Ok(())
        } else {
            Err(NativeParseError::new(format!(
                "erwartet {:?}, gefunden {:?}",
                expected,
                self.cur()
            )))
        }
    }

    fn ident(&mut self, what: &str) -> Result<String, NativeParseError> {
        match self.bump() {
            Token::Ident(v) => Ok(v),
            other => Err(NativeParseError::new(format!(
                "{what} erwartet, gefunden {other:?}"
            ))),
        }
    }

    fn parse(&mut self) -> Result<NativeContract, NativeParseError> {
        let mut version = None;
        let mut standards = Vec::new();
        let mut asset_type = None;
        let mut name = None;
        let mut symbol = None;

        while *self.cur() == Token::At {
            self.bump();
            let directive = self.ident("Direktive")?;
            match directive.as_str() {
                "version" => {
                    if version.is_some() {
                        return Err(NativeParseError::new("doppelte @version-Direktive"));
                    }
                    version = Some(self.version()?);
                }
                "standard" => standards.push(self.standard_id()?),
                "type" => asset_type = Some(self.ident("@type-Wert")?),
                "name" => name = Some(self.string("@name")?),
                "symbol" => symbol = Some(self.string("@symbol")?),
                other => {
                    return Err(NativeParseError::new(format!(
                        "unbekannte Direktive @{other}"
                    )))
                }
            }
        }

        self.expect(Token::Contract)?;
        let contract_name = self.ident("Contract-Name")?;
        self.expect(Token::LBrace)?;
        let mut members = Vec::new();
        while *self.cur() != Token::RBrace && *self.cur() != Token::Eof {
            match self.cur() {
                Token::State => members.push(ContractMember::State(self.state()?)),
                Token::At | Token::Function => {
                    members.push(ContractMember::Function(self.function()?))
                }
                other => {
                    return Err(NativeParseError::new(format!(
                        "Contract-Member erwartet, gefunden {other:?}"
                    )))
                }
            }
        }
        self.expect(Token::RBrace)?;
        if *self.cur() != Token::Eof {
            return Err(NativeParseError::new("unerwartete Tokens nach Contract"));
        }

        let contract = NativeContract {
            version: version.ok_or_else(|| NativeParseError::new("@version ist erforderlich"))?,
            standards,
            asset_type,
            name,
            symbol,
            contract: ContractDef {
                name: contract_name,
                members,
            },
        };
        validate_native_contract(&contract)?;
        Ok(contract)
    }

    fn version(&mut self) -> Result<String, NativeParseError> {
        let mut out = match self.bump() {
            Token::Int(v) => v.to_string(),
            other => {
                return Err(NativeParseError::new(format!(
                    "Versionsnummer erwartet, gefunden {other:?}"
                )))
            }
        };
        while *self.cur() == Token::Dot {
            self.bump();
            match self.bump() {
                Token::Int(v) => {
                    out.push('.');
                    out.push_str(&v.to_string());
                }
                other => {
                    return Err(NativeParseError::new(format!(
                        "Versionssegment erwartet, gefunden {other:?}"
                    )))
                }
            }
        }
        Ok(out)
    }

    fn standard_id(&mut self) -> Result<String, NativeParseError> {
        let mut out = match self.bump() {
            Token::Ident(v) => v,
            Token::Int(v) => format!("{v:03}"),
            other => {
                return Err(NativeParseError::new(format!(
                    "@standard-ID erwartet, gefunden {other:?}"
                )))
            }
        };
        while *self.cur() == Token::Minus {
            self.bump();
            let part = match self.bump() {
                Token::Ident(v) => v,
                Token::Int(v) => format!("{v:03}"),
                other => {
                    return Err(NativeParseError::new(format!(
                        "Standard-ID-Segment erwartet, gefunden {other:?}"
                    )))
                }
            };
            out.push('-');
            out.push_str(&part);
        }
        Ok(out)
    }

    fn string(&mut self, what: &str) -> Result<String, NativeParseError> {
        match self.bump() {
            Token::String(v) => Ok(v),
            other => Err(NativeParseError::new(format!(
                "{what} String erwartet, gefunden {other:?}"
            ))),
        }
    }

    fn state(&mut self) -> Result<StateDef, NativeParseError> {
        self.expect(Token::State)?;
        self.expect(Token::LBrace)?;
        let mut fields = Vec::new();
        while *self.cur() != Token::RBrace && *self.cur() != Token::Eof {
            let field_name = self.ident("State-Feld")?;
            self.expect(Token::Colon)?;
            let type_name = self.ident("State-Typ")?;
            let initializer = if *self.cur() == Token::Assign {
                self.bump();
                Some(self.collect_until(&[Token::Semi, Token::RBrace])?)
            } else {
                None
            };
            if *self.cur() == Token::Semi {
                self.bump();
            }
            fields.push(StateField {
                name: field_name,
                type_name,
                initializer,
            });
        }
        self.expect(Token::RBrace)?;
        Ok(StateDef { fields })
    }

    fn function(&mut self) -> Result<NativeFunction, NativeParseError> {
        let mut capabilities = Vec::new();
        let mut policies = Vec::new();
        while *self.cur() == Token::At {
            self.bump();
            // Keyword-Token (Capability/Policy) direkt akzeptieren; Lexer mappt
            // capability/policy auf Keywords, der Decorator-Name darf beides sein.
            let decorator = match self.cur() {
                Token::Capability => {
                    self.bump();
                    "capability".to_string()
                }
                Token::Policy => {
                    self.bump();
                    "policy".to_string()
                }
                _ => self.ident("Decorator")?,
            };
            match decorator.as_str() {
                "capability" => capabilities.push(CapabilityDef {
                    name: self.ident("@capability-Wert")?,
                }),
                "policy" => policies.push(PolicyDef {
                    name: self.ident("@policy-Wert")?,
                }),
                other => {
                    return Err(NativeParseError::new(format!(
                        "unbekannter Function-Decorator @{other}"
                    )))
                }
            }
        }
        self.expect(Token::Function)?;
        let name = self.ident("Funktionsname")?;
        self.expect(Token::LParen)?;
        let mut params = Vec::new();
        while *self.cur() != Token::RParen {
            let pname = self.ident("Parametername")?;
            self.expect(Token::Colon)?;
            let ptype = self.ident("Parameter-Typ")?;
            params.push(NativeParam {
                name: pname,
                type_name: ptype,
            });
            if *self.cur() == Token::Comma {
                self.bump();
            } else {
                break;
            }
        }
        self.expect(Token::RParen)?;
        let return_type = if *self.cur() == Token::Arrow {
            self.bump();
            Some(self.ident("Return-Typ")?)
        } else {
            None
        };
        self.expect(Token::LBrace)?;
        let body = self.collect_balanced_body()?;
        Ok(NativeFunction {
            name,
            params,
            return_type,
            capabilities,
            policies,
            body,
        })
    }

    fn collect_balanced_body(&mut self) -> Result<Vec<Token>, NativeParseError> {
        let mut body = Vec::new();
        let mut depth = 1usize;
        while depth > 0 {
            match self.bump() {
                Token::LBrace => {
                    depth += 1;
                    body.push(Token::LBrace);
                }
                Token::RBrace => {
                    depth -= 1;
                    if depth > 0 {
                        body.push(Token::RBrace);
                    }
                }
                Token::Eof => return Err(NativeParseError::new("unbeendeter Function-Body")),
                token => body.push(token),
            }
        }
        Ok(body)
    }

    fn collect_until(&mut self, stops: &[Token]) -> Result<Vec<Token>, NativeParseError> {
        let mut out = Vec::new();
        while !stops.iter().any(|s| self.cur() == s) {
            if *self.cur() == Token::Eof {
                return Err(NativeParseError::new("unerwartetes Ende im Ausdruck"));
            }
            out.push(self.bump());
        }
        Ok(out)
    }
}

fn format_lex_error(error: LexError) -> String {
    format!("Lex-Fehler bei Position {}: {:?}", error.pos, error.ch)
}

#[cfg(test)]
mod tests {
    use super::*;

    const SOURCE: &str = r#"
@version 1.0
@standard ATC-001
@standard ATC-005
@type NFT721
@name "ATownAvatar"
@symbol "ATCA"

contract ATownAvatar {
    state {
        next_id: u256 = 1;
    }

    @capability mint
    function mintAvatar(to: Address, metadata: String) -> TokenId {
        let id = next_id;
        next_id = next_id + 1;
        mint(to, id);
        set_metadata(id, metadata);
        return id;
    }

    @policy soulbound
    function enforceSoulbound(token_id: TokenId) {
        require(!is_soulbound(token_id), "ATC-005: soulbound token");
    }
}
"#;

    #[test]
    fn parses_reference_contract_shape() {
        let contract = parse_native_contract(SOURCE).expect("native .atc must parse");
        assert_eq!(contract.version, "1.0");
        assert_eq!(contract.standards, vec!["ATC-001", "ATC-005"]);
        assert_eq!(contract.asset_type.as_deref(), Some("NFT721"));
        assert_eq!(contract.name.as_deref(), Some("ATownAvatar"));
        assert_eq!(contract.symbol.as_deref(), Some("ATCA"));
        assert_eq!(contract.contract.name, "ATownAvatar");
        assert_eq!(contract.contract.members.len(), 3);
    }

    #[test]
    fn rejects_unknown_directive() {
        let err = parse_native_contract("@version 1.0 @unknown x contract C {}").unwrap_err();
        assert!(err.message.contains("unbekannte Direktive"));
    }

    #[test]
    fn rejects_missing_version() {
        let err = parse_native_contract("contract C {}").unwrap_err();
        assert!(err.message.contains("@version"));
    }

    #[test]
    fn rejects_unknown_native_type() {
        let err = parse_native_contract("@version 1.0 @type NotNative contract C {}").unwrap_err();
        assert!(err.message.contains("unbekannter nativer @type"));
    }

    #[test]
    fn parses_capability_and_policy_ast_nodes() {
        let contract = parse_native_contract(
            r#"@version 1.0
contract C {
    @capability mint
    function mint(to: Address) {
    }

    @policy soulbound
    function enforce(token_id: TokenId) {
    }
}"#,
        )
        .expect("capability/policy decorators must parse");

        let functions = contract
            .contract
            .members
            .iter()
            .filter_map(|member| match member {
                ContractMember::Function(function) => Some(function),
                ContractMember::State(_) => None,
            })
            .collect::<Vec<_>>();

        assert_eq!(
            functions[0].capabilities,
            vec![CapabilityDef {
                name: "mint".into()
            }]
        );
        assert!(functions[0].policies.is_empty());
        assert_eq!(
            functions[1].policies,
            vec![PolicyDef {
                name: "soulbound".into()
            }]
        );
        assert!(functions[1].capabilities.is_empty());
    }

    #[test]
    fn rejects_duplicate_version_directive() {
        let err = parse_native_contract("@version 1.0 @version 1.1 contract C {}").unwrap_err();
        assert!(err.message.contains("doppelte @version"));
    }

    #[test]
    fn rejects_unknown_function_decorator() {
        let err =
            parse_native_contract("@version 1.0 contract C { @unknown mint function f() {} }")
                .unwrap_err();
        assert!(err.message.contains("unbekannter Function-Decorator"));
    }

    #[test]
    fn rejects_unterminated_function_body() {
        let err = parse_native_contract("@version 1.0 contract C { function f() { let x = 1;")
            .unwrap_err();
        assert!(err.message.contains("unbeendeter Function-Body"));
    }

    #[test]
    fn rejects_missing_contract() {
        let err = parse_native_contract("@version 1.0").unwrap_err();
        assert!(err.message.contains("Contract-Name") || err.message.contains("Contract"));
    }
}
