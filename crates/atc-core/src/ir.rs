// Copyright (c) 2026 A-TownChain-Okosystems — Apache-2.0
//! Canonical ATC-IR type/value boundary.
//!
//! ATC-IR keeps contract-visible ABI values separate from protocol/host
//! metadata. The IR may carry either category, but their semantic domains
//! remain distinct so a protocol counter cannot accidentally become an
//! economic contract value.

use crate::value::{AbiType, TypedValue};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum ProtocolType {
    Height,
    Nonce,
    Timestamp,
    Epoch,
    ProgramCounter,
    Gas,
}

impl ProtocolType {
    pub const fn host_type(self) -> &'static str {
        "u64"
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum IrType {
    Abi(AbiType),
    Protocol(ProtocolType),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IrValue {
    Abi(TypedValue),
    Protocol { ty: ProtocolType, value: u64 },
}

impl IrValue {
    pub fn ir_type(&self) -> IrType {
        match self {
            Self::Abi(value) => IrType::Abi(value.abi_type()),
            Self::Protocol { ty, .. } => IrType::Protocol(*ty),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn economic_values_use_abi_domain() {
        let value = IrValue::Abi(TypedValue::U128(360_000_000_000_000_000_000_000_000));
        assert_eq!(value.ir_type(), IrType::Abi(AbiType::U128));
    }

    #[test]
    fn protocol_counters_use_separate_u64_domain() {
        let height = IrValue::Protocol {
            ty: ProtocolType::Height,
            value: 42,
        };
        assert_eq!(height.ir_type(), IrType::Protocol(ProtocolType::Height));
        assert_eq!(ProtocolType::Height.host_type(), "u64");
    }

    #[test]
    fn abi_and_protocol_domains_are_not_interchangeable() {
        let economic = IrType::Abi(AbiType::U128);
        let height = IrType::Protocol(ProtocolType::Height);
        assert_ne!(economic, height);
    }
}
