// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Canonical ATCLang bytecode format and verifier (G3 baseline, SCR-0128 Stufe 1).
//! Legacy encoding is deterministic and little-endian. The canonical encoding
//! below is a separate wire contract: fixed opcode bytes and big-endian
//! immediates, with no host-dependent serialization.
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
    EmptyBytecode,
    UnexpectedEnd {
        pc: usize,
    },
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
    /// Control-flow path ends without an explicit Return.
    MissingReturn {
        pc: usize,
    },
    /// Sprungziel ausserhalb [0, len].
    InvalidJumpTarget {
        pc: usize,
        target: i64,
    },
    /// Instruction count cannot be represented by the canonical u32 field.
    InstructionCountOverflow,
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
    /// LEGACY / NON-CANONICAL: Little-Endian-Encoder (historisch).
    /// Kanonische Serialisierung ist ausschliesslich `encode_canonical()`
    /// (ATC-BC-001 v1.0.0-FROZEN, ATCB v1, big-endian).
    /// Nicht als kanonisches Format referenzieren. Entfernung nur per
    /// Gate-0-Folgecommit nach bestaetigter Nichtnutzung.
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

    /// Canonical deterministic binary encoding.
    ///
    /// Format:
    /// magic "ATCB", version u16 BE, instruction_count u32 BE,
    /// followed by fixed opcode payloads. This deliberately avoids serde/JSON.
    ///
    /// A standalone bytecode object does not know its containing program's
    /// local count or function signature table. We derive the minimum local
    /// count from the bytecode and use unknown call signatures here.
    /// Full program validation remains the responsibility of
    /// `CompiledProgram::verify()`.
    pub fn encode_canonical(&self) -> Result<Vec<u8>, VerifyError> {
        let local_count = self
            .instructions
            .iter()
            .filter_map(|ins| match ins {
                Instruction::LoadLocal(i) | Instruction::StoreLocal(i) => Some(*i),
                _ => None,
            })
            .max()
            .map_or(0, |i| i.saturating_add(1));
        self.verify(local_count, u16::MAX)?;
        let instruction_count = u32::try_from(self.instructions.len())
            .map_err(|_| VerifyError::InstructionCountOverflow)?;
        let mut out =
            Vec::with_capacity(10usize.saturating_add(self.instructions.len().saturating_mul(9)));
        out.extend_from_slice(b"ATCB");
        out.extend_from_slice(&1u16.to_be_bytes());
        out.extend_from_slice(&instruction_count.to_be_bytes());
        for ins in &self.instructions {
            match ins {
                Instruction::ConstI64(v) => {
                    out.push(0x01);
                    out.extend_from_slice(&v.to_be_bytes());
                }
                Instruction::LoadLocal(i) => {
                    out.push(0x02);
                    out.extend_from_slice(&i.to_be_bytes());
                }
                Instruction::StoreLocal(i) => {
                    out.push(0x03);
                    out.extend_from_slice(&i.to_be_bytes());
                }
                Instruction::Add => out.push(0x10),
                Instruction::Sub => out.push(0x11),
                Instruction::Mul => out.push(0x12),
                Instruction::Div => out.push(0x13),
                Instruction::Neg => out.push(0x14),
                Instruction::Eq => out.push(0x15),
                Instruction::Ne => out.push(0x16),
                Instruction::Lt => out.push(0x17),
                Instruction::Gt => out.push(0x18),
                Instruction::Le => out.push(0x19),
                Instruction::Ge => out.push(0x1A),
                Instruction::Call { function, argc } => {
                    out.push(0x20);
                    out.extend_from_slice(&function.to_be_bytes());
                    out.extend_from_slice(&argc.to_be_bytes());
                }
                Instruction::Return => out.push(0x21),
                Instruction::Jump(delta) => {
                    out.push(0x30);
                    out.extend_from_slice(&delta.to_be_bytes());
                }
                Instruction::JumpIfFalse(delta) => {
                    out.push(0x31);
                    out.extend_from_slice(&delta.to_be_bytes());
                }
                Instruction::Pop => out.push(0x40),
            }
        }
        Ok(out)
    }

    pub fn verify(&self, local_count: u16, function_count: u16) -> Result<(), VerifyError> {
        self.verify_with_signatures(local_count, &vec![u16::MAX; function_count as usize])
    }

    /// Full verifier including exact call arity when function signatures are available.
    pub fn verify_with_signatures(
        &self,
        local_count: u16,
        function_params: &[u16],
    ) -> Result<(), VerifyError> {
        let len = self.instructions.len();
        if len == 0 {
            return Err(VerifyError::EmptyBytecode);
        }
        // visited[pc] = Hoehe beim ersten Besuch; height
        let mut visited: Vec<Option<usize>> = vec![None; len];
        // last_const beim ersten Besuch; bei Join mit abweichendem Wert -> None
        let mut last_const_at: Vec<Option<i64>> = vec![None; len];
        // Worklist: (pc, hoehe, last_const) — deterministisch (fester Stack-Order).
        let mut work: Vec<(usize, usize, Option<i64>)> = vec![(0, 0, None)];
        while let Some((pc, stack, last_const)) = work.pop() {
            if pc >= len {
                return Err(VerifyError::UnexpectedEnd { pc });
            }
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
            let instruction = &self.instructions[pc];
            match instruction {
                Instruction::ConstI64(v) => {
                    let next_stack =
                        stack
                            .checked_add(1)
                            .ok_or(VerifyError::InvalidStackHeight {
                                pc,
                                expected: usize::MAX,
                                actual: stack,
                            })?;
                    if pc + 1 >= len {
                        return Err(VerifyError::MissingReturn { pc });
                    }
                    work.push((pc + 1, next_stack, Some(*v)));
                }
                Instruction::LoadLocal(index) => {
                    if *index >= local_count {
                        return Err(VerifyError::InvalidLocal { pc, index: *index });
                    }
                    let next_stack =
                        stack
                            .checked_add(1)
                            .ok_or(VerifyError::InvalidStackHeight {
                                pc,
                                expected: usize::MAX,
                                actual: stack,
                            })?;
                    if pc + 1 >= len {
                        return Err(VerifyError::MissingReturn { pc });
                    }
                    work.push((pc + 1, next_stack, None));
                }
                Instruction::StoreLocal(index) => {
                    if *index >= local_count {
                        return Err(VerifyError::InvalidLocal { pc, index: *index });
                    }
                    if stack < 1 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    if pc + 1 >= len {
                        return Err(VerifyError::MissingReturn { pc });
                    }
                    work.push((pc + 1, stack - 1, None));
                }
                Instruction::Add | Instruction::Sub | Instruction::Mul => {
                    if stack < 2 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    if pc + 1 >= len {
                        return Err(VerifyError::MissingReturn { pc });
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
                    if pc + 1 >= len {
                        return Err(VerifyError::MissingReturn { pc });
                    }
                    work.push((pc + 1, stack - 1, None));
                }
                Instruction::Neg => {
                    if stack < 1 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    if pc + 1 >= len {
                        return Err(VerifyError::MissingReturn { pc });
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
                    if pc + 1 >= len {
                        return Err(VerifyError::MissingReturn { pc });
                    }
                    work.push((pc + 1, stack - 1, None));
                }
                Instruction::Call { function, argc } => {
                    if (*function as usize) >= function_params.len() {
                        return Err(VerifyError::InvalidFunction {
                            pc,
                            function: *function,
                        });
                    }
                    let argc = *argc as usize;
                    let expected = function_params[*function as usize];
                    if expected != u16::MAX && argc != usize::from(expected) {
                        return Err(VerifyError::InvalidFunction {
                            pc,
                            function: *function,
                        });
                    }
                    if stack < argc {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    if pc + 1 >= len {
                        return Err(VerifyError::MissingReturn { pc });
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
                    if pc + 1 >= len {
                        return Err(VerifyError::MissingReturn { pc });
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
    fn canonical_encoding_is_stable_and_big_endian() {
        let bc = Bytecode {
            instructions: vec![
                Instruction::ConstI64(0x0102030405060708),
                Instruction::Return,
            ],
        };
        let encoded = bc.encode_canonical().unwrap();
        assert_eq!(&encoded[..10], b"ATCB\x00\x01\x00\x00\x00\x02");
        assert_eq!(encoded[10], 0x01);
        assert_eq!(&encoded[11..19], &0x0102030405060708i64.to_be_bytes());
        assert_eq!(encoded[19], 0x21);
    }

    #[test]
    fn canonical_encoding_covers_all_comparison_opcodes() {
        let bc = Bytecode {
            instructions: vec![
                Instruction::ConstI64(1),
                Instruction::ConstI64(2),
                Instruction::Ne,
                Instruction::Pop,
                Instruction::ConstI64(1),
                Instruction::ConstI64(2),
                Instruction::Lt,
                Instruction::Pop,
                Instruction::ConstI64(1),
                Instruction::ConstI64(2),
                Instruction::Gt,
                Instruction::Pop,
                Instruction::ConstI64(1),
                Instruction::ConstI64(2),
                Instruction::Le,
                Instruction::Pop,
                Instruction::ConstI64(1),
                Instruction::ConstI64(2),
                Instruction::Ge,
                Instruction::Return,
            ],
        };
        let encoded = bc.encode_canonical().unwrap();
        for opcode in [0x16u8, 0x17, 0x18, 0x19, 0x1A] {
            assert!(
                encoded.contains(&opcode),
                "missing canonical opcode {opcode:#x}"
            );
        }
    }

    #[test]
    fn verifier_rejects_fallthrough_past_end() {
        let bc = Bytecode {
            instructions: vec![Instruction::ConstI64(1)],
        };
        assert_eq!(bc.verify(0, 1), Err(VerifyError::MissingReturn { pc: 0 }));
    }

    #[test]
    fn verifier_rejects_empty_bytecode() {
        let bc = Bytecode {
            instructions: vec![],
        };
        assert_eq!(bc.verify(0, 1), Err(VerifyError::EmptyBytecode));
    }

    #[test]
    fn verifier_checks_call_arity_when_signatures_are_known() {
        let bc = Bytecode {
            instructions: vec![
                Instruction::ConstI64(1),
                Instruction::Call {
                    function: 0,
                    argc: 1,
                },
                Instruction::Return,
            ],
        };
        assert_eq!(
            bc.verify_with_signatures(0, &[2]),
            Err(VerifyError::InvalidFunction { pc: 1, function: 0 })
        );
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
