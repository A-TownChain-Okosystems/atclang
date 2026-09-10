// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! AST des Canonical Cores mit kanonischer JSON-Serialisierung.
//! Die JSON ist BYTGLEICH mit der Python-Referenz-Ausgabe aus
//! tools/differential/dump_reference.py (json.dumps, sort_keys=True,
//! compact separators) — das ist der Differential-Kontrakt (SCR-0084/0085).
//! Stage 3: FunctionDef/Parameter/ReturnStatement/ExprStatement (SCR-0085).

#[derive(Debug, Clone, PartialEq)]
pub enum Expr {
    Int(i64),
    Ident(String),
    Unary { op: String, operand: Box<Expr> },
    Binary { op: String, left: Box<Expr>, right: Box<Expr> },
    Call { target: Box<Expr>, args: Vec<Expr> },
}

#[derive(Debug, Clone, PartialEq)]
pub struct TypeHint {
    pub name: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct LetStmt {
    pub name: String,
    pub is_const: bool,
    pub type_hint: Option<TypeHint>,
    pub value: Option<Expr>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Param {
    pub name: String,
    pub type_hint: TypeHint,
}

#[derive(Debug, Clone, PartialEq)]
pub struct FunctionDef {
    pub name: String,
    pub params: Vec<Param>,
    pub return_type: Option<TypeHint>,
    pub body: Vec<Stmt>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Stmt {
    Let(LetStmt),
    Fn(FunctionDef),
    Return { value: Option<Expr> },
    /// Nackter Ausdruck — Referenz wrappt als ExprStatement.
    Expr(Expr),
}

#[derive(Debug, Clone, PartialEq, Default)]
pub struct Program {
    pub statements: Vec<Stmt>,
}

fn esc(s: &str) -> String {
    let mut out = String::new();
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            _ => out.push(c),
        }
    }
    out
}

fn expr_json(e: &Expr, out: &mut String) {
    match e {
        Expr::Int(v) => {
            out.push_str("{\"kind\":\"IntLiteral\",\"value\":");
            out.push_str(&v.to_string());
            out.push('}');
        }
        Expr::Ident(name) => {
            out.push_str("{\"kind\":\"Identifier\",\"name\":\"");
            out.push_str(&esc(name));
            out.push_str("\"}");
        }
        Expr::Unary { op, operand } => {
            out.push_str("{\"kind\":\"UnaryOp\",\"op\":\"");
            out.push_str(&esc(op));
            out.push_str("\",\"operand\":");
            expr_json(operand, out);
            out.push('}');
        }
        Expr::Binary { op, left, right } => {
            out.push_str("{\"kind\":\"BinaryOp\",\"left\":");
            expr_json(left, out);
            out.push_str(",\"op\":\"");
            out.push_str(&esc(op));
            out.push_str("\",\"right\":");
            expr_json(right, out);
            out.push('}');
        }
        Expr::Call { target, args } => {
            out.push_str("{\"args\":[");
            for (i, a) in args.iter().enumerate() {
                if i > 0 {
                    out.push(',');
                }
                expr_json(a, out);
            }
            out.push_str("],\"kind\":\"FunctionCall\",\"target\":");
            expr_json(target, out);
            out.push('}');
        }
    }
}

fn type_json(t: &TypeHint, out: &mut String) {
    out.push_str("{\"kind\":\"TypeAnnotation\",\"name\":\"");
    out.push_str(&esc(&t.name));
    out.push_str("\",\"params\":[]}");
}

fn let_json(s: &LetStmt, out: &mut String) {
    out.push_str("{\"is_const\":");
    out.push_str(if s.is_const { "true" } else { "false" });
    out.push_str(",\"kind\":\"LetStatement\",\"name\":\"");
    out.push_str(&esc(&s.name));
    out.push_str("\",\"type_hint\":");
    match &s.type_hint {
        None => out.push_str("null"),
        Some(t) => type_json(t, out),
    }
    out.push_str(",\"value\":");
    match &s.value {
        None => out.push_str("null"),
        Some(v) => expr_json(v, out),
    }
    out.push('}');
}

fn param_json(p: &Param, out: &mut String) {
    out.push_str("{\"kind\":\"Parameter\",\"name\":\"");
    out.push_str(&esc(&p.name));
    out.push_str("\",\"type_hint\":");
    type_json(&p.type_hint, out);
    out.push('}');
}

fn fn_json(f: &FunctionDef, out: &mut String) {
    out.push_str("{\"body\":[");
    for (i, s) in f.body.iter().enumerate() {
        if i > 0 {
            out.push(',');
        }
        stmt_json(s, out);
    }
    out.push_str("],\"decorators\":[],\"is_pub\":false,\"kind\":\"FunctionDef\",\"name\":\"");
    out.push_str(&esc(&f.name));
    out.push_str("\",\"params\":[");
    for (i, p) in f.params.iter().enumerate() {
        if i > 0 {
            out.push(',');
        }
        param_json(p, out);
    }
    out.push_str("],\"return_type\":");
    match &f.return_type {
        None => out.push_str("null"),
        Some(t) => type_json(t, out),
    }
    out.push('}');
}

fn stmt_json(s: &Stmt, out: &mut String) {
    match s {
        Stmt::Let(l) => let_json(l, out),
        Stmt::Fn(f) => fn_json(f, out),
        Stmt::Return { value } => {
            out.push_str("{\"kind\":\"ReturnStatement\",\"value\":");
            match value {
                None => out.push_str("null"),
                Some(v) => expr_json(v, out),
            }
            out.push('}');
        }
        Stmt::Expr(e) => {
            out.push_str("{\"expr\":");
            expr_json(e, out);
            out.push_str(",\"kind\":\"ExprStatement\"}");
        }
    }
}

impl Program {
    /// Kanonisches JSON — bytgleich zur Python-Referenz (Differential-Kontrakt).
    pub fn to_json(&self) -> String {
        let mut out = String::from("{\"kind\":\"Program\",\"statements\":[");
        for (i, s) in self.statements.iter().enumerate() {
            if i > 0 {
                out.push(',');
            }
            stmt_json(s, &mut out);
        }
        out.push_str("]}");
        out
    }
}
