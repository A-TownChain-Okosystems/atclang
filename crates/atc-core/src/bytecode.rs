// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Canonical ATCLang bytecode format and verifier (G3 baseline).
//! Encoding is deterministic: fixed opcode bytes, little-endian immediates,
//! no host-dependent serialization.

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
    Call { function: u16, argc: u16 },
    Return,
    Pop,
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
            Self::Call { function, argc } => {
                out.push(0x20);
                out.extend_from_slice(&function.to_le_bytes());
                out.extend_from_slice(&argc.to_le_bytes());
            }
            Self::Return => out.push(0x30),
            Self::Pop => out.push(0x31),
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

    pub fn verify(&self, local_count: u16, function_count: u16) -> Result<(), VerifyError> {
        let mut stack = 0usize;
        // Letzter Konstantenwert: faengt 'ConstI64(0), Div' (Div/0) statisch ab.
        let mut last_const: Option<i64> = None;
        for (pc, instruction) in self.instructions.iter().enumerate() {
            match instruction {
                Instruction::ConstI64(v) => {
                    last_const = Some(*v);
                    stack += 1;
                }
                Instruction::LoadLocal(index) => {
                    last_const = None;
                    if *index >= local_count {
                        return Err(VerifyError::InvalidLocal { pc, index: *index });
                    }
                    stack += 1;
                }
                Instruction::StoreLocal(index) => {
                    last_const = None;
                    if *index >= local_count {
                        return Err(VerifyError::InvalidLocal { pc, index: *index });
                    }
                    if stack < 1 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    stack -= 1;
                }
                Instruction::Add | Instruction::Sub | Instruction::Mul => {
                    last_const = None;
                    if stack < 2 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    stack -= 1;
                }
                Instruction::Div => {
                    if last_const == Some(0) {
                        return Err(VerifyError::DivisionByZeroConstant { pc });
                    }
                    last_const = None;
                    if stack < 2 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    stack -= 1;
                }
                Instruction::Neg => {
                    last_const = None;
                    if stack < 1 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                }
                Instruction::Call { function, argc } => {
                    last_const = None;
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
                    stack = stack - argc + 1;
                }
                Instruction::Return => {
                    last_const = None;
                    if stack != 1 {
                        return Err(VerifyError::InvalidStackHeight {
                            pc,
                            expected: 1,
                            actual: stack,
                        });
                    }
                }
                Instruction::Pop => {
                    last_const = None;
                    if stack < 1 {
                        return Err(VerifyError::StackUnderflow { pc });
                    }
                    stack -= 1;
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
}
