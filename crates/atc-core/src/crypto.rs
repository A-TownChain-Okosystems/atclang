// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! Canonical Rust security primitives for ATCLang production boundaries.
//!
//! This module intentionally exposes only real cryptographic operations. There
//! are no simulated signatures, permissive JWT checks, or host-dependent
//! success paths. Higher layers must bind these primitives explicitly to their
//! capability and policy boundaries.

use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
use p256::ecdsa::{signature::{Signer, Verifier}, Signature, SigningKey, VerifyingKey};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use subtle::ConstantTimeEq;
use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum CryptoError {
    #[error("invalid signing key")]
    InvalidSigningKey,
    #[error("invalid verifying key")]
    InvalidVerifyingKey,
    #[error("invalid signature")]
    InvalidSignature,
    #[error("invalid JWT structure")]
    InvalidJwtStructure,
    #[error("unsupported JWT algorithm")]
    UnsupportedJwtAlgorithm,
    #[error("invalid JWT encoding")]
    InvalidJwtEncoding,
    #[error("invalid JWT claims")]
    InvalidJwtClaims,
    #[error("JWT signature verification failed")]
    JwtSignatureMismatch,
    #[error("JWT is expired")]
    JwtExpired,
    #[error("JWT is not yet valid")]
    JwtNotYetValid,
}

/// Sign an arbitrary message with a P-256 ECDSA private key.
///
/// The returned signature is the fixed-width 64-byte IEEE-P1363 encoding
/// (`r || s`) and is base64url encoded without padding.
pub fn ecdsa_sign(message: &[u8], private_key: &[u8; 32]) -> Result<String, CryptoError> {
    let key = SigningKey::from_bytes(private_key.into()).map_err(|_| CryptoError::InvalidSigningKey)?;
    let signature: Signature = key.sign(message);
    Ok(URL_SAFE_NO_PAD.encode(signature.to_bytes()))
}

/// Verify a P-256 ECDSA signature encoded as base64url `r || s`.
pub fn ecdsa_verify(
    message: &[u8],
    signature_b64url: &str,
    public_key_sec1: &[u8],
) -> Result<bool, CryptoError> {
    let key = VerifyingKey::from_sec1_bytes(public_key_sec1)
        .map_err(|_| CryptoError::InvalidVerifyingKey)?;
    let signature_bytes = URL_SAFE_NO_PAD
        .decode(signature_b64url)
        .map_err(|_| CryptoError::InvalidSignature)?;
    let signature = Signature::from_slice(&signature_bytes).map_err(|_| CryptoError::InvalidSignature)?;
    Ok(key.verify(message, &signature).is_ok())
}

/// Derive a domain-separated ATC address from a SEC1 public key.
///
/// Address derivation is deliberately independent of host state. The digest
/// is `SHA-256("ATC-ADDRESS-V1:" || compressed-sec1-pubkey)` and is encoded
/// as `atc1` plus lowercase hexadecimal.
pub fn address_from_public_key(public_key_sec1: &[u8]) -> Result<String, CryptoError> {
    let key = VerifyingKey::from_sec1_bytes(public_key_sec1)
        .map_err(|_| CryptoError::InvalidVerifyingKey)?;
    let compressed = key.to_encoded_point(true);
    let mut hasher = Sha256::new();
    hasher.update(b"ATC-ADDRESS-V1:");
    hasher.update(compressed.as_bytes());
    Ok(format!("atc1{:x}", hasher.finalize()))
}

#[derive(Debug, Clone, Deserialize, PartialEq, Eq)]
pub struct JwtClaims {
    #[serde(default)]
    pub sub: Option<String>,
    #[serde(default)]
    pub exp: Option<u64>,
    #[serde(default)]
    pub nbf: Option<u64>,
    #[serde(default)]
    pub iat: Option<u64>,
}

#[derive(Debug, Deserialize)]
struct JwtHeader {
    alg: String,
    typ: Option<String>,
}

/// Verify an HS256 JWT with an explicit shared secret and deterministic time.
///
/// Only `HS256` is accepted. `alg=none`, algorithm confusion, malformed
/// segments, invalid claims and temporal violations are rejected. `now` is
/// supplied by the caller so consensus code never reads a host clock.
pub fn verify_hs256_jwt(
    token: &str,
    secret: &[u8],
    now: u64,
) -> Result<JwtClaims, CryptoError> {
    let mut parts = token.split('.');
    let header_b64 = parts.next().ok_or(CryptoError::InvalidJwtStructure)?;
    let claims_b64 = parts.next().ok_or(CryptoError::InvalidJwtStructure)?;
    let signature_b64 = parts.next().ok_or(CryptoError::InvalidJwtStructure)?;
    if parts.next().is_some() || header_b64.is_empty() || claims_b64.is_empty() || signature_b64.is_empty() {
        return Err(CryptoError::InvalidJwtStructure);
    }

    let header_bytes = URL_SAFE_NO_PAD.decode(header_b64).map_err(|_| CryptoError::InvalidJwtEncoding)?;
    let header: JwtHeader = serde_json::from_slice(&header_bytes).map_err(|_| CryptoError::InvalidJwtClaims)?;
    if header.alg != "HS256" || header.typ.as_deref().is_some_and(|typ| typ != "JWT") {
        return Err(CryptoError::UnsupportedJwtAlgorithm);
    }

    let claims_bytes = URL_SAFE_NO_PAD.decode(claims_b64).map_err(|_| CryptoError::InvalidJwtEncoding)?;
    let claims: JwtClaims = serde_json::from_slice(&claims_bytes).map_err(|_| CryptoError::InvalidJwtClaims)?;
    let supplied = URL_SAFE_NO_PAD.decode(signature_b64).map_err(|_| CryptoError::InvalidJwtEncoding)?;

    let signing_input = format!("{header_b64}.{claims_b64}");
    // HS256 is HMAC-SHA256, not plain SHA-256. The explicit HMAC construction
    // below avoids accidentally treating a digest as a MAC.
    let expected = hmac_sha256(secret, signing_input.as_bytes());
    if supplied.len() != expected.len() || supplied.as_slice().ct_eq(expected.as_slice()).unwrap_u8() != 1 {
        return Err(CryptoError::JwtSignatureMismatch);
    }

    if claims.exp.is_some_and(|exp| now >= exp) {
        return Err(CryptoError::JwtExpired);
    }
    if claims.nbf.is_some_and(|nbf| now < nbf) {
        return Err(CryptoError::JwtNotYetValid);
    }

    Ok(claims)
}

fn hmac_sha256(key: &[u8], message: &[u8]) -> [u8; 32] {
    const BLOCK: usize = 64;
    let mut key_block = [0u8; BLOCK];
    if key.len() > BLOCK {
        let mut hash = Sha256::new();
        hash.update(key);
        key_block[..32].copy_from_slice(&hash.finalize());
    } else {
        key_block[..key.len()].copy_from_slice(key);
    }

    let mut ipad = [0x36u8; BLOCK];
    let mut opad = [0x5cu8; BLOCK];
    for i in 0..BLOCK {
        ipad[i] ^= key_block[i];
        opad[i] ^= key_block[i];
    }

    let mut inner = Sha256::new();
    inner.update(ipad);
    inner.update(message);
    let inner_digest = inner.finalize();

    let mut outer = Sha256::new();
    outer.update(opad);
    outer.update(inner_digest);
    outer.finalize().into()
}

#[cfg(test)]
mod tests {
    use super::*;
    use p256::ecdsa::SigningKey;

    #[test]
    fn ecdsa_round_trip_and_rejects_modified_message() {
        let private = [7u8; 32];
        let signing = SigningKey::from_bytes((&private).into()).unwrap();
        let public = signing.verifying_key().to_encoded_point(false);
        let signature = ecdsa_sign(b"atc", &private).unwrap();
        assert!(ecdsa_verify(b"atc", &signature, public.as_bytes()).unwrap());
        assert!(!ecdsa_verify(b"tampered", &signature, public.as_bytes()).unwrap());
        assert!(!ecdsa_verify(b"atc", "sig_simulated", public.as_bytes()).unwrap());
    }

    #[test]
    fn address_is_deterministic() {
        let private = [9u8; 32];
        let signing = SigningKey::from_bytes((&private).into()).unwrap();
        let public = signing.verifying_key().to_encoded_point(false);
        let first = address_from_public_key(public.as_bytes()).unwrap();
        let second = address_from_public_key(public.as_bytes()).unwrap();
        assert_eq!(first, second);
        assert!(first.starts_with("atc1"));
    }

    #[test]
    fn jwt_hs256_checks_signature_and_time() {
        let header = URL_SAFE_NO_PAD.encode(br#"{"alg":"HS256","typ":"JWT"}"#);
        let claims = URL_SAFE_NO_PAD.encode(br#"{"sub":"alice","exp":200}"#);
        let input = format!("{header}.{claims}");
        let signature = URL_SAFE_NO_PAD.encode(hmac_sha256(b"secret", input.as_bytes()));
        let token = format!("{input}.{signature}");
        assert_eq!(verify_hs256_jwt(&token, b"secret", 100).unwrap().sub.as_deref(), Some("alice"));
        assert_eq!(verify_hs256_jwt(&token, b"secret", 200), Err(CryptoError::JwtExpired));
        assert_eq!(verify_hs256_jwt(&token, b"wrong", 100), Err(CryptoError::JwtSignatureMismatch));
    }
}
