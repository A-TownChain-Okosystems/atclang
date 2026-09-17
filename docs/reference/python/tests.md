# tests/ — Test-Suiten

*6 Dateien, 1575 Zeilen — AST-generiert*


## `test_atclang_1_0_gate.py`
### `tests/test_atclang_1_0_gate.py` (34 Zeilen)

> Release-gate smoke checks for ATCLang 1.0.
> 
> These checks intentionally verify only invariants that can be established by the
> repository itself. They do not claim ATVM/mainnet readiness.

- **`def test_normative_spec_exists()`** — 
- **`def test_release_gate_exists_and_is_no_go_until_evidence_exists()`** — 
- **`def test_conformance_plan_exists()`** — 


## `test_bytecode_abi.py`
### `tests/test_bytecode_abi.py` (1045 Zeilen)

> ATCLang Bytecode ABI v1.0 Tests
> ================================
> 
> Normative tests for the ATC-92 / ATCLang Bytecode ABI.

- **`def make_module() -> CompiledModule`** — Construct the smallest representative valid module.
- **`def assert_roundtrip(encoded: bytes, decoder) -> None`** — 
- **`def test_abi_version_is_1_0() -> None`** — 
- **`def test_abi_magic_matches_bytecode_magic() -> None`** — 
- **`def test_header_size_is_20_bytes() -> None`** — 
- **`def test_header_struct_is_big_endian() -> None`** — 
- **`def test_header_can_be_decoded() -> None`** — 
- **`def test_header_checksum_is_zero_for_abi_1_0() -> None`** — 
- **`def test_invalid_magic_is_rejected() -> None`** — 
- **`def test_invalid_major_version_is_rejected() -> None`** — 
- **`def test_invalid_minor_version_is_rejected() -> None`** — 
- **`def test_nonzero_flags_are_rejected() -> None`** — 
- **`def test_nonzero_reserved_header_byte_is_rejected() -> None`** — 
- **`def test_nonzero_checksum_is_rejected() -> None`** — 
- **`def test_payload_length_mismatch_is_rejected() -> None`** — 
- **`def test_truncated_header_is_rejected() -> None`** — 
- **`def test_u8_encoding(value: int, expected: bytes) -> None`** — 
- **`def test_u16_big_endian(value: int, expected: bytes) -> None`** — 
- **`def test_u32_big_endian(value: int, expected: bytes) -> None`** — 
- **`def test_u64_big_endian(value: int, expected: bytes) -> None`** — 
- **`def test_i64_negative_value_is_big_endian() -> None`** — 
- **`def test_u8_roundtrip() -> None`** — 
- **`def test_u16_roundtrip() -> None`** — 
- **`def test_u32_roundtrip() -> None`** — 
- **`def test_u64_roundtrip() -> None`** — 
- **`def test_i64_roundtrip() -> None`** — 
- **`def test_u8_range_validation(value: int) -> None`** — 
- **`def test_u16_range_validation() -> None`** — 
- **`def test_u32_range_validation() -> None`** — 
- **`def test_u64_range_validation() -> None`** — 
- **`def test_i64_range_validation() -> None`** — 
- **`def test_f64_uses_ieee754_binary64_big_endian() -> None`** — 
- **`def test_f64_roundtrip(value: float) -> None`** — 
- **`def test_nonfinite_f64_is_rejected(value: float) -> None`** — 
- **`def test_nonfinite_f64_in_binary_is_rejected() -> None`** — 
- **`def test_bytes_encoding_contains_u32_length() -> None`** — 
- **`def test_bytes_roundtrip() -> None`** — 
- **`def test_string_encoding_is_utf8() -> None`** — 
- **`def test_string_roundtrip() -> None`** — 
- **`def test_invalid_utf8_is_rejected() -> None`** — 
- **`def test_truncated_bytes_are_rejected() -> None`** — 
- **`def test_constant_type_ids_are_explicit() -> None`** — 
- **`def test_null_constant_encoding() -> None`** — 
- **`def test_bool_constant_encoding() -> None`** — 
- **`def test_integer_constant_encoding() -> None`** — 
- **`def test_float_constant_encoding() -> None`** — 
- **`def test_string_constant_encoding() -> None`** — 
- **`def test_bytes_constant_encoding() -> None`** — 
- **`def test_null_operand_encoding() -> None`** — 
- **`def test_bool_operand_encoding() -> None`** — 
- **`def test_integer_operand_encoding() -> None`** — 
- **`def test_float_operand_encoding() -> None`** — 
- **`def test_string_operand_encoding() -> None`** — 
- **`def test_bytes_operand_encoding() -> None`** — 
- **`def test_opcode_is_one_byte() -> None`** — 
- **`def test_instruction_operand_count_is_explicit() -> None`** — 
- **`def test_instruction_encoding_is_deterministic() -> None`** — 
- **`def test_instruction_stream_contains_instruction_count() -> None`** — 
- **`def test_instruction_stream_is_deterministic() -> None`** — 
- **`def test_section_header_is_eight_bytes() -> None`** — 
- **`def test_section_encoding_contains_type_and_length() -> None`** — 
- **`def test_module_contains_exactly_six_sections() -> None`** — 
- **`def test_module_section_order_is_normative() -> None`** — 
- **`def test_invalid_section_order_is_rejected() -> None`** — 
- **`def test_unknown_section_type_is_rejected() -> None`** — 
- **`def test_trailing_bytes_are_rejected() -> None`** — 
- **`def test_metadata_encoding_is_utf8_based() -> None`** — 
- **`def test_empty_functions_encoding() -> None`** — 
- **`def test_function_count_is_encoded() -> None`** — 
- **`def test_encode_module_starts_with_atcb() -> None`** — 
- **`def test_encode_module_is_at_least_header_size() -> None`** — 
- **`def test_encode_module_is_deterministic() -> None`** — 
- **`def test_validate_binary_accepts_valid_module() -> None`** — 
- **`def test_decode_sections_accepts_valid_module() -> None`** — 
- **`def test_short_binary_is_rejected(payload: bytes) -> None`** — 
- **`def test_non_bytes_input_is_rejected() -> None`** — 
- **`def test_corrupt_section_length_is_rejected() -> None`** — 
- **`def test_corrupt_section_count_is_rejected() -> None`** — 
- **`def test_write_and_read_abi(tmp_path) -> None`** — 
- **`def test_written_binary_is_deterministic(tmp_path) -> None`** — 
- **`def test_abi_info_is_machine_readable() -> None`** — 
- **`def test_abi_info_contains_all_sections() -> None`** — 
- **`def test_abi_info_contains_constant_types() -> None`** — 
- **`def test_abi_info_contains_operand_types() -> None`** — 


## `test_missing_modules.py`
### `tests/test_missing_modules.py` (210 Zeilen)

- **`def test_abi_selector_deterministic()`** — 
- **`def test_abi_roundtrip_all_types()`** — 
- **`def test_abi_uint_overflow_rejected()`** — 
- **`def test_abi_encode_call_selector_prefix()`** — 
- **`def test_engine_deploy_and_call()`** — 
- **`def test_engine_unknown_selector_fails()`** — 
- **`def test_engine_transfer_and_balances()`** — 
- **`def test_engine_deploy_twice_fails()`** — 
- **`def test_engine_deterministic_addresses()`** — 
- **`def _artifact(**over)`** — 
- **`def test_artifact_roundtrip_and_id_stability()`** — 
- **`def test_artifact_tamper_detected()`** — 
- **`def test_host_deterministic_time()`** — 
- **`def test_host_gas_limit_enforced()`** — 
- **`def test_gate_blocks_nondeterminism_in_consensus()`** — 
- **`def test_gate_blocks_random()`** — 
- **`def test_gate_allows_clean_code()`** — 
- **`def test_gate_unsafe_without_require()`** — 
- **`def test_profiles_registry()`** — 
- **`def test_manifest_valid_and_invalid()`** — 
- **`def test_ir_hash_stable()`** — 


## `test_namespace_calls.py`
### `tests/test_namespace_calls.py` (78 Zeilen)

> Regression: Namespace-Calls mit Keyword-Member (Issue: silent wrong semantics).
> 
> Vor dem Fix (12.09.2026) zerfiel `ATCoin::transfer(a, b, c)` in Statement-
> und let-Position in ZWEI Statements: `Identifier('ATCoin')` + ein folgender

- **`def _first_stmt(src)`** — 
- **`def test_namespace_call_in_statement_position()`** — 
- **`def test_namespace_call_in_let_initializer()`** — 
- **`def test_atc_std_namespace_still_intact()`** — 
- **`def test_chained_member_after_keyword_method()`** — ATC::Net::P2P::connect — Member nach Keyword-Kette (connect ist Keyword).


## `test_security_boundaries.py`
### `tests/test_security_boundaries.py` (26 Zeilen)

- **`def test_consensus_rejects_wall_clock_and_randomness()`** — 
- **`def test_chain_timestamp_is_host_supplied_and_deterministic()`** — 


## `test_semantics.py`
### `tests/test_semantics.py` (182 Zeilen)

> Gate G2 — Semantik-Tests (specs/semantics/SPEC.md, Regeln SEM-001…SEM-012).

- **`def wrap(body: str) -> str`** — Gueltiges Programm-Geruest: Contract mit einer Funktion drumherum.
- **`def diags(src: str)`** — 
- **`def rules(ds)`** — 
- **`def test_examples_clean()`** — Alle parsbaren Beispiel-Programme (kanonisch: src/atclang/programs,
- **`def test_valid_program_clean()`** — 
- **`def test_shadowing_allowed()`** — 
- **`def test_int_float_promotion_ok()`** — 
- **`def test_sem001_duplicate_let()`** — 
- **`def test_sem001_duplicate_contract_fn()`** — 
- **`def test_sem002_undefined_symbol()`** — 
- **`def test_sem003_break_outside_loop()`** — 
- **`def test_sem004_continue_outside_loop()`** — 
- **`def test_sem005_return_outside_function()`** — 
- **`def test_sem006_let_type_mismatch()`** — 
- **`def test_sem006_int_not_assignable_to_int_from_float()`** — 
- **`def test_sem007_return_type_mismatch()`** — 
- **`def test_sem008_builtin_arity()`** — 
- **`def test_sem009_builtin_param_type()`** — 
- **`def test_sem010_duplicate_parameter()`** — 
- **`def test_sem011_string_plus_int()`** — 
- **`def test_sem012_condition_must_be_boolable()`** — 
- **`def test_strict_mode_raises()`** — 
- **`def test_strict_type_mismatch_raises()`** — 
