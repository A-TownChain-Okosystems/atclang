// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! AST -> Bytecode-Lowering (Welle 2, SCR-0085-Fortschreibung).
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
