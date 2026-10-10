// Copyright (c) 2026 A-TownChain-Okosystems — Apache-2.0
//! Canonical ABI value contract shared by the ATCLang/IR boundary.
//!
//! This module deliberately separates:
//! - `AbiType`: the semantic contract-visible type;
//! - `TypedValue`: a typed runtime value carrying that ABI type;
//! - host/protocol metadata (height, nonce, timestamp, gas, PC, etc.), which
//!   is NOT represented here and remains a separate protocol/VM concern.
//!
//! ABI wire encoding is intentionally not implemented here. ATC-ABI-001 is
//! still draft and its canonical byte encoding is a separate conformance gate.

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AbiType {
    U64,
    U128,
    U256,
    Bool,
    Address,
    Bytes,
    ContractRef,
}

impl AbiType {
    /// Map the canonical ATCLang spelling to the ABI semantic type.
    pub fn from_name(name: &str) -> Option<Self> {
        match name {
            "u64" | "UInt64" => Some(Self::U64),
            "u128" | "UInt128" => Some(Self::U128),
            "u256" | "UInt256" => Some(Self::U256),
            "bool" | "Bool" => Some(Self::Bool),
            "Address" => Some(Self::Address),
            "bytes" | "Bytes" => Some(Self::Bytes),
            "ContractRef" => Some(Self::ContractRef),
            _ => None,
        }
    }
}

/// Host-independent 256-bit unsigned integer representation.
///
/// Limb 0 is the least-significant 64 bits. This is an internal value
/// representation; it does not define the ABI byte order.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct U256(pub [u64; 4]);

/// Contract-visible typed value.
///
/// Protocol/VM metadata such as block height, nonce, timestamp, epoch,
/// program counter and gas counters must remain outside this enum.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TypedValue {
    U64(u64),
    U128(u128),
    U256(U256),
    Bool(bool),
    /// ATC addresses are represented by the 32-byte address payload.
    Address([u8; 32]),
    Bytes(Vec<u8>),
    /// ContractRef encoding is deliberately opaque until its ABI encoding is
    /// frozen; no width or wire format is inferred here.
    ContractRef(Vec<u8>),
}

impl TypedValue {
    pub fn abi_type(&self) -> AbiType {
        match self {
            Self::U64(_) => AbiType::U64,
            Self::U128(_) => AbiType::U128,
            Self::U256(_) => AbiType::U256,
            Self::Bool(_) => AbiType::Bool,
            Self::Address(_) => AbiType::Address,
            Self::Bytes(_) => AbiType::Bytes,
            Self::ContractRef(_) => AbiType::ContractRef,
        }
    }

    pub fn is_type(&self, ty: AbiType) -> bool {
        self.abi_type() == ty
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_numeric_types_are_distinct() {
        assert_eq!(TypedValue::U64(1).abi_type(), AbiType::U64);
        assert_eq!(TypedValue::U128(1).abi_type(), AbiType::U128);
        assert_eq!(
            TypedValue::U256(U256([1, 0, 0, 0])).abi_type(),
            AbiType::U256
        );
    }

    #[test]
    fn abi_type_names_are_explicit() {
        assert_eq!(AbiType::from_name("u64"), Some(AbiType::U64));
        assert_eq!(AbiType::from_name("u128"), Some(AbiType::U128));
        assert_eq!(AbiType::from_name("u256"), Some(AbiType::U256));
        assert_eq!(AbiType::from_name("Address"), Some(AbiType::Address));
        assert_eq!(AbiType::from_name("bytes"), Some(AbiType::Bytes));
        assert_eq!(
            AbiType::from_name("ContractRef"),
            Some(AbiType::ContractRef)
        );
        assert_eq!(AbiType::from_name("height"), None);
    }

    #[test]
    fn protocol_metadata_is_not_an_abi_value() {
        assert_eq!(AbiType::from_name("height"), None);
        assert_eq!(AbiType::from_name("nonce"), None);
        assert_eq!(AbiType::from_name("timestamp"), None);
        assert_eq!(AbiType::from_name("epoch"), None);
    }

    #[test]
    fn value_type_identity_is_preserved() {
        let value = TypedValue::Address([0; 32]);
        assert!(value.is_type(AbiType::Address));
        assert!(!value.is_type(AbiType::U128));
    }
}
