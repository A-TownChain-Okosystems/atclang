// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Canonical ATCA artifact envelope.
//! Raw bytecode is not an L1-trusted artifact until this envelope,
//! canonical encoding and SHA-256 binding have been verified.

use crate::bytecode::{Bytecode, Instruction, VerifyError};
use crate::lower::{CompiledFunction, CompiledProgram};
use sha2::{Digest, Sha256};

pub const ATCA_MAGIC: &[u8; 4] = b"ATCA";
pub const ATCA_VERSION: u16 = 1;
pub const MAX_STRING_BYTES: usize = 255;
pub const MAX_CAPABILITIES: usize = 64;
pub const MAX_ARTIFACT_BYTES: usize = 16 * 1024 * 1024;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArtifactMetadata {
    pub language_version: String,
    pub compiler_version: String,
    pub target_profile: String,
    /// Must already be lexicographically sorted and duplicate-free.
    pub capabilities: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArtifactFunction {
    pub name: String,
    pub param_count: u16,
    pub local_count: u16,
    pub bytecode: Bytecode,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Artifact {
    pub metadata: ArtifactMetadata,
    pub entry: u16,
    pub functions: Vec<ArtifactFunction>,
    pub hash: [u8; 32],
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct VerifiedArtifact {
    artifact: Artifact,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ArtifactError {
    InvalidMagic,
    UnsupportedVersion(u16),
    Truncated,
    TrailingBytes,
    InvalidUtf8,
    StringTooLong,
    TooManyCapabilities,
    CapabilitiesNotCanonical,
    InvalidCount,
    InvalidInstruction,
    InvalidBytecode(VerifyError),
    InvalidProgram(String),
    HashMismatch,
    ArtifactTooLarge,
}

impl From<VerifyError> for ArtifactError {
    fn from(value: VerifyError) -> Self {
        Self::InvalidBytecode(value)
    }
}

impl Artifact {
    pub fn from_program(
        program: &CompiledProgram,
        metadata: ArtifactMetadata,
    ) -> Result<Self, ArtifactError> {
        program
            .verify()
            .map_err(|e| ArtifactError::InvalidProgram(e.message))?;
        validate_metadata(&metadata)?;
        if program.functions.len() > u16::MAX as usize {
            return Err(ArtifactError::InvalidCount);
        }
        let functions = program
            .functions
            .iter()
            .map(|f| ArtifactFunction {
                name: f.name.clone(),
                param_count: f.param_count,
                local_count: f.local_count,
                bytecode: f.bytecode.clone(),
            })
            .collect();
        let mut artifact = Self {
            metadata,
            entry: program.entry,
            functions,
            hash: [0; 32],
        };
        artifact.hash = artifact.compute_hash()?;
        Ok(artifact)
    }

    /// Canonical bytes covered by the artifact hash. The hash itself is
    /// deliberately excluded from this payload.
    pub fn canonical_payload(&self) -> Result<Vec<u8>, ArtifactError> {
        validate_artifact(self)?;
        let mut out = Vec::with_capacity(1024);
        out.extend_from_slice(ATCA_MAGIC);
        out.extend_from_slice(&ATCA_VERSION.to_be_bytes());
        put_string(&mut out, &self.metadata.language_version)?;
        put_string(&mut out, &self.metadata.compiler_version)?;
        put_string(&mut out, &self.metadata.target_profile)?;
        put_u16(&mut out, self.metadata.capabilities.len())?;
        for capability in &self.metadata.capabilities {
            put_string(&mut out, capability)?;
        }
        out.extend_from_slice(&self.entry.to_be_bytes());
        put_u16(&mut out, self.functions.len())?;
        for function in &self.functions {
            put_string(&mut out, &function.name)?;
            out.extend_from_slice(&function.param_count.to_be_bytes());
            out.extend_from_slice(&function.local_count.to_be_bytes());
            let bytecode = function.bytecode.encode_canonical()?;
            let len = u32::try_from(bytecode.len()).map_err(|_| ArtifactError::InvalidCount)?;
            out.extend_from_slice(&len.to_be_bytes());
            out.extend_from_slice(&bytecode);
        }
        if out.len() > MAX_ARTIFACT_BYTES {
            return Err(ArtifactError::ArtifactTooLarge);
        }
        Ok(out)
    }

    pub fn compute_hash(&self) -> Result<[u8; 32], ArtifactError> {
        Ok(Sha256::digest(self.canonical_payload()?).into())
    }

    pub fn encode(&self) -> Result<Vec<u8>, ArtifactError> {
        let mut out = self.canonical_payload()?;
        out.extend_from_slice(&self.hash);
        Ok(out)
    }

    pub fn verify(&self) -> Result<VerifiedArtifact, ArtifactError> {
        validate_artifact(self)?;
        if self.compute_hash()? != self.hash {
            return Err(ArtifactError::HashMismatch);
        }
        Ok(VerifiedArtifact {
            artifact: self.clone(),
        })
    }

    /// Parse untrusted bytes and verify all structure, bytecode and hash
    /// before returning the trusted wrapper.
    pub fn decode_and_verify(bytes: &[u8]) -> Result<VerifiedArtifact, ArtifactError> {
        if bytes.len() > MAX_ARTIFACT_BYTES {
            return Err(ArtifactError::ArtifactTooLarge);
        }
        let mut r = Reader::new(bytes);
        if r.take(4)? != ATCA_MAGIC {
            return Err(ArtifactError::InvalidMagic);
        }
        let version = r.u16()?;
        if version != ATCA_VERSION {
            return Err(ArtifactError::UnsupportedVersion(version));
        }

        let metadata = ArtifactMetadata {
            language_version: r.string()?,
            compiler_version: r.string()?,
            target_profile: r.string()?,
            capabilities: {
                let count = r.u16()? as usize;
                if count > MAX_CAPABILITIES {
                    return Err(ArtifactError::TooManyCapabilities);
                }
                let mut values = Vec::with_capacity(count);
                for _ in 0..count {
                    values.push(r.string()?);
                }
                values
            },
        };
        validate_metadata(&metadata)?;

        let entry = r.u16()?;
        let count = r.u16()? as usize;
        // A function has at least name-length + params + locals + bytecode-length.
        if count > r.remaining() / 10 {
            return Err(ArtifactError::InvalidCount);
        }
        let mut functions = Vec::with_capacity(count);
        for _ in 0..count {
            let name = r.string()?;
            let param_count = r.u16()?;
            let local_count = r.u16()?;
            let bytecode_len = r.u32()? as usize;
            if bytecode_len > r.remaining() {
                return Err(ArtifactError::Truncated);
            }
            let raw = r.take(bytecode_len)?;
            let bytecode = decode_bytecode(raw)?;
            functions.push(ArtifactFunction {
                name,
                param_count,
                local_count,
                bytecode,
            });
        }

        let hash_bytes = r.take(32)?;
        if r.remaining() != 0 {
            return Err(ArtifactError::TrailingBytes);
        }
        let mut hash = [0u8; 32];
        hash.copy_from_slice(hash_bytes);

        Artifact {
            metadata,
            entry,
            functions,
            hash,
        }
        .verify()
    }

    pub fn into_program(&self) -> Result<CompiledProgram, ArtifactError> {
        let verified = self.verify()?;
        Ok(verified.artifact_to_program())
    }
}

impl VerifiedArtifact {
    pub fn metadata(&self) -> &ArtifactMetadata {
        &self.artifact.metadata
    }

    pub fn artifact_hash(&self) -> [u8; 32] {
        self.artifact.hash
    }

    pub fn into_program(self) -> CompiledProgram {
        self.artifact_to_program()
    }

    fn artifact_to_program(&self) -> CompiledProgram {
        CompiledProgram {
            functions: self
                .artifact
                .functions
                .iter()
                .map(|f| CompiledFunction {
                    name: f.name.clone(),
                    param_count: f.param_count,
                    local_count: f.local_count,
                    bytecode: f.bytecode.clone(),
                })
                .collect(),
            entry: self.artifact.entry,
        }
    }
}

fn validate_metadata(metadata: &ArtifactMetadata) -> Result<(), ArtifactError> {
    validate_string(&metadata.language_version)?;
    validate_string(&metadata.compiler_version)?;
    validate_string(&metadata.target_profile)?;
    if metadata.capabilities.len() > MAX_CAPABILITIES {
        return Err(ArtifactError::TooManyCapabilities);
    }
    if metadata.capabilities.windows(2).any(|w| w[0] >= w[1]) {
        return Err(ArtifactError::CapabilitiesNotCanonical);
    }
    for capability in &metadata.capabilities {
        validate_string(capability)?;
    }
    Ok(())
}

fn validate_string(value: &str) -> Result<(), ArtifactError> {
    if value.len() > MAX_STRING_BYTES {
        return Err(ArtifactError::StringTooLong);
    }
    Ok(())
}

fn validate_artifact(artifact: &Artifact) -> Result<(), ArtifactError> {
    validate_metadata(&artifact.metadata)?;
    if artifact.functions.is_empty() || artifact.functions.len() > u16::MAX as usize {
        return Err(ArtifactError::InvalidCount);
    }
    if artifact.entry as usize >= artifact.functions.len() {
        return Err(ArtifactError::InvalidProgram("invalid entry".into()));
    }
    let signatures: Vec<u16> = artifact.functions.iter().map(|f| f.param_count).collect();
    for f in &artifact.functions {
        validate_string(&f.name)?;
        if f.param_count > f.local_count {
            return Err(ArtifactError::InvalidProgram(format!(
                "function {} has more parameters than locals",
                f.name
            )));
        }
        f.bytecode
            .verify_with_signatures(f.local_count, &signatures)?;
    }
    Ok(())
}

fn put_string(out: &mut Vec<u8>, value: &str) -> Result<(), ArtifactError> {
    validate_string(value)?;
    out.extend_from_slice(&(value.len() as u16).to_be_bytes());
    out.extend_from_slice(value.as_bytes());
    Ok(())
}

fn put_u16(out: &mut Vec<u8>, value: usize) -> Result<(), ArtifactError> {
    let value = u16::try_from(value).map_err(|_| ArtifactError::InvalidCount)?;
    out.extend_from_slice(&value.to_be_bytes());
    Ok(())
}

struct Reader<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> Reader<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, pos: 0 }
    }

    fn remaining(&self) -> usize {
        self.bytes.len().saturating_sub(self.pos)
    }

    fn take(&mut self, n: usize) -> Result<&'a [u8], ArtifactError> {
        if n > self.remaining() {
            return Err(ArtifactError::Truncated);
        }
        let start = self.pos;
        self.pos += n;
        Ok(&self.bytes[start..self.pos])
    }

    fn u16(&mut self) -> Result<u16, ArtifactError> {
        let b = self.take(2)?;
        Ok(u16::from_be_bytes([b[0], b[1]]))
    }

    fn u32(&mut self) -> Result<u32, ArtifactError> {
        let b = self.take(4)?;
        Ok(u32::from_be_bytes([b[0], b[1], b[2], b[3]]))
    }

    fn string(&mut self) -> Result<String, ArtifactError> {
        let len = self.u16()? as usize;
        let bytes = self.take(len)?;
        String::from_utf8(bytes.to_vec()).map_err(|_| ArtifactError::InvalidUtf8)
    }
}

fn decode_bytecode(raw: &[u8]) -> Result<Bytecode, ArtifactError> {
    if raw.len() < 10 || &raw[..4] != b"ATCB" {
        return Err(ArtifactError::InvalidMagic);
    }
    if u16::from_be_bytes([raw[4], raw[5]]) != 1 {
        return Err(ArtifactError::UnsupportedVersion(u16::from_be_bytes([
            raw[4], raw[5],
        ])));
    }
    let count = u32::from_be_bytes([raw[6], raw[7], raw[8], raw[9]]) as usize;
    let remaining = raw.len().saturating_sub(10);
    // Every instruction consumes at least one opcode byte. Do not allocate
    // from an attacker-controlled count before this structural bound.
    if count > remaining {
        return Err(ArtifactError::InvalidCount);
    }
    let mut p = 10usize;
    let mut instructions = Vec::with_capacity(count);

    for _ in 0..count {
        let opcode = *raw.get(p).ok_or(ArtifactError::Truncated)?;
        p += 1;
        let ins = match opcode {
            0x01 => Instruction::ConstI64(read_i64(raw, &mut p)?),
            0x02 => Instruction::LoadLocal(read_u16(raw, &mut p)?),
            0x03 => Instruction::StoreLocal(read_u16(raw, &mut p)?),
            0x10 => Instruction::Add,
            0x11 => Instruction::Sub,
            0x12 => Instruction::Mul,
            0x13 => Instruction::Div,
            0x14 => Instruction::Neg,
            0x15 => Instruction::Eq,
            0x16 => Instruction::Ne,
            0x17 => Instruction::Lt,
            0x18 => Instruction::Gt,
            0x19 => Instruction::Le,
            0x1A => Instruction::Ge,
            0x20 => Instruction::Call {
                function: read_u16(raw, &mut p)?,
                argc: read_u16(raw, &mut p)?,
            },
            0x21 => Instruction::Return,
            0x30 => Instruction::Jump(read_i16(raw, &mut p)?),
            0x31 => Instruction::JumpIfFalse(read_i16(raw, &mut p)?),
            0x40 => Instruction::Pop,
            _ => return Err(ArtifactError::InvalidInstruction),
        };
        instructions.push(ins);
    }
    if p != raw.len() {
        return Err(ArtifactError::TrailingBytes);
    }
    Ok(Bytecode { instructions })
}

fn read_u16(raw: &[u8], p: &mut usize) -> Result<u16, ArtifactError> {
    if *p + 2 > raw.len() {
        return Err(ArtifactError::Truncated);
    }
    let value = u16::from_be_bytes([raw[*p], raw[*p + 1]]);
    *p += 2;
    Ok(value)
}

fn read_i16(raw: &[u8], p: &mut usize) -> Result<i16, ArtifactError> {
    Ok(read_u16(raw, p)? as i16)
}

fn read_i64(raw: &[u8], p: &mut usize) -> Result<i64, ArtifactError> {
    if *p + 8 > raw.len() {
        return Err(ArtifactError::Truncated);
    }
    let mut b = [0u8; 8];
    b.copy_from_slice(&raw[*p..*p + 8]);
    *p += 8;
    Ok(i64::from_be_bytes(b))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_program() -> CompiledProgram {
        CompiledProgram {
            functions: vec![CompiledFunction {
                name: "__main__".into(),
                param_count: 0,
                local_count: 0,
                bytecode: Bytecode {
                    instructions: vec![Instruction::ConstI64(42), Instruction::Return],
                },
            }],
            entry: 0,
        }
    }

    fn metadata() -> ArtifactMetadata {
        ArtifactMetadata {
            language_version: "1.0".into(),
            compiler_version: "atc-core-0.1.0".into(),
            target_profile: "l1-deterministic-v1".into(),
            capabilities: vec!["state.read".into(), "state.write".into()],
        }
    }

    #[test]
    fn artifact_hash_is_deterministic() {
        let a = Artifact::from_program(&sample_program(), metadata()).unwrap();
        let b = Artifact::from_program(&sample_program(), metadata()).unwrap();
        assert_eq!(a.hash, b.hash);
        assert_eq!(a.encode().unwrap(), b.encode().unwrap());
    }

    #[test]
    fn artifact_round_trip_verifies() {
        let a = Artifact::from_program(&sample_program(), metadata()).unwrap();
        let bytes = a.encode().unwrap();
        let verified = Artifact::decode_and_verify(&bytes).unwrap();
        assert_eq!(verified.artifact_hash(), a.hash);
        assert_eq!(verified.into_program(), sample_program());
    }

    #[test]
    fn tampered_artifact_is_rejected() {
        let a = Artifact::from_program(&sample_program(), metadata()).unwrap();
        let mut bytes = a.encode().unwrap();
        let last_hash_byte = bytes.len() - 1;
        bytes[last_hash_byte] ^= 1;
        assert_eq!(
            Artifact::decode_and_verify(&bytes),
            Err(ArtifactError::HashMismatch)
        );
    }

    #[test]
    fn capabilities_must_be_canonical() {
        let mut m = metadata();
        m.capabilities.reverse();
        assert_eq!(
            Artifact::from_program(&sample_program(), m),
            Err(ArtifactError::CapabilitiesNotCanonical)
        );
    }
}
