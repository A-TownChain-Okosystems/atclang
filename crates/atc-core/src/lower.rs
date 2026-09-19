// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! AST -> Bytecode-Lowering (Welle 2, Fortschreibung SCR-0128 Stufe 1:
//! if/else, while, Vergleiche mit PC-relativen Spruengen, i16-Distanzen).
//! Fail-closed: jede nicht im Subset unterstuetzte Form ist ein Lowering-Fehler,
//! jede erzeugte Funktion wird vor Rueckgabe gegen den Bytecode-Verifizierer
//! geprueft (verify vor trust).
//!
//! Ablaufmodell: Programmstatements ausser Funktionsdefinitionen bilden die
//! implizite Einstiegsfunktion `__main__` (Index 0, lokale Variablen sind die
//! top-level lets). Gibt es keine top-level Statements und genau eine
//! nutzerdefinierte Funktion `main`, ist diese der Entry.

use crate::ast::{Expr, FunctionDef, Program, Stmt};
use crate::bytecode::{Bytecode, Instruction};
use std::collections::HashMap;

/// Ein vom Lowering abgelehnter Zustand (fail-closed).
#[derive(Debug, Clone, PartialEq)]
pub struct LowerError {
    pub message: String,
}

impl LowerError {
    fn new(msg: impl Into<String>) -> Self {
        Self {
            message: msg.into(),
        }
    }
}

/// Funktionsindex -> Name, Parametzahl, verifizierter Bytecode.
#[derive(Debug, Clone, PartialEq)]
pub struct CompiledFunction {
    pub name: String,
    pub param_count: u16,
    pub local_count: u16,
    pub bytecode: Bytecode,
}

/// Vollstaendig verifiziertes Kompilat eines Programms.
#[derive(Debug, Clone, PartialEq)]
pub struct CompiledProgram {
    pub functions: Vec<CompiledFunction>,
    /// Einstiegsfunktion (Index), deren Rueckgabewert `execute` liefert.
    pub entry: u16,
}

impl CompiledProgram {
    pub fn function_count(&self) -> u16 {
        self.functions.len() as u16
    }
}

const ENTRY: &str = "__main__";

struct FnLowerer<'a> {
    /// name -> (Funktionsindex, Parametzahl)
    fn_ids: &'a HashMap<String, (u16, u16)>,
    function_name: &'a str,
    locals: HashMap<String, u16>,
    next_local: u16,
    out: Vec<Instruction>,
}

impl<'a> FnLowerer<'a> {
    fn local_slot(&mut self, name: &str) -> Result<u16, LowerError> {
        if let Some(i) = self.locals.get(name) {
            return Ok(*i);
        }
        if self.next_local == u16::MAX {
            return Err(LowerError::new(format!(
                "Lokal-Limit ueberschritten in Funktion {}",
                self.function_name
            )));
        }
        let i = self.next_local;
        self.next_local += 1;
        self.locals.insert(name.to_string(), i);
        Ok(i)
    }

    /// PC-relative Sprungdistanz (Basis: Folgeinstruktion), i16-bereichsgeprueft.
    fn disp(&self, from: usize, to: usize) -> Result<i16, LowerError> {
        let d = to as i64 - (from as i64 + 1);
        if d < i16::MIN as i64 || d > i16::MAX as i64 {
            return Err(LowerError::new(
                "Sprungdistanz ueberschreitet i16-Bereich (Funktion zu gross)",
            ));
        }
        Ok(d as i16)
    }

    fn lower_stmt(&mut self, s: &Stmt, top_level: bool) -> Result<(), LowerError> {
        match s {
            Stmt::Let(l) => {
                let Some(value) = &l.value else {
                    return Err(LowerError::new(format!(
                        "let ohne Initialisierung wird nicht unterstuetzt ({} in {})",
                        l.name, self.function_name
                    )));
                };
                let slot = self.local_slot(&l.name)?;
                self.lower_expr(value)?;
                self.out.push(Instruction::StoreLocal(slot));
                Ok(())
            }
            Stmt::Return { value } => {
                if top_level {
                    return Err(LowerError::new(
                        "return ist nur innerhalb von Funktionen erlaubt",
                    ));
                }
                match value {
                    Some(v) => self.lower_expr(v)?,
                    None => self.out.push(Instruction::ConstI64(0)),
                }
                self.out.push(Instruction::Return);
                Ok(())
            }
            Stmt::Expr(e) => {
                self.lower_expr(e)?;
                self.out.push(Instruction::Pop);
                Ok(())
            }
            Stmt::If {
                cond,
                then_body,
                else_body,
            } => {
                self.lower_expr(cond)?;
                let jif = self.out.len();
                self.out.push(Instruction::JumpIfFalse(0));
                for s in then_body {
                    self.lower_stmt(s, top_level)?;
                }
                match else_body {
                    Some(eb) => {
                        let jend = self.out.len();
                        self.out.push(Instruction::Jump(0));
                        let d = self.disp(jif, self.out.len())?;
                        self.out[jif] = Instruction::JumpIfFalse(d);
                        for s in eb {
                            self.lower_stmt(s, top_level)?;
                        }
                        let d2 = self.disp(jend, self.out.len())?;
                        self.out[jend] = Instruction::Jump(d2);
                    }
                    None => {
                        let d = self.disp(jif, self.out.len())?;
                        self.out[jif] = Instruction::JumpIfFalse(d);
                    }
                }
                Ok(())
            }
            Stmt::While { cond, body } => {
                let start = self.out.len();
                self.lower_expr(cond)?;
                let jif = self.out.len();
                self.out.push(Instruction::JumpIfFalse(0));
                for s in body {
                    self.lower_stmt(s, top_level)?;
                }
                // Ruecksprung zum Schleifenkopf (i16, negativ).
                let d_back = self.disp(self.out.len(), start)?;
                self.out.push(Instruction::Jump(d_back));
                let d_fwd = self.disp(jif, self.out.len())?;
                self.out[jif] = Instruction::JumpIfFalse(d_fwd);
                Ok(())
            }
            Stmt::Fn(_) => Err(LowerError::new(format!(
                "Funktionsdefinition ist nur auf Programmebene erlaubt (in {})",
                self.function_name
            ))),
        }
    }

    fn lower_expr(&mut self, e: &Expr) -> Result<(), LowerError> {
        match e {
            Expr::Int(v) => self.out.push(Instruction::ConstI64(*v)),
            Expr::Ident(name) => match self.locals.get(name) {
                Some(i) => self.out.push(Instruction::LoadLocal(*i)),
                None => {
                    return Err(LowerError::new(format!(
                        "unbekannter Bezeichner '{}' in Funktion {}",
                        name, self.function_name
                    )))
                }
            },
            Expr::Unary { op, operand } => match op.as_str() {
                "-" => {
                    self.out.push(Instruction::ConstI64(0));
                    self.lower_expr(operand)?;
                    self.out.push(Instruction::Sub);
                }
                "+" => self.lower_expr(operand)?,
                other => {
                    return Err(LowerError::new(format!(
                        "unarer Operator '{other}' ist nicht im Subset"
                    )))
                }
            },
            Expr::Binary { op, left, right } => {
                self.lower_expr(left)?;
                self.lower_expr(right)?;
                match op.as_str() {
                    "+" => self.out.push(Instruction::Add),
                    "-" => self.out.push(Instruction::Sub),
                    "*" => self.out.push(Instruction::Mul),
                    "/" => self.out.push(Instruction::Div),
                    "==" => self.out.push(Instruction::Eq),
                    "!=" => self.out.push(Instruction::Ne),
                    "<" => self.out.push(Instruction::Lt),
                    ">" => self.out.push(Instruction::Gt),
                    "<=" => self.out.push(Instruction::Le),
                    ">=" => self.out.push(Instruction::Ge),
                    other => {
                        return Err(LowerError::new(format!(
                            "Operator '{other}' ist nicht im Subset"
                        )))
                    }
                }
            }
            Expr::Call { target, args } => {
                let Expr::Ident(fname) = target.as_ref() else {
                    return Err(LowerError::new(
                        "Aufrufziel muss ein Bezeichner sein (keine First-Class-Funktionen)",
                    ));
                };
                if args.len() > u16::MAX as usize {
                    return Err(LowerError::new("Argumentanzahl ueberschritten"));
                }
                let Some((fid, param_count)) = self.fn_ids.get(fname.as_str()) else {
                    return Err(LowerError::new(format!(
                        "Aufruf unbekannter Funktion '{fname}'"
                    )));
                };
                if *param_count != args.len() as u16 {
                    return Err(LowerError::new(format!(
                        "Argumentzahl passt nicht: '{fname}' erwartet {}, Aufruf mit {}",
                        param_count,
                        args.len()
                    )));
                }
                for a in args {
                    self.lower_expr(a)?;
                }
                self.out.push(Instruction::Call {
                    function: *fid,
                    argc: args.len() as u16,
                });
            }
        }
        Ok(())
    }
}

fn finish_function(
    l: FnLowerer,
    name: String,
    param_count: u16,
) -> Result<CompiledFunction, LowerError> {
    let mut instructions = l.out;
    let last_is_return = matches!(instructions.last(), Some(Instruction::Return));
    if !last_is_return {
        instructions.push(Instruction::ConstI64(0));
        instructions.push(Instruction::Return);
    }
    let bytecode = Bytecode { instructions };
    let local_count = l.next_local;
    let function_count = l.fn_ids.len() as u16;
    bytecode
        .verify(local_count, function_count)
        .map_err(|e| LowerError::new(format!("Verifizierer lehnte Funktion {name} ab: {e:?}")))?;
    Ok(CompiledFunction {
        name,
        param_count,
        local_count,
        bytecode,
    })
}

/// Lowered eine nutzerdefinierte Funktion (nicht der Entry).
fn lower_user_function(
    f: &FunctionDef,
    fn_ids: &HashMap<String, (u16, u16)>,
) -> Result<CompiledFunction, LowerError> {
    if f.params.len() > u16::MAX as usize {
        return Err(LowerError::new(format!(
            "Parameterzahl ueberschritten in Funktion {}",
            f.name
        )));
    }
    let mut lowerer = FnLowerer {
        fn_ids,
        function_name: &f.name,
        locals: HashMap::new(),
        next_local: 0,
        out: Vec::new(),
    };
    for p in &f.params {
        // Slot nur registrieren — die VM liefert die Argumente als lokale Werte.
        lowerer.local_slot(&p.name)?;
    }
    for s in &f.body {
        lowerer.lower_stmt(s, false)?;
    }
    finish_function(lowerer, f.name.clone(), f.params.len() as u16)
}

/// Lowered ein komplettes Programm: Entry + alle Funktionen, alles verifiziert.
pub fn lower_program(prog: &Program) -> Result<CompiledProgram, LowerError> {
    // Funktionsindex-Tabelle: Index 0 reserviert fuer __main__.
    let mut fn_ids: HashMap<String, (u16, u16)> = HashMap::new();
    fn_ids.insert(ENTRY.to_string(), (0, 0));
    for s in &prog.statements {
        if let Stmt::Fn(f) = s {
            let idx = fn_ids.len() as u16;
            if fn_ids
                .insert(f.name.clone(), (idx, f.params.len() as u16))
                .is_some()
            {
                return Err(LowerError::new(format!(
                    "doppelte Funktionsdefinition '{}'",
                    f.name
                )));
            }
        }
    }
    // Entry senken: alle Nicht-Fn-Statements in __main__.
    let mut main_lowerer = FnLowerer {
        fn_ids: &fn_ids,
        function_name: ENTRY,
        locals: HashMap::new(),
        next_local: 0,
        out: Vec::new(),
    };
    let mut main_has_code = false;
    for s in &prog.statements {
        if let Stmt::Fn(_) = s {
            continue;
        }
        main_has_code = true;
        main_lowerer.lower_stmt(s, true)?;
    }
    let entry_fn = finish_function(main_lowerer, ENTRY.to_string(), 0)?;

    // Entry-Auswahl: fn main nur nutzen, wenn __main__ leer ist.
    let entry = if main_has_code {
        0
    } else {
        fn_ids.get("main").map_or(0, |(idx, _)| *idx)
    };

    let mut functions = vec![entry_fn];
    for s in &prog.statements {
        if let Stmt::Fn(f) = s {
            functions.push(lower_user_function(f, &fn_ids)?);
        }
    }
    Ok(CompiledProgram { functions, entry })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn run(src: &str) -> i64 {
        let prog = crate::parser::parse_program(src).expect("Parse-Fehler");
        let compiled = lower_program(&prog).expect("Lowering-Fehler");
        crate::vm::execute(&compiled).expect("Run-Fehler")
    }

    #[test]
    fn if_ohne_else_waehlt_zweig() {
        // fn m(a) { if a < 0 { return 0 - a; } return a; } — keine main-Nutzerfn,
        // Entry = __main__ leer -> main nutzen
        assert_eq!(
            run(
                "fn abs(x: i64) -> i64 { if x < 0 { return 0 - x; } return x; }
                 fn main() -> i64 { return abs(0 - 5); }"
            ),
            5
        );
        assert_eq!(
            run(
                "fn abs(x: i64) -> i64 { if x < 0 { return 0 - x; } return x; }
                 fn main() -> i64 { return abs(7); }"
            ),
            7
        );
    }

    #[test]
    fn if_else_beide_zweige() {
        assert_eq!(
            run(
                "fn max(a: i64, b: i64) -> i64 { if a < b { return b; } else { return a; } }
                 fn main() -> i64 { return max(3, 9) + max(9, 3); }"
            ),
            18
        );
    }

    #[test]
    fn while_fakultaet() {
        assert_eq!(
            run("fn fact(n: i64) -> i64 { let r = 1; let i = 2; while i < n + 1 { let r = r * i; let i = i + 1; } return r; }
                 fn main() -> i64 { return fact(5); }"),
            120
        );
    }

    #[test]
    fn while_nulldurchlauf() {
        assert_eq!(
            run(
                "fn f(n: i64) -> i64 { while n < 0 { let n = n + 1; } return n; }
                 fn main() -> i64 { return f(42); }"
            ),
            42
        );
    }

    #[test]
    fn vergleichsoperatoren_ende_zu_ende() {
        let src = "fn cmp(a: i64, b: i64) -> i64 { return a < b; }
                   fn main() -> i64 { return cmp(1, 2) + 10 * cmp(2, 1) + 100 * (1 == 1) + 1000 * (1 != 1); }";
        // 1 + 0 + 100 + 0
        assert_eq!(run(src), 101);
    }

    #[test]
    fn else_if_kette() {
        assert_eq!(
            run("fn sign(x: i64) -> i64 { if x < 0 { return 0 - 1; } else if 0 < x { return 1; } return 0; }
                 fn main() -> i64 { return sign(0 - 3) + 2 * sign(0) + 3 * sign(9); }"),
            2
        );
    }

    #[test]
    fn while_laenge_begrenzt_nicht_endlos() {
        // Endlosschleife-Schutz ist Laufzeit-Ende nicht — aber deterministisch:
        // hier nur Korrektheit des Ruecksprungs ueber 3 Iterationen.
        assert_eq!(
            run(
                "fn f() -> i64 { let i = 0; while i < 3 { let i = i + 1; } return i; }
                 fn main() -> i64 { return f(); }"
            ),
            3
        );
    }

    #[test]
    fn unbekannter_operator_nach_wie_vor_fail_closed() {
        let prog = crate::parser::parse_program("fn main() -> i64 { return 1 && 2; }");
        assert!(prog.is_err()); // '&&' lexikographisch nicht im Subset
    }
}
