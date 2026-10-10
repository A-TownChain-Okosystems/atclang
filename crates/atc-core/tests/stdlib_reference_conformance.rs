// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Referenz-Standardbibliothek (Konformanz-Referenz, ATC-STDLIB-CONTRACT-001).
//!
//! Diese Referenz-Implementierung ist REFERENCE-only: deterministische, reine
//! Funktionen fuer Differential-Konformanz. Sie ist niemals Konsens-/Runtime-
//! Vertrauensanker (ATC-RUNTIME-CLASSIFICATION-001, Rolle `reference`).
//! Ersetzt die fruehere Python-Referenz (Rust-only-Politik 2026-09-17);
//! Semantik ist identisch: Big-Endian-Wire-Format, 4-Byte-Laengenpraefix,
//! fail-closed bei Ueberlauf/Unterlauf.

use sha2::{Digest, Sha256};

// ---------------------------------------------------------------------------
// Kodierung (Wire-Format: Big-Endian, binaer)
// ---------------------------------------------------------------------------

/// Kodiert einen u128-Wert kanonisch als 16 Bytes Big-Endian.
pub fn encode_u128_be(value: u128) -> [u8; 16] {
    value.to_be_bytes()
}

/// Dekodiert genau 16 Bytes als u128 Big-Endian; sonst fail-closed.
pub fn decode_u128_be(data: &[u8]) -> u128 {
    assert_eq!(data.len(), 16, "u128 requires exactly 16 bytes");
    let mut buf = [0u8; 16];
    buf.copy_from_slice(data);
    u128::from_be_bytes(buf)
}

/// U256 als Paar (hi, lo) aus u128-Haelften — deterministisch, ohne externe Crates.
impl PartialOrd for U256 {
    fn partial_cmp(&self, other: &U256) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for U256 {
    fn cmp(&self, other: &U256) -> std::cmp::Ordering {
        (self.hi, self.lo).cmp(&(other.hi, other.lo))
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct U256 {
    pub hi: u128,
    pub lo: u128,
}

impl U256 {
    pub const ZERO: U256 = U256 { hi: 0, lo: 0 };
    pub const MAX: U256 = U256 {
        hi: u128::MAX,
        lo: u128::MAX,
    };

    /// Kodiert kanonisch als 32 Bytes Big-Endian.
    pub fn encode_be(&self) -> [u8; 32] {
        let mut out = [0u8; 32];
        out[..16].copy_from_slice(&self.hi.to_be_bytes());
        out[16..].copy_from_slice(&self.lo.to_be_bytes());
        out
    }

    /// Dekodiert genau 32 Bytes; sonst fail-closed.
    pub fn decode_be(data: &[u8]) -> U256 {
        assert_eq!(data.len(), 32, "u256 requires exactly 32 bytes");
        let mut hi = [0u8; 16];
        let mut lo = [0u8; 16];
        hi.copy_from_slice(&data[..16]);
        lo.copy_from_slice(&data[16..]);
        U256 {
            hi: u128::from_be_bytes(hi),
            lo: u128::from_be_bytes(lo),
        }
    }
}

/// Kanonische laengenpraefxierte Verkettung: je Part 4 Bytes Big-Endian-Laenge
/// + Payload. Entspricht canonical_bytes() der Referenz-Semantik.
pub fn canonical_bytes(parts: &[&[u8]]) -> Vec<u8> {
    let mut out = Vec::new();
    for part in parts {
        let len = u32::try_from(part.len()).expect("part length exceeds u32 prefix");
        out.extend_from_slice(&len.to_be_bytes());
        out.extend_from_slice(part);
    }
    out
}

// ---------------------------------------------------------------------------
// Krypto (reine Hash-Funktion; keine Signatur-/Schluesselpruefung hier)
// ---------------------------------------------------------------------------

/// SHA-256, deterministisch, ohne Host-Abhaengigkeiten.
pub fn sha256(data: &[u8]) -> [u8; 32] {
    let mut hasher = Sha256::new();
    hasher.update(data);
    let digest = hasher.finalize();
    let mut out = [0u8; 32];
    out.copy_from_slice(&digest);
    out
}

// ---------------------------------------------------------------------------
// Mathematik (overflow: fail_closed laut STDLIB-CONTRACT)
// ---------------------------------------------------------------------------

impl U256 {
    /// Ueberlauf-behaftete Addition; fail-closed statt Wrap.
    pub fn checked_add(self, other: U256) -> U256 {
        let (lo, carry) = self.lo.overflowing_add(other.lo);
        let hi = self
            .hi
            .checked_add(other.hi)
            .and_then(|h| h.checked_add(u128::from(carry)))
            .expect("u256 addition overflow");
        U256 { hi, lo }
    }

    /// Unterlauf-behaftete Subtraktion; fail-closed statt Wrap.
    pub fn checked_sub(self, other: U256) -> U256 {
        assert!(other <= self, "u256 subtraction underflow");
        let lo = self.lo.wrapping_sub(other.lo);
        let borrow = u128::from(self.lo < other.lo);
        let hi = self
            .hi
            .checked_sub(other.hi)
            .and_then(|h| h.checked_sub(borrow))
            .expect("u256 subtraction underflow");
        U256 { hi, lo }
    }
}

/// Kanonischer u128-Roundtrip-Cast (checked_cast-Semantik).
pub fn checked_cast_u128(value: u128) -> u128 {
    decode_u128_be(&encode_u128_be(value))
}

/// require(): fail-closed Bedingungspruefung.
pub fn require(condition: bool, message: &str) {
    assert!(condition, "{}", message);
}

// ---------------------------------------------------------------------------
// Konformanz-Tests (golden + negative Vektoren)
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn u128_boundaries() {
        assert_eq!(encode_u128_be(0), [0u8; 16]);
        let max = u128::MAX;
        assert_eq!(decode_u128_be(&encode_u128_be(max)), max);
    }

    #[test]
    fn u128_decode_rejects_wrong_length() {
        let result = std::panic::catch_unwind(|| decode_u128_be(&[0u8; 15]));
        assert!(result.is_err(), "decode must fail closed on wrong length");
    }

    #[test]
    fn u256_boundaries() {
        assert_eq!(U256::MAX.encode_be().len(), 32);
        let one = U256 { hi: 0, lo: 1 };
        let two = U256 { hi: 0, lo: 2 };
        let three = one.checked_add(two);
        assert_eq!(three, U256 { hi: 0, lo: 3 });
        assert_eq!(three.checked_sub(two), one);
    }

    #[test]
    fn u256_add_overflow_fails_closed() {
        let result = std::panic::catch_unwind(|| U256::MAX.checked_add(U256 { hi: 0, lo: 1 }));
        assert!(result.is_err(), "overflow must fail closed");
    }

    #[test]
    fn u256_sub_underflow_fails_closed() {
        let result = std::panic::catch_unwind(|| U256::ZERO.checked_sub(U256 { hi: 0, lo: 1 }));
        assert!(result.is_err(), "underflow must fail closed");
    }

    #[test]
    fn u256_roundtrip_max() {
        let max = U256::MAX;
        assert_eq!(U256::decode_be(&max.encode_be()), max);
    }

    #[test]
    fn canonical_bytes_is_length_delimited() {
        // Golden-Vektor identisch zur Referenz: b"a", b"bc"
        let expected: &[u8] = &[
            0, 0, 0, 1, b'a', // len=1 "a"
            0, 0, 0, 2, b'b', b'c', // len=2 "bc"
        ];
        assert_eq!(canonical_bytes(&[b"a", b"bc"]), expected);
    }

    #[test]
    fn canonical_bytes_empty_parts() {
        assert!(canonical_bytes(&[]).is_empty());
        assert_eq!(
            canonical_bytes(&[b"", b"x"]),
            &[0, 0, 0, 0, 0, 0, 0, 1, b'x']
        );
    }

    #[test]
    fn sha256_known_answer() {
        // NIST-Known-Answer-Vektor: sha256("abc")
        let expected: [u8; 32] = [
            0xba, 0x78, 0x16, 0xbf, 0x8f, 0x01, 0xcf, 0xea, 0x41, 0x41, 0x40, 0xde, 0x5d, 0xae,
            0x22, 0x23, 0xb0, 0x03, 0x61, 0xa3, 0x96, 0x17, 0x7a, 0x9c, 0xb4, 0x10, 0xff, 0x61,
            0xf2, 0x00, 0x15, 0xad,
        ];
        assert_eq!(sha256(b"abc"), expected);
    }

    #[test]
    fn checked_cast_roundtrip() {
        assert_eq!(checked_cast_u128(42), 42);
        assert_eq!(checked_cast_u128(u128::MAX), u128::MAX);
    }

    #[test]
    fn require_fails_closed() {
        let result = std::panic::catch_unwind(|| require(false, "requirement failed"));
        assert!(result.is_err());
        require(true, "ok");
    }
}
