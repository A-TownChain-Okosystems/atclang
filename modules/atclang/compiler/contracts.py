# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Compiler — Contract Compilation
=======================================

ATC-92 | ATCLang v0.3.x

Contract-spezifische Codegenerierung.

Verantwortlichkeiten:
    - Contract-Definitionen kompilieren
    - State-Felder registrieren
    - State-Initialisierung erzeugen
    - Contract-Funktionen kompilieren
    - Exports registrieren
    - Contract-/State-Symbole verwalten

Nicht zuständig für:
    - Expressions
    - allgemeine Statements
    - Control Flow
    - Optimierung
    - VM-Ausführung
    - Parsing

Diese Datei arbeitet auf dem bereits erzeugten AST.
"""

from __future__ import annotations

from typing import Any, Optional

from atclang.parser.ast_nodes import (
    ASTNode,
    ContractDef,
    StateField,
    FunctionDef,
    MapLiteral,
)

from atclang.vm.atcvm import OP

from .context import CompilerContext
from .errors import CompileError
from .functions import compile_function


# ══════════════════════════════════════════════════════════════
# CONTRACT COMPILER
# ══════════════════════════════════════════════════════════════


class ContractCompiler:
    """
    Kompiliert ATCLang Contracts in ATC-Bytecode.

    Ein Contract besteht konzeptionell aus:

        Contract
          ├── State
          ├── Events
          ├── Errors
          └── Functions

    State-Daten werden als Contract-qualified Globals
    registriert:

        ContractName.fieldName

    Funktionen werden ebenfalls namespaced:

        ContractName.functionName
    """

    def __init__(self, context: CompilerContext):
        self.ctx = context

    # ══════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════

    def compile(self, contract: ContractDef) -> None:
        """
        Kompiliert einen vollständigen Contract.

        Reihenfolge:

            1. Contract validieren
            2. State registrieren
            3. State initialisieren
            4. Funktionen registrieren
            5. Funktionen kompilieren
            6. Public Exports registrieren
        """

        self._validate_contract(contract)

        contract_name = self._contract_name(contract)

        self._register_contract(contract)

        # State muss vor den Funktionen bekannt sein.
        self._compile_state(contract)

        # Funktionen werden anschließend kompiliert.
        self._compile_functions(contract)

        self._register_metadata(contract_name, contract)

    # ══════════════════════════════════════════════════════════
    # VALIDATION
    # ══════════════════════════════════════════════════════════

    def _validate_contract(self, contract: ContractDef) -> None:
        """Grundlegende Contract-Validierung."""

        if not getattr(contract, "name", None):
            self._error("Contract benötigt einen Namen.", contract)

        contract_name = contract.name

        if not contract_name.isidentifier():
            self._error(
                f"Ungültiger Contract-Name: '{contract_name}'",
                contract,
            )

        seen_states: set[str] = set()

        for state in getattr(contract, "states", []) or []:
            state_name = getattr(state, "name", None)

            if not state_name:
                self._error(
                    f"Contract '{contract_name}' enthält ein "
                    "State-Feld ohne Namen.",
                    state,
                )

            if state_name in seen_states:
                self._error(
                    f"Doppeltes State-Feld: "
                    f"'{contract_name}.{state_name}'",
                    state,
                )

            seen_states.add(state_name)

        seen_functions: set[str] = set()

        for fn in getattr(contract, "functions", []) or []:
            fn_name = getattr(fn, "name", None)

            if not fn_name:
                self._error(
                    f"Contract '{contract_name}' enthält "
                    "eine Funktion ohne Namen.",
                    fn,
                )

            if fn_name in seen_functions:
                self._error(
                    f"Doppelte Contract-Funktion: "
                    f"'{contract_name}.{fn_name}'",
                    fn,
                )

            seen_functions.add(fn_name)

    # ══════════════════════════════════════════════════════════
    # CONTRACT SYMBOL
    # ══════════════════════════════════════════════════════════

    def _register_contract(self, contract: ContractDef) -> None:
        """
        Registriert den Contract im globalen Symbolbereich.

        Die konkrete SymbolTable-Implementierung wird über
        CompilerContext abstrahiert.
        """

        name = contract.name

        existing = self.ctx.symbols.resolve(name)

        if existing is not None:
            self._error(
                f"Symbol '{name}' ist bereits definiert.",
                contract,
            )

        self.ctx.symbols.define(
            name=name,
            kind="contract",
            typ="Contract",
        )

    # ══════════════════════════════════════════════════════════
    # STATE
    # ══════════════════════════════════════════════════════════

    def _compile_state(self, contract: ContractDef) -> None:
        """
        Kompiliert Contract-State.

        Beispiel:

            contract Counter {
                state count: Int
            }

        wird konzeptionell zu:

            PUSH None
            STORE "Counter.count"

        State-Symbole erhalten den fully-qualified Namen.
        """

        contract_name = contract.name

        for state in getattr(contract, "states", []) or []:
            self._register_state(contract, state)
            self._emit_state_initializer(contract, state)

    def _register_state(
        self,
        contract: ContractDef,
        state: StateField,
    ) -> None:
        """Registriert ein State-Feld."""

        qualified_name = self._state_name(
            contract.name,
            state.name,
        )

        existing = self.ctx.symbols.resolve(qualified_name)

        if existing is not None:
            self._error(
                f"State '{qualified_name}' ist bereits definiert.",
                state,
            )

        type_name = self._type_name(state)

        self.ctx.symbols.define(
            name=qualified_name,
            kind="state",
            typ=type_name,
        )

    def _emit_state_initializer(
        self,
        contract: ContractDef,
        state: StateField,
    ) -> None:
        """
        Erzeugt die Initialisierung eines State-Feldes.

        Unterstützte Fälle:

            state x: Int
            state x = 10
            state x: Map
            state x = {...}
        """

        # Falls der AST ein Initialisierungsfeld besitzt,
        # verwenden wir es.
        initializer = self._state_initializer(state)

        if initializer is not None:
            self.ctx.emit_expr(initializer)
        else:
            type_name = self._type_name(state)

            if self._is_map_type(type_name):
                self.ctx.emit(OP.NEW_MAP, 0)
            else:
                self.ctx.emit(OP.PUSH, None)

        self.ctx.emit(
            OP.STORE,
            self._state_name(contract.name, state.name),
            line=self._line(state),
        )

    # ══════════════════════════════════════════════════════════
    # FUNCTIONS
    # ══════════════════════════════════════════════════════════

    def _compile_functions(self, contract: ContractDef) -> None:
        """Kompiliert sämtliche Contract-Funktionen."""

        contract_name = contract.name

        for function in getattr(contract, "functions", []) or []:
            self._compile_function(
                contract_name,
                function,
            )

    def _compile_function(
        self,
        contract_name: str,
        function: FunctionDef,
    ) -> None:
        """
        Kompiliert eine Contract-Funktion und registriert
        ihren fully-qualified Namen.
        """

        qualified_name = self._function_name(
            contract_name,
            function.name,
        )

        instructions = compile_function(
            function,
            self.ctx,
        )

        self.ctx.functions[qualified_name] = instructions

        # Parameter-Metadaten.
        self.ctx.function_params[qualified_name] = [
            getattr(parameter, "name", "")
            for parameter in getattr(function, "params", []) or []
        ]

        # Contract functions are callable through their
        # qualified name.
        self.ctx.exports.append(qualified_name)

    # ══════════════════════════════════════════════════════════
    # METADATA
    # ══════════════════════════════════════════════════════════

    def _register_metadata(
        self,
        contract_name: str,
        contract: ContractDef,
    ) -> None:
        """
        Optionaler Metadata-Hook für spätere ABI-/reflection-
        Erweiterungen.

        CompilerContext kann metadata speichern, falls die
        Implementierung dies unterstützt.
        """

        metadata = getattr(self.ctx, "metadata", None)

        if metadata is None:
            return

        contracts = metadata.setdefault("contracts", {})

        contracts[contract_name] = {
            "name": contract_name,
            "states": [
                {
                    "name": state.name,
                    "type": self._type_name(state),
                }
                for state in getattr(contract, "states", []) or []
            ],
            "functions": [
                {
                    "name": function.name,
                    "public": bool(
                        getattr(function, "is_pub", False)
                    ),
                    "params": [
                        getattr(parameter, "name", "")
                        for parameter in (
                            getattr(function, "params", []) or []
                        )
                    ],
                }
                for function in getattr(contract, "functions", []) or []
            ],
        }

    # ══════════════════════════════════════════════════════════
    # NAME HELPERS
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _contract_name(contract: ContractDef) -> str:
        return contract.name

    @staticmethod
    def _state_name(
        contract_name: str,
        state_name: str,
    ) -> str:
        return f"{contract_name}.{state_name}"

    @staticmethod
    def _function_name(
        contract_name: str,
        function_name: str,
    ) -> str:
        return f"{contract_name}.{function_name}"

    # ══════════════════════════════════════════════════════════
    # AST HELPERS
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _type_name(state: StateField) -> str:
        """
        Extrahiert den Type-Namen robust aus unterschiedlichen
        AST-Versionen.
        """

        type_hint = getattr(state, "type_hint", None)

        if type_hint is None:
            return ""

        if isinstance(type_hint, str):
            return type_hint

        return str(
            getattr(
                type_hint,
                "name",
                type_hint,
            )
        )

    @staticmethod
    def _state_initializer(
        state: StateField,
    ) -> Optional[ASTNode]:
        """
        Unterstützt unterschiedliche AST-Feldnamen für
        State-Initialisierung.
        """

        for attribute in (
            "value",
            "initializer",
            "default_value",
        ):
            if hasattr(state, attribute):
                value = getattr(state, attribute)

                if value is not None:
                    return value

        return None

    @staticmethod
    def _is_map_type(type_name: str) -> bool:
        normalized = type_name.replace(" ", "").lower()

        return normalized in {
            "map",
            "hashmap",
            "dict",
            "dictionary",
        } or normalized.startswith("map[")

    @staticmethod
    def _line(node: ASTNode) -> int:
        return int(getattr(node, "line", 0) or 0)

    # ══════════════════════════════════════════════════════════
    # ERROR HANDLING
    # ══════════════════════════════════════════════════════════

    @staticmethod
    def _error(
        message: str,
        node: Optional[ASTNode] = None,
    ) -> None:

        line = getattr(node, "line", None) if node else None

        if line is not None:
            raise CompileError(
                f"[ATCCompiler] @ Zeile {line}: {message}"
            )

        raise CompileError(
            f"[ATCCompiler]: {message}"
        )


# ══════════════════════════════════════════════════════════════
# FUNCTION API
# ══════════════════════════════════════════════════════════════


def compile_contract(
    contract: ContractDef,
    context: CompilerContext,
) -> None:
    """
    Convenience API.

    Beispiel:

        compile_contract(contract, context)
    """

    ContractCompiler(context).compile(contract)


__all__ = [
    "ContractCompiler",
    "compile_contract",
]