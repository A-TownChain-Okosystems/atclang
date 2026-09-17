// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Deterministische Stack-Maschine ueber verifiziertem ATCLang-Bytecode.
//! Kein Host-Zugriff, keine Uhr, kein Zufall: reine i64-Berechnung mit
//! checked-Arithmetik (Overflow ist ein Fehler, kein Wrap) und fester
//! Aufruftiefe (fail-closed).

use crate::bytecode::Instruction;
use crate::lower::CompiledProgram;

/// Deterministischer Laufzeitfehler (kein Panic-Pfad).
#[derive(Debug, Clone, PartialEq)]
pub enum RunError {
    DivisionByZero { function: String, pc: usize },
    ArithmeticOverflow { function: String, pc: usize },
    CallDepthExceeded { max_depth: usize },
}

/// Feste maximale Aufruftiefe — kein Stack-Overflow, immer ein Fehler.
pub const MAX_CALL_DEPTH: usize = 1024;

struct Frame {
    function_idx: usize,
    pc: usize,
    locals: Vec<i64>,
    stack: Vec<i64>,
}

enum Step {
    Continue,
    Done(i64),
    Invoke {
        callee: usize,
        argc: u16,
        args: Vec<i64>,
    },
}

/// Fuehrt das Kompilat ab der Entry-Funktion aus; Ergebnis = Rueckgabewert.
pub fn execute(prog: &CompiledProgram) -> Result<i64, RunError> {
    let entry = prog.entry as usize;
    let mut frames: Vec<Frame> = vec![new_frame(entry, 0, Vec::new(), prog)];
    loop {
        let step = {
            let depth = frames.len();
            let frame = frames.last_mut().expect("mindestens ein Frame aktiv");
            let function_idx = frame.function_idx;
            let Some(instruction) = prog.functions[function_idx]
                .bytecode
                .instructions
                .get(frame.pc)
                .copied()
            else {
                return Err(RunError::CallDepthExceeded {
                    max_depth: MAX_CALL_DEPTH,
                });
            };
            let pc = frame.pc;
            frame.pc += 1;
            match instruction {
                Instruction::ConstI64(v) => {
                    frame.stack.push(v);
                    Step::Continue
                }
                Instruction::LoadLocal(i) => {
                    frame.stack.push(frame.locals[i as usize]);
                    Step::Continue
                }
                Instruction::StoreLocal(i) => {
                    let v = frame.stack.pop().expect("verifiziert");
                    frame.locals[i as usize] = v;
                    Step::Continue
                }
                Instruction::Add | Instruction::Sub | Instruction::Mul => {
                    let (b, a) = pop2(&mut frame.stack);
                    let v = match instruction {
                        Instruction::Add => a.checked_add(b),
                        Instruction::Sub => a.checked_sub(b),
                        _ => a.checked_mul(b),
                    };
                    match v {
                        Some(x) => {
                            frame.stack.push(x);
                            Step::Continue
                        }
                        None => {
                            return Err(RunError::ArithmeticOverflow {
                                function: prog.functions[function_idx].name.clone(),
                                pc,
                            })
                        }
                    }
                }
                Instruction::Div => {
                    let (b, a) = pop2(&mut frame.stack);
                    if b == 0 {
                        return Err(RunError::DivisionByZero {
                            function: prog.functions[function_idx].name.clone(),
                            pc,
                        });
                    }
                    match a.checked_div(b) {
                        Some(x) => {
                            frame.stack.push(x);
                            Step::Continue
                        }
                        None => {
                            return Err(RunError::ArithmeticOverflow {
                                function: prog.functions[function_idx].name.clone(),
                                pc,
                            })
                        }
                    }
                }
                Instruction::Neg => {
                    let v = frame.stack.pop().expect("verifiziert");
                    match v.checked_neg() {
                        Some(x) => {
                            frame.stack.push(x);
                            Step::Continue
                        }
                        None => {
                            return Err(RunError::ArithmeticOverflow {
                                function: prog.functions[function_idx].name.clone(),
                                pc,
                            })
                        }
                    }
                }
                Instruction::Call { function, argc } => {
                    if depth >= MAX_CALL_DEPTH {
                        return Err(RunError::CallDepthExceeded {
                            max_depth: MAX_CALL_DEPTH,
                        });
                    }
                    let callee = function as usize;
                    debug_assert_eq!(prog.functions[callee].param_count, argc);
                    // Argumente vom Stack nehmen (oberstes = letztes Argument).
                    let mut args: Vec<i64> = Vec::with_capacity(argc as usize);
                    for _ in 0..argc {
                        args.push(frame.stack.pop().expect("verifiziert"));
                    }
                    args.reverse();
                    Step::Invoke { callee, argc, args }
                }
                Instruction::Return => {
                    let value = frame.stack.pop().expect("verifiziert");
                    Step::Done(value)
                }
                Instruction::Pop => {
                    frame.stack.pop().expect("verifiziert");
                    Step::Continue
                }
            }
        };
        match step {
            Step::Invoke { callee, argc, args } => {
                frames.push(new_frame(callee, argc, args, prog));
                continue;
            }
            Step::Continue => continue,
            Step::Done(value) => {
                frames.pop();
                match frames.last_mut() {
                    Some(caller) => {
                        caller.stack.push(value);
                    }
                    None => return Ok(value),
                }
            }
        }
    }
}

fn new_frame(function_idx: usize, argc: u16, args: Vec<i64>, prog: &CompiledProgram) -> Frame {
    let meta = &prog.functions[function_idx];
    debug_assert_eq!(meta.param_count, argc);
    debug_assert_eq!(args.len(), argc as usize);
    let mut locals = vec![0i64; meta.local_count as usize];
    locals[..argc as usize].copy_from_slice(&args);
    Frame {
        function_idx,
        pc: 0,
        locals,
        stack: Vec::new(),
    }
}

fn pop2(stack: &mut Vec<i64>) -> (i64, i64) {
    let b = stack.pop().expect("verifiziert");
    let a = stack.pop().expect("verifiziert");
    (b, a)
}
