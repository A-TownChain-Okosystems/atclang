# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.

"""
ATCLang Function Compiler
=========================

Function-level compilation for ATCLang.

Responsibilities
----------------
- Compile FunctionDef nodes
- Create isolated function compilation scopes
- Register parameters
- Compile function bodies
- Emit implicit return
- Track public/exported functions
- Preserve function parameter metadata
- Support deterministic function ordering

This module intentionally does not own:
- expression compilation
- statement compilation
- control-flow lowering
- contract compilation
- optimization
- bytecode serialization

Those responsibilities belong to their respective compiler modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from atclang.parser.ast_nodes import (
    ASTNode,
    FunctionDef,
    Parameter,
)

from atclang.vm.atcvm import Instruction, OP

if TYPE_CHECKING:
    from .context import CompilerContext
    from .symbols import SymbolTable


# ═════════════════════════════════════════════════════════════
# FUNCTION METADATA
# ═════════════════════════════════════════════════════════════

@dataclass
class CompiledFunction:
    """
    Result of compiling one ATCLang function.

    This is intentionally independent from CompiledModule so
    functions can be compiled and validated before module assembly.
    """

    name: str
    instructions: List[Instruction] = field(default_factory=list)

    parameters: List[str] = field(default_factory=list)
    parameter_types: Dict[str, str] = field(default_factory=dict)

    return_type: Optional[str] = None

    is_public: bool = False
    is_async: bool = False
    is_generator: bool = False

    source_line: int = 0
    source_column: int = 0

    def instruction_count(self) -> int:
        return len(self.instructions)


# ═════════════════════════════════════════════════════════════
# FUNCTION COMPILER
# ═════════════════════════════════════════════════════════════

class FunctionCompiler:
    """
    Compiles ATCLang FunctionDef nodes.

    The compiler is intentionally orchestration-oriented.
    Expression and statement semantics remain in their dedicated
    compiler modules.
    """

    def __init__(self, context: "CompilerContext"):
        self.context = context

    # ─────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────

    def compile(
        self,
        function: FunctionDef,
        *,
        qualified_name: Optional[str] = None,
    ) -> CompiledFunction:
        """
        Compile a FunctionDef into an isolated instruction stream.

        Parameters
        ----------
        function:
            ATCLang FunctionDef AST node.

        qualified_name:
            Optional fully-qualified name, e.g.
            ``Wallet.transfer``.

        Returns
        -------
        CompiledFunction
        """

        name = qualified_name or self._function_name(function)

        with self.context.function_scope(name) as function_scope:
            self._register_parameters(function, function_scope)

            self._compile_body(function, function_scope)

            self._ensure_return(function)

            instructions = list(function_scope.instructions)

            result = CompiledFunction(
                name=name,
                instructions=instructions,
                parameters=[
                    self._parameter_name(param)
                    for param in function.params
                ],
                parameter_types={
                    self._parameter_name(param): self._parameter_type(param)
                    for param in function.params
                    if self._parameter_type(param)
                },
                return_type=self._return_type(function),
                is_public=self._is_public(function),
                is_async=self._is_async(function),
                is_generator=self._is_generator(function),
                source_line=getattr(function, "line", 0),
                source_column=getattr(function, "col", 0),
            )

        self._register_function(result)

        return result

    def compile_many(
        self,
        functions: List[FunctionDef],
        *,
        namespace: Optional[str] = None,
    ) -> Dict[str, CompiledFunction]:
        """
        Compile multiple functions deterministically.
        """

        compiled: Dict[str, CompiledFunction] = {}

        for function in functions:
            local_name = self._function_name(function)

            if namespace:
                name = f"{namespace}.{local_name}"
            else:
                name = local_name

            compiled[name] = self.compile(
                function,
                qualified_name=name,
            )

        return compiled

    # ═════════════════════════════════════════════════════════
    # PARAMETER HANDLING
    # ═════════════════════════════════════════════════════════

    def _register_parameters(
        self,
        function: FunctionDef,
        scope: Any,
    ) -> None:
        """
        Register function parameters in the function-local scope.
        """

        seen = set()

        for index, parameter in enumerate(function.params):
            name = self._parameter_name(parameter)

            if not name:
                self._error(
                    "Function parameter has no name",
                    function,
                )

            if name in seen:
                self._error(
                    f"Duplicate function parameter: '{name}'",
                    parameter,
                )

            seen.add(name)

            typ = self._parameter_type(parameter)

            self._define_parameter(
                scope,
                name=name,
                index=index,
                typ=typ,
            )

            # Parameter ABI:
            #
            # argument 0 → local parameter 0
            # argument 1 → local parameter 1
            #
            # The VM's CALL implementation remains responsible for
            # physically placing arguments into the function frame.

            self._emit_parameter_load(
                scope,
                name=name,
                index=index,
                parameter=parameter,
            )

    def _define_parameter(
        self,
        scope: Any,
        *,
        name: str,
        index: int,
        typ: str,
    ) -> None:
        """
        Define a parameter using the repository's symbol API.

        Supports the refactored SymbolTable while retaining a
        compatibility path for older implementations.
        """

        symbols = getattr(scope, "symbols", None)

        if symbols is None:
            return

        define = getattr(symbols, "define", None)

        if define is None:
            return

        try:
            define(
                name=name,
                kind="parameter",
                typ=typ,
                index=index,
            )
        except TypeError:
            try:
                define(
                    name,
                    "parameter",
                    typ,
                )
            except TypeError:
                define(
                    name,
                    "parameter",
                )

    def _emit_parameter_load(
        self,
        scope: Any,
        *,
        name: str,
        index: int,
        parameter: Parameter,
    ) -> None:
        """
        Emit parameter binding instructions when the context/ABI
        requires explicit argument-to-local binding.

        Newer contexts may implement this themselves. In that case
        this method becomes a no-op.
        """

        emitter = getattr(scope, "bind_parameter", None)

        if callable(emitter):
            emitter(
                name=name,
                index=index,
                line=getattr(parameter, "line", 0),
                col=getattr(parameter, "col", 0),
            )
            return

        # The VM may already expose arguments through LOAD of the
        # parameter symbol. Do not emit legacy bytecode here unless
        # the context explicitly requests it.
        return

    # ═════════════════════════════════════════════════════════
    # BODY
    # ═════════════════════════════════════════════════════════

    def _compile_body(
        self,
        function: FunctionDef,
        scope: Any,
    ) -> None:
        """
        Compile all function statements.
        """

        statement_compiler = self._statement_compiler()

        for statement in function.body:
            statement_compiler.compile(
                statement,
                scope,
            )

    # ═════════════════════════════════════════════════════════
    # RETURN HANDLING
    # ═════════════════════════════════════════════════════════

    def _ensure_return(
        self,
        function: FunctionDef,
    ) -> None:
        """
        Guarantee that every function has a deterministic return.

        If the function already terminates in RETURN, nothing is
        emitted.

        Otherwise:

            PUSH None
            RETURN

        is emitted.
        """

        instructions = self.context.instructions

        if not instructions:
            self.context.emit(
                OP.PUSH,
                None,
                line=getattr(function, "line", 0),
                col=getattr(function, "col", 0),
            )
            self.context.emit(
                OP.RETURN,
                line=getattr(function, "line", 0),
                col=getattr(function, "col", 0),
            )
            return

        last = instructions[-1]

        if last.op in (
            OP.RETURN,
            OP.HALT,
        ):
            return

        self.context.emit(
            OP.PUSH,
            None,
            line=getattr(function, "line", 0),
            col=getattr(function, "col", 0),
        )

        self.context.emit(
            OP.RETURN,
            line=getattr(function, "line", 0),
            col=getattr(function, "col", 0),
        )

    # ═════════════════════════════════════════════════════════
    # FUNCTION METADATA
    # ═════════════════════════════════════════════════════════

    @staticmethod
    def _function_name(function: FunctionDef) -> str:
        name = getattr(function, "name", None)

        if not name:
            raise FunctionCompileError(
                "FunctionDef has no function name"
            )

        return name

    @staticmethod
    def _parameter_name(parameter: Parameter) -> str:
        name = getattr(parameter, "name", None)

        if not name:
            return ""

        return str(name)

    @staticmethod
    def _parameter_type(parameter: Parameter) -> str:
        type_hint = getattr(parameter, "type_hint", None)

        if type_hint is None:
            return ""

        name = getattr(type_hint, "name", None)

        if name is not None:
            return str(name)

        return str(type_hint)

    @staticmethod
    def _return_type(function: FunctionDef) -> Optional[str]:
        """
        Support the currently known ATCLang AST variants.
        """

        for attribute in (
            "return_type",
            "return_type_hint",
            "type_hint",
        ):
            value = getattr(function, attribute, None)

            if value is None:
                continue

            name = getattr(value, "name", None)

            if name is not None:
                return str(name)

            return str(value)

        return None

    @staticmethod
    def _is_public(function: FunctionDef) -> bool:
        return bool(
            getattr(function, "is_pub", False)
            or getattr(function, "is_public", False)
            or getattr(function, "public", False)
        )

    @staticmethod
    def _is_async(function: FunctionDef) -> bool:
        return bool(
            getattr(function, "is_async", False)
            or getattr(function, "async_", False)
        )

    @staticmethod
    def _is_generator(function: FunctionDef) -> bool:
        return bool(
            getattr(function, "is_generator", False)
            or getattr(function, "generator", False)
        )

    # ═════════════════════════════════════════════════════════
    # COMPILER SERVICES
    # ═════════════════════════════════════════════════════════

    def _statement_compiler(self):
        """
        Resolve the statement compiler from the context.

        This avoids circular imports between the compiler
        subsystems.
        """

        compiler = getattr(
            self.context,
            "statement_compiler",
            None,
        )

        if compiler is not None:
            return compiler

        factory = getattr(
            self.context,
            "get_statement_compiler",
            None,
        )

        if callable(factory):
            return factory()

        # Lazy import avoids compiler module cycles.
        from .statements import StatementCompiler

        return StatementCompiler(self.context)

    def _register_function(
        self,
        function: CompiledFunction,
    ) -> None:
        """
        Register compiled function metadata in the module context.
        """

        register = getattr(
            self.context,
            "register_function",
            None,
        )

        if callable(register):
            register(function)
            return

        functions = getattr(
            self.context,
            "functions",
            None,
        )

        if functions is not None:
            functions[function.name] = function.instructions

        params = getattr(
            self.context,
            "function_params",
            None,
        )

        if params is not None:
            params[function.name] = list(function.parameters)

        exports = getattr(
            self.context,
            "exports",
            None,
        )

        if exports is not None and function.is_public:
            if function.name not in exports:
                exports.append(function.name)

    # ═════════════════════════════════════════════════════════
    # ERROR HANDLING
    # ═════════════════════════════════════════════════════════

    def _error(
        self,
        message: str,
        node: Optional[ASTNode] = None,
    ) -> None:
        """
        Delegate compiler errors to the centralized error module.
        """

        line = getattr(node, "line", 0) if node else 0
        col = getattr(node, "col", 0) if node else 0

        error_factory = getattr(
            self.context,
            "error",
            None,
        )

        if callable(error_factory):
            error_factory(
                message,
                node=node,
            )

        raise FunctionCompileError(
            message,
            line=line,
            column=col,
        )


# ═════════════════════════════════════════════════════════════
# ERROR
# ═════════════════════════════════════════════════════════════

class FunctionCompileError(Exception):
    """
    Function-level compiler error.

    Kept local as a compatibility fallback. The central compiler
    error hierarchy should be preferred when available.
    """

    def __init__(
        self,
        message: str,
        *,
        line: int = 0,
        column: int = 0,
    ):
        self.line = line
        self.column = column

        location = ""

        if line:
            location = f" @ {line}:{column}"

        super().__init__(
            f"[ATCLang FunctionCompiler]{location}: {message}"
        )


# ═════════════════════════════════════════════════════════════
# CONVENIENCE API
# ═════════════════════════════════════════════════════════════

def compile_function(
    context: "CompilerContext",
    function: FunctionDef,
    *,
    qualified_name: Optional[str] = None,
) -> CompiledFunction:
    """
    Convenience wrapper around FunctionCompiler.
    """

    compiler = FunctionCompiler(context)

    return compiler.compile(
        function,
        qualified_name=qualified_name,
    )


def compile_functions(
    context: "CompilerContext",
    functions: List[FunctionDef],
    *,
    namespace: Optional[str] = None,
) -> Dict[str, CompiledFunction]:
    """
    Convenience wrapper for compiling multiple functions.
    """

    compiler = FunctionCompiler(context)

    return compiler.compile_many(
        functions,
        namespace=namespace,
    )


__all__ = [
    "CompiledFunction",
    "FunctionCompiler",
    "FunctionCompileError",
    "compile_function",
    "compile_functions",
]