# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems.
# All Rights Reserved.
"""
ATCLang Semantics — TypeChecker (Subsystem, Gate G2)

Normativ: specs/semantics/SPEC.md | Quelle: specs/language/SPEC.md §5-6.

Unabhaengige semantische Analyse des AST: Scope-Kette, Symbolaufloesung,
Typ-Regeln, Built-in-Signaturen, Kontrollfluss-Platzierung. Der TypeChecker
mutiert nichts und erzeugt keinen Code — er validiert NUR (AD-022:
Compiler erzeugt, Verifier entscheidet).

API:
    TypeChecker().check_and_report(ast) -> List[SemanticDiagnostic]
    TypeChecker().check(ast)           -> None | raise CompileError (strict)
    analyze_source(source)             -> List[SemanticDiagnostic]
"""
from __future__ import annotations

import dataclasses as _dc
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from atclang.compiler.errors import (
    BreakOutsideLoopError,
    CompileError,
    ContinueOutsideLoopError,
    DuplicateParameterError,
    DuplicateSymbolError,
    InvalidCallError,
    InvalidReturnError,
    TypeMismatchError,
    UndefinedSymbolError,
)
from atclang.frontend.parser.ast_nodes import (
    ASTNode,
    BinaryOp,
    BoolLiteral,
    BreakStatement,
    ContinueStatement,
    ContractDef,
    DotAccess,
    EnumDef,
    ExprStatement,
    FloatLiteral,
    ForStatement,
    FunctionCall,
    FunctionDef,
    Identifier,
    IfStatement,
    ImportStatement,
    IntLiteral,
    LetStatement,
    ListLiteral,
    MapLiteral,
    NullLiteral,
    Program,
    ReturnStatement,
    StringLiteral,
    StructDef,
    StructLiteral,
    UnaryOp,
    WhileStatement,
)

T_ANY = "any"
T_VOID = "void"
NUMERIC = ("int", "float")
KNOWN_PRIMS = ("int", "float", "string", "bool", "list", "map", T_VOID)

# Built-in-Signaturen (specs/language/SPEC.md 5.3, 13 Funktionen)
BUILTIN_SIGNATURES: Dict[str, Dict[str, Any]] = {
    "print":  {"params": ["any"],         "result": T_VOID},
    "len":    {"params": ["any"],         "result": "int"},
    "range":  {"params": ["int"],         "result": "list"},
    "sha256": {"params": ["any"],         "result": "string"},
    "int":    {"params": ["any"],         "result": "int"},
    "float":  {"params": ["any"],         "result": "float"},
    "str":    {"params": ["any"],         "result": "string"},
    "bool":   {"params": ["any"],         "result": "bool"},
    "abs":    {"params": ["int"],         "result": "int"},
    "min":    {"params": ["int", "int"],  "result": "int"},
    "max":    {"params": ["int", "int"],  "result": "int"},
    "push":   {"params": ["list", "any"], "result": T_VOID},
    "pop":    {"params": ["list"],        "result": "any"},
}

_ERROR_CLASSES = {
    "BreakOutsideLoopError": BreakOutsideLoopError,
    "ContinueOutsideLoopError": ContinueOutsideLoopError,
    "DuplicateParameterError": DuplicateParameterError,
    "DuplicateSymbolError": DuplicateSymbolError,
    "InvalidCallError": InvalidCallError,
    "InvalidReturnError": InvalidReturnError,
    "TypeMismatchError": TypeMismatchError,
    "UndefinedSymbolError": UndefinedSymbolError,
}


@dataclass
class SemanticDiagnostic:
    """Eine semantische Verletzung (Regel-ID gemaess specs/semantics/SPEC.md)."""
    rule: str
    error_class: str
    message: str
    line: int = 0
    col: int = 0
    expected: str = ""
    actual: str = ""

    def __str__(self) -> str:
        return "[%s] %s (Zeile %s): %s" % (self.rule, self.error_class, self.line, self.message)


class TypeChecker:
    """G2 — unabhaengige semantische Analyse (AST rein, Diagnosen raus)."""

    def __init__(self) -> None:
        self.diagnostics: List[SemanticDiagnostic] = []
        self._scopes: List[Dict[str, str]] = [{}]
        self._functions: Dict[str, Dict[str, Any]] = {}
        self._loop_depth = 0
        self._fn_returns: List[str] = []

    # Scope-API
    def _define(self, name, typ, rule, err, node):
        scope = self._scopes[-1]
        if name in scope:
            self._diag(rule, err, "Doppelte Definition von '%s' im selben Scope" % name, node)
            return
        scope[name] = typ or T_ANY

    def _lookup(self, name):
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        return None

    def _push(self):
        self._scopes.append({})

    def _pop(self):
        self._scopes.pop()

    def _diag(self, rule, err, msg, node, expected="", actual=""):
        self.diagnostics.append(SemanticDiagnostic(
            rule, err, msg, getattr(node, "line", 0), getattr(node, "col", 0),
            expected, actual))

    # API
    def check_and_report(self, program):
        self._check_program(program)
        return self.diagnostics

    def analyze_source(self, source: str) -> List[SemanticDiagnostic]:
        """Komfort-Entry: Quelle direkt analysieren (parse + check_and_report)."""
        from atclang.frontend.parser.parser import parse
        return self.check_and_report(parse(source))

    def check(self, program):
        diags = self.check_and_report(program)
        if diags:
            d = diags[0]
            msg = "%s: %s (Zeile %s, Spalte %s)" % (d.rule, d.message, d.line, d.col)
            cls = _ERROR_CLASSES.get(d.error_class, CompileError)
            try:
                raise cls(msg)
            except TypeError:
                if d.error_class == "TypeMismatchError":
                    raise TypeMismatchError(d.expected or d.message, d.actual or "unbekannt")
                raise CompileError("%s: %s (Zeile %s)" % (d.rule, d.message, d.line))

    # Programm / Top-Level
    def _check_program(self, program):
        for st in program.statements:
            if isinstance(st, FunctionDef):
                self._register_function(st)
            elif isinstance(st, (ContractDef, StructDef, EnumDef)):
                self._define(st.name, T_ANY, "SEM-001", "DuplicateSymbolError", st)
        for st in program.statements:
            self._check_stmt(st)

    def _register_function(self, fn):
        if fn.name in self._functions:
            return
        self._functions[fn.name] = {
            "params": list(fn.params),
            "ret": self._type_name(fn.return_type),
        }
        self._define(fn.name, self._type_name(fn.return_type) or T_ANY,
                     "SEM-001", "DuplicateSymbolError", fn)

    # Anweisungen
    def _check_stmt(self, node):
        if isinstance(node, FunctionDef):
            self._push()
            for p in node.params:
                self._define(p.name, self._type_name(p.type_hint),
                             "SEM-010", "DuplicateParameterError", p)
            ret = self._type_name(node.return_type) or T_VOID
            self._fn_returns.append(ret)
            for st in node.body:
                self._check_stmt(st)
            self._fn_returns.pop()
            self._pop()

        elif isinstance(node, LetStatement):
            vtyp = self._check_expr(node.value) if node.value is not None else T_ANY
            hint = self._type_name(node.type_hint)
            if (hint in KNOWN_PRIMS and hint != T_VOID
                    and vtyp in KNOWN_PRIMS and vtyp != T_VOID):
                if not self._assignable(hint, vtyp):
                    self._diag("SEM-006", "TypeMismatchError",
                               "let '%s' als '%s', Initialisierung ist '%s'" % (node.name, hint, vtyp), node,
                               expected=hint, actual=vtyp)
            self._define(node.name, hint or vtyp or T_ANY, "SEM-001", "DuplicateSymbolError", node)

        elif isinstance(node, ReturnStatement):
            if not self._fn_returns:
                self._diag("SEM-005", "InvalidReturnError", "return ausserhalb einer Funktion", node)
            else:
                ret = self._fn_returns[-1]
                vtyp = self._check_expr(node.value) if node.value is not None else T_VOID
                if ret in KNOWN_PRIMS and vtyp in KNOWN_PRIMS:
                    if ret == T_VOID and vtyp != T_VOID:
                        self._diag("SEM-007", "TypeMismatchError",
                                   "Funktion ohne Rueckgabetyp, aber return mit Wert", node,
                                   expected=T_VOID, actual=vtyp)
                    elif ret != T_VOID and vtyp == T_VOID:
                        self._diag("SEM-007", "TypeMismatchError",
                                   "Funktion erwartet '%s', return ohne Wert" % ret, node,
                                   expected=ret, actual=T_VOID)
                    elif not self._assignable(ret, vtyp):
                        self._diag("SEM-007", "TypeMismatchError",
                                   "Rueckgabetyp '%s', Wert ist '%s'" % (ret, vtyp), node,
                                   expected=ret, actual=vtyp)

        elif isinstance(node, BreakStatement):
            if self._loop_depth == 0:
                self._diag("SEM-003", "BreakOutsideLoopError", "break ausserhalb einer Loop", node)

        elif isinstance(node, ContinueStatement):
            if self._loop_depth == 0:
                self._diag("SEM-004", "ContinueOutsideLoopError", "continue ausserhalb einer Loop", node)

        elif isinstance(node, WhileStatement):
            self._cond_check(node.condition, node)
            self._loop_depth += 1
            self._push()
            for st in node.body:
                self._check_stmt(st)
            self._pop()
            self._loop_depth -= 1

        elif isinstance(node, ForStatement):
            self._check_expr(node.iterable)
            self._loop_depth += 1
            self._push()
            self._define(node.var, T_ANY, "SEM-001", "DuplicateSymbolError", node)
            for st in node.body:
                self._check_stmt(st)
            self._pop()
            self._loop_depth -= 1

        elif isinstance(node, IfStatement):
            self._cond_check(node.condition, node)
            self._push()
            for st in (node.then_block or []):
                self._check_stmt(st)
            self._pop()
            for block in (getattr(node, "elif_blocks", None) or []):
                self._walk_maybe_block(block)
            if getattr(node, "else_block", None):
                self._walk_maybe_block(node.else_block)

        elif isinstance(node, ContractDef):
            self._push()
            for s in (node.states or []):
                name = getattr(s, "name", None)
                if name:
                    self._define(name, self._type_name(getattr(s, "type_hint", None)),
                                 "SEM-001", "DuplicateSymbolError", s)
                init = getattr(s, "value", None)
                if init is not None:
                    self._check_expr(init)
            for e in (getattr(node, "events", None) or []) + (getattr(node, "errors", None) or []):
                name = getattr(e, "name", None)
                if name:
                    self._define(name, T_ANY, "SEM-001", "DuplicateSymbolError", e)
            fns = [f for f in (node.functions or []) if isinstance(f, FunctionDef)]
            seen = set()
            for f in fns:
                if f.name in seen:
                    self._diag("SEM-001", "DuplicateSymbolError",
                               "Doppelte Funktion '%s' im Contract" % f.name, f)
                seen.add(f.name)
            for f in fns:
                self._check_stmt(f)
            self._pop()

        elif isinstance(node, ExprStatement):
            self._check_expr(getattr(node, "expr", None))

        elif isinstance(node, (ImportStatement, StructDef, EnumDef)):
            self._walk_generic(node)

        else:
            self._walk_generic(node)

    def _walk_maybe_block(self, block):
        if block is None:
            return
        if isinstance(block, list):
            self._push()
            for st in block:
                if isinstance(st, ASTNode):
                    self._check_stmt(st)
            self._pop()
        elif isinstance(block, ASTNode):
            self._push()
            self._check_stmt(block)
            self._pop()

    def _walk_generic(self, node):
        """Rekursiver Fallback fuer nicht spezialisierte Knoten (Match, Emit,
        Require, Assignment, Struct-Literals, unbekannte Erweiterungen)."""
        if isinstance(node, (list, tuple)):
            for el in node:
                self._walk_generic(el)
            return
        if not isinstance(node, ASTNode):
            return
        if _dc.is_dataclass(node):
            for f in _dc.fields(node):
                self._walk_generic(getattr(node, f.name, None))
        # keine __dict__-Iteration bei Nicht-Dataclasses: bewusst konservativ

    # Ausdruecke
    def _check_expr(self, node):
        if node is None or not isinstance(node, ASTNode):
            return T_ANY

        if isinstance(node, IntLiteral):
            return "int"
        if isinstance(node, FloatLiteral):
            return "float"
        if isinstance(node, StringLiteral):
            return "string"
        if isinstance(node, BoolLiteral):
            return "bool"
        if isinstance(node, NullLiteral):
            return "null"
        if isinstance(node, (ListLiteral, MapLiteral, StructLiteral)):
            self._walk_generic(node)
            return "list" if isinstance(node, ListLiteral) else ("map" if isinstance(node, MapLiteral) else T_ANY)

        if isinstance(node, Identifier):
            found = self._lookup(node.name)
            if found is None:
                if node.name in self._functions:
                    return self._functions[node.name]["ret"] or T_ANY
                self._diag("SEM-002", "UndefinedSymbolError",
                           "Unbekanntes Symbol '%s'" % node.name, node)
                return T_ANY
            return found or T_ANY

        if isinstance(node, BinaryOp):
            lt = self._check_expr(node.left)
            rt = self._check_expr(node.right)
            op = node.op
            if op in ("==", "!=", "<", ">", "<=", ">="):
                if (lt in KNOWN_PRIMS and rt in KNOWN_PRIMS and lt != T_VOID and rt != T_VOID
                        and lt != rt and not self._assignable(lt, rt) and not self._assignable(rt, lt)):
                    self._diag("SEM-011", "TypeMismatchError",
                               "Vergleich '%s' mit '%s'" % (lt, rt), node, expected=lt, actual=rt)
                return "bool"
            if op in ("and", "or"):
                return "bool"
            if op == "+":
                if lt == "string" and rt == "string":
                    return "string"
                if lt == "list" and rt == "list":
                    return "list"
                if lt in NUMERIC and rt in NUMERIC:
                    return "float" if "float" in (lt, rt) else "int"
                if (lt in KNOWN_PRIMS and rt in KNOWN_PRIMS and lt != T_VOID and rt != T_VOID
                        and not (lt == "string" and rt == "string")
                        and not (lt == "list" and rt == "list")
                        and not (lt in NUMERIC and rt in NUMERIC)):
                    self._diag("SEM-011", "TypeMismatchError",
                               "'+' zwischen '%s' und '%s'" % (lt, rt), node, expected=lt, actual=rt)
                return T_ANY
            if op in ("-", "*", "/", "%"):
                if lt in NUMERIC and rt in NUMERIC:
                    return "float" if "float" in (lt, rt) else "int"
                bad = ("string", "bool", "list", "map", "null")
                if lt in bad or rt in bad:
                    self._diag("SEM-011", "TypeMismatchError",
                               "'%s' zwischen '%s' und '%s'" % (op, lt, rt), node, expected=lt, actual=rt)
                return T_ANY
            return T_ANY

        if isinstance(node, UnaryOp):
            operand = getattr(node, "operand", None) or getattr(node, "expr", None)
            t = self._check_expr(operand)
            op = getattr(node, "op", "")
            if op in ("!", "not"):
                return "bool"
            return t or T_ANY

        if isinstance(node, FunctionCall):
            target = node.target
            args = node.args or []
            if isinstance(target, Identifier):
                name = target.name
                if name in BUILTIN_SIGNATURES:
                    sig = BUILTIN_SIGNATURES[name]
                    if len(args) != len(sig["params"]):
                        self._diag("SEM-008", "InvalidCallError",
                                   "Built-in '%s' erwartet %d Argument(e), erhalten %d"
                                   % (name, len(sig["params"]), len(args)), node)
                    for i, (arg, want) in enumerate(zip(args, sig["params"])):
                        at = self._check_expr(arg)
                        if (want in KNOWN_PRIMS and at in KNOWN_PRIMS
                                and at != T_VOID and want != T_VOID and at != want
                                and not self._assignable(want, at)):
                            self._diag("SEM-009", "TypeMismatchError",
                                       "Built-in '%s': Argument %d ist '%s', erwartet '%s'"
                                       % (name, i + 1, at, want), node, expected=want, actual=at)
                    return sig["result"]
                if name in self._functions:
                    for arg in args:
                        self._check_expr(arg)
                    return self._functions[name]["ret"] or T_ANY
                for arg in args:
                    self._check_expr(arg)
                return T_ANY
            self._walk_generic(node.target)
            for arg in args:
                self._check_expr(arg)
            return T_ANY

        if isinstance(node, DotAccess):
            self._walk_generic(node)
            return T_ANY

        self._walk_generic(node)
        return T_ANY

    # Hilfsregeln
    def _cond_check(self, cond, node):
        t = self._check_expr(cond)
        if t in ("string", "list", "map", "null"):
            self._diag("SEM-012", "TypeMismatchError",
                       "Bedingung ist '%s', erwartet bool" % t, node, expected="bool", actual=t)

    def _type_name(self, hint):
        if hint is None:
            return T_ANY
        name = hint if isinstance(hint, str) else getattr(hint, "name", None)
        return name if name in KNOWN_PRIMS else T_ANY

    @staticmethod
    def _assignable(target, value):
        if target == value:
            return True
        if target == "float" and value == "int":
            return True
        return False


def analyze_source(source):
    """Komfort-Entry: Quelle direkt analysieren (parse + check_and_report)."""
    from atclang.frontend.parser.parser import parse
    return TypeChecker().check_and_report(parse(source))
