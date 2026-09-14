# ATCLang 1.0.0 Conformance Plan

This plan defines the evidence required before ATCLang can receive a 1.0.0 production GO decision.

## Required vectors

1. **Lexical:** every normative token, keyword, literal and malformed lexical form.
2. **Parser:** every grammar production and precedence rule, including negative cases.
3. **Semantics:** every SEM rule, scope rule, type rule, invalid program and diagnostic.
4. **IR:** canonical representation for equivalent source constructs.
5. **Bytecode:** opcode encoding, operand encoding, constant pools, jumps and ABI.
6. **Determinism:** identical source/configuration produces identical canonical output.
7. **ATVM:** identical bytecode/state/transaction produces identical execution result and state transition.
8. **Stdlib:** deterministic behavior and API/ABI vectors for all standard modules.
9. **Negative:** malformed source, invalid AST, malformed bytecode and resource-limit cases.
10. **Differential:** Python reference tooling versus the canonical implementation.

## 1.0 acceptance criteria

A conformance suite is PASS only when all mandatory vectors pass on the supported release matrix, no known P0/P1 discrepancy remains, and the resulting evidence is committed or attached to a reproducible CI run.

A passing parser or semantic suite alone is insufficient for 1.0.0.

## Known specification hygiene checks

The normative language specification must be checked against the implementation before release. In particular, grammar spelling, AST inventory counts, token/type inventories and generated registry data must be validated automatically so documentation cannot silently drift from code.
