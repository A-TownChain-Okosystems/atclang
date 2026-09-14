// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! ATCLang Canonical Core (Rust).
//! Rust is the canonical compiler-side implementation boundary; Python is
//! reference tooling and differential-test infrastructure.

pub mod ast;
pub mod bytecode;
pub mod lexer;
pub mod parser;
