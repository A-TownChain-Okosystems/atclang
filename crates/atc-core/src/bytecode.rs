// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Canonical ATCLang bytecode format and verifier (G3 baseline, SCR-0128 Stufe 1).
//! Encoding is deterministic: fixed opcode bytes, little-endian immediates,
//! no host-dependent serialization.
//!
//! Sprungmodell (SCR-0128 Stufe 1): `Jump(i16)`/`JumpIfFalse(i16)` sind PC-relativ,
//! Bezugsbasis ist die Folgeinstruktion (`Ziel = pc + 1 + distanz`). i16 erlaubt
//! Rueckwaertsspruenge fuer `while` (Dokumentation: SCR-0128 weicht damit von der
//! u16-Skizze ab — Begruendung: Schleifen). Der Verifizierer ist seit Stufe 1 ein
//! Worklist-Fixpoint: Er prueft jeden ERREICHBAREN Pfad, validiert Sprungziele
//! (Grenzen) und verlangt konsistente Stack-Hoehen an Sprungzielen (Join-Stellen).
//! `last_const` (statischer Div/0-Fang) ist pfadabhaengig; an Joins mit
//! unterschiedlichen Werten wird konservativ auf `None` geschwächt — der
//! dynamische Check in der VM bleibt fail-closed erhalten.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Instruction {
    ConstI64(i64),
    LoadLocal(u16),
    StoreLocal(u16),
    Add,
    Sub,
    Mul,
    Div,
    Neg,
    Eq,
    Ne,
    Lt,
    Gt,
    Le,
    Ge,
    Call {
        function: u16,
        argc: u16,
    },
    Return,
    Pop,
    /// PC-relativer Sprung: Ziel = pc + 1 + distanz (auch rueckwaerts, while).
    Jump(i16),
    /// Pop der Bedingung; Sprung bei 0 (falsch). Ziel = pc + 1 + distanz.
    JumpIfFalse(i16),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Bytecode {
    pub instructions: Vec<Instruction>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum VerifyError {
    StackUnderflow {
        pc: usize,
    },
    DivisionByZeroConstant {
        pc: usize,
    },
    InvalidLocal {
        pc: usize,
        index: u16,
    },
    InvalidFunction {
        pc: usize,
        function: u16,
    },
    InvalidStackHeight {
        pc: usize,
        expected: usize,
        actual: usize,
    },
    /// Sprungziel ausserhalb [0, len].
    InvalidJumpTarget {
        pc: usize,
        target: i64,
    },
    /// Widerspruechliche Stack-Hoehen an einer Join-Stelle (Sprungziel).
    InconsistentStackHeight {
        pc: usize,
        first: usize,
        second: usize,
    },
}

impl Instruction {
    pub fn encode(&self, out: &mut Vec<u8>) {
        match self {
            Self::ConstI64(v) => {
                out.push(0x01);
                out.extend_from_slice(&v.to_le_bytes());
            }
            Self::LoadLocal(i) => {
                out.push(0x02);
                out.extend_from_slice(&i.to_le_bytes());
            }
            Self::StoreLocal(i) => {
                out.push(0x03);
                out.extend_from_slice(&i.to_le_bytes());
            }
            Self::Add => out.push(0x10),
            Self::Sub => out.push(0x11),
            Self::Mul => out.push(0x12),
            Self::Div => out.push(0x13),
            Self::Neg => out.push(0x14),
            Self::Eq => out.push(0x15),
            Self::Ne => out.push(0x16),
            Self::Lt => out.push(0x17),
            Self::Gt => out.push(0x18),
            Self::Le => out.push(0x19),
            Self::Ge => out.push(0x1A),
            Self::Call { function, argc } => {
                out.push(0x20);
                out.extend_from_slice(&function.to_le_bytes());
                out.extend_from_slice(&argc.to_le_bytes());
            }
            Self::Return => out.push(0x30),
            Self::Pop => out.push(0x31),
            Self::Jump(d) => {
                out.push(0x40);
                out.extend_from_slice(&d.to_le_bytes());
            }
            Self::JumpIfFalse(d) => {
                out.push(0x41);
                out.extend_from_slice(&d.to_le_bytes());
            }
        }
    }
}

impl Bytecode {
    pub fn encode(&self) -> Vec<u8> {
        let mut out = Vec::new();
        out.extend_from_slice(b"ATCB");
        out.extend_from_slice(&1u16.to_le_bytes());
        out.extend_from_slice(&(self.instructions.len() as u32).to_le_bytes());
        for instruction in &self.instructions {
            instruction.encode(&mut out);
        }
        out
    }

    /// Sprungziel zu einer Instruktion (Bezugsbasis: Folgeinstruktion).
    fn jump_target(pc: usize, distanz: i16) -> i64 {
        pc as i64 + 1 + distanz as i64
    }

    pub fn verify(&self, local_count: u16, function_count: u16) -> Result<(), VerifyError> {
        let len = self.instructions.len();
        // visited[pc] = Hoehe beim ersten Besuch; height
        let mut visited: Vec<Option<usize>> = vec![None; len];
        // last_const beim ersten Besuch; bei Join mit abweichendem Wert -> None
        let mut last_const_at: Vec<Option<i64>> = vec![None; len];
        // Worklist: (pc, hoehe, last_const) — deterministisch (fester Stack-Order).
        let mut work: Vec<(usize, usize, Option<i64>)> = vec![(0, 0, None)];
        while let Some((pc, stack, last_const)) = work.pop() {
            match visited[pc] {
                Some(h) => {
                    if h != stack {
                        return Err(VerifyError::InconsistentStackHeight {
                            pc,
                            first: h,
                            second: stack,
                        });
                    }
                    if last_const_at[pc] != last_const {
                        // Konservative Schwaechung: Div/0-Fang bleibt pfadgenau,
                        // an uneinheitlichen Joins wird er aufgegeben (dynamisch
                        // faengt die VM weiter fail-closed).
                        last_const_at[pc] = None;
                    }
                    continue;
                }
                None => {
                    visited[pc] = Some(stack);
                    last_const_at[pc] = last_const;
                }
            }
            let Some(instruction) = self.instructions.get(pc) else {
                // pc == len: Pfad laeuft ohne Return aus — wie zuvor kein
                // Verifizierer-Fehler; die VM behandelt das fail-closed.
                continue;
            };
            match instruction {
                Instruction::ConstI64(v) => {
                    work.push((pc + 1, stack + 1, Some(*v)));
                }
                Instruction::LoadLocal(index) => {
                    if *index >= local_count {
                        return Err(VerifyError::InvalidLocal { pc, index: *index });
                    }
                    work.push((pc + 1, stack + 1, None));
                }
                Instruction::StoreLocal(index) => {
                    if *index >= local_count {
                        return Err(VerifyError::InvalidLocal { pc, index: *index });
                    }
                    if stack < 1 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    work.push((pc + 1, stack - 1, None));
                }
                Instruction::Add | Instruction::Sub | Instruction::Mul => {
                    if stack < 2 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    work.push((pc + 1, stack - 1, None));
                }
                Instruction::Div => {
                    if last_const == Some(0) {
                        return Err(VerifyError::DivisionByZeroConstant { pc });
                    }
                    if stack < 2 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    work.push((pc + 1, stack - 1, None));
                }
                Instruction::Neg => {
                    if stack < 1 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    work.push((pc + 1, stack, None));
                }
                Instruction::Eq
                | Instruction::Ne
                | Instruction::Lt
                | Instruction::Gt
                | Instruction::Le
                | Instruction::Ge => {
                    if stack < 2 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    work.push((pc + 1, stack - 1, None));
                }
                Instruction::Call { function, argc } => {
                    if *function >= function_count {
                        return Err(VerifyError::InvalidFunction {
                            pc,
                            function: *function,
                        });
                    }
                    let argc = *argc as usize;
                    if stack < argc {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    work.push((pc + 1, stack - argc + 1, None));
                }
                Instruction::Return => {
                    if stack != 1 {
                        return Err(VerifyError::InvalidStackHeight {
                            pc,
                            expected: 1,
                            actual: stack,
                        });
                    }
                    // Kein Nachfolger.
                }
                Instruction::Pop => {
                    if stack < 1 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    work.push((pc + 1, stack - 1, None));
                }
                Instruction::Jump(d) => {
                    let target = Self::jump_target(pc, *d);
                    if target < 0 || target >= len as i64 {
                        return Err(VerifyError::InvalidJumpTarget { pc, target });
                    }
                    work.push((target as usize, stack, last_const));
                }
                Instruction::JumpIfFalse(d) => {
                    if stack < 1 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    let target = Self::jump_target(pc, *d);
                    if target < 0 || target >= len as i64 {
                        return Err(VerifyError::InvalidJumpTarget { pc, target });
                    }
                    // Bedingung wird in beiden Zweigen gepop -> Hoehe -1.
                    // Reihenfolge (Determinismus): erst Sprungziel, dann Fall-through.
                    work.push((target as usize, stack - 1, None));
                    work.push((pc + 1, stack - 1, None));
                }
            }
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encoding_is_deterministic() {
        let bc = Bytecode {
            instructions: vec![Instruction::ConstI64(42), Instruction::Return],
        };
        assert_eq!(bc.encode(), bc.encode());
        assert_eq!(&bc.encode()[..6], b"ATCB\x01\x00");
    }

    #[test]
    fn encoding_spruenge_und_vergleiche() {
        let bc = Bytecode {
            instructions: vec![
                Instruction::ConstI64(1),
                Instruction::ConstI64(2),
                Instruction::Lt,
                Instruction::JumpIfFalse(1),
                Instruction::Pop,
                Instruction::Jump(-5),
                Instruction::ConstI64(0),
                Instruction::Return,
            ],
        };
        let enc = bc.encode();
        assert_eq!(&enc[..4], b"ATCB");
        // JumpIfFalse(1): 0x41 + i16 LE; Jump(-5): 0x40 + i16 LE
        // Layout: Header 10B, ConstI64 je 9B, Lt 1B -> JumpIfFalse-Opcode bei 29.
        assert_eq!(enc[29], 0x41);
        assert_eq!(&enc[30..32], &1i16.to_le_bytes());
        assert_eq!(enc[33], 0x40);
        assert_eq!(&enc[34..36], &(-5i16).to_le_bytes());
    }

    #[test]
    fn verifier_accepts_simple_return() {
        let bc = Bytecode {
            instructions: vec![Instruction::ConstI64(42), Instruction::Return],
        };
        assert!(bc.verify(0, 1).is_ok());
    }

    #[test]
    fn verifier_rejects_stack_underflow() {
        let bc = Bytecode {
            instructions: vec![Instruction::Add],
        };
        assert_eq!(bc.verify(0, 1), Err(VerifyError::StackUnderflow { pc: 0 }));
    }

    #[test]
    fn verifier_rejects_invalid_local() {
        let bc = Bytecode {
            instructions: vec![Instruction::LoadLocal(2)],
        };
        assert_eq!(
            bc.verify(1, 1),
            Err(VerifyError::InvalidLocal { pc: 0, index: 2 })
        );
    }

    #[test]
    fn verifier_rejects_jump_target_out_of_bounds() {
        let bc = Bytecode {
            instructions: vec![Instruction::Jump(100)],
        };
        assert_eq!(
            bc.verify(0, 1),
            Err(VerifyError::InvalidJumpTarget { pc: 0, target: 101 })
        );
    }

    #[test]
    fn verifier_rejects_jumpif_false_underflow() {
        let bc = Bytecode {
            instructions: vec![Instruction::JumpIfFalse(0)],
        };
        assert_eq!(bc.verify(0, 1), Err(VerifyError::StackUnderflow { pc: 0 }));
    }

    #[test]
    fn verifier_akzeptiert_while_form() {
        // Kanonische While-Form des Lowerings: Ruecksprung zum Cond-Start (pc0),
        // Join an pc0 konsistent (h0 == h0), Exit faellt auf Const+Return mit h1.
        let bc = Bytecode {
            instructions: vec![
                Instruction::ConstI64(1),    // 0: cond (h0 -> 1)
                Instruction::JumpIfFalse(3), // 1: Ziel pc5 (h0), Fall pc2 (h0)
                Instruction::ConstI64(0),    // 2: Body-Ausdruck
                Instruction::Pop,            // 3: Body laesst Stack 0
                Instruction::Jump(-5),       // 4: Ruecksprung zu pc0 (h0)
                Instruction::ConstI64(42),   // 5: Exit-Wert (h1)
                Instruction::Return,         // 6: (h1)
            ],
        };
        assert!(bc.verify(0, 1).is_ok());
    }
    #[test]
    fn verifier_rejects_widerspruechliche_hoehen_an_join() {
        // Join bei pc4: Fall-through-Pfad erreicht ihn mit Hoehe 2 (pc2/pc3),
        // Sprungziel-Pfad mit Hoehe 0 -> Widerspruch am Join.
        let bc = Bytecode {
            instructions: vec![
                Instruction::ConstI64(1),    // 0: h1
                Instruction::JumpIfFalse(2), // 1: Ziel pc4 (h0), Fall pc2 (h0)
                Instruction::ConstI64(7),    // 2: h1
                Instruction::ConstI64(9),    // 3: h2 -> pc4
                Instruction::Pop,            // 4: JOIN (zuerst h2 besucht, dann h0)
                Instruction::Return,         // 5: h1 OK
            ],
        };
        let err = bc.verify(0, 1);
        assert!(matches!(
            err,
            Err(VerifyError::InconsistentStackHeight {
                pc: 4,
                first: 2,
                second: 0,
            })
        ));
    }
}
