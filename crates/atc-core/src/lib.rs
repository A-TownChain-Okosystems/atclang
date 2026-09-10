// Copyright (c) 2026 Michael Wroblewski — Apache-2.0
//! ATCLang Canonical Core (Rust) — Stage 2 (SCR-0084).
//! Stage 1: Lexer-MVP (SCR-0083) · Stage 2: Parser + AST + kanonische
//! JSON-Serialisierung mit Differential-Tests gegen die Python-Referenz
//! (src/atclang/frontend). Python bleibt Referenz-Tooling; der Rust-Core
//! ist der kanonische Start — volle Paritaet via F-111.

pub mod ast;
pub mod lexer;
pub mod parser;
