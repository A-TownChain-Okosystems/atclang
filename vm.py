# ATCLang VM v0.2.0
# Vollständige Implementierung → atclang/vm/atcvm.py

"""
ATCLang VM — Stack-basierte virtuelle Maschine
Version: 0.2.0 | A-TownChain Ökosystem
Erweitert für vollständige atcos_main.atc Ausführung.
"""

import hashlib, os, time, secrets, json, struct
from enum import IntEnum, auto
from dataclasses import dataclass, field
from typing import List, Any, Dict, Optional, Callable


# ══════════════════════════════════════════════════════════
#  OPCODES — VOLLSTÄNDIG
# ══════════════════════════════════════════════════════════

class OP(IntEnum):
    # ── Stack ──────────────────────────────────────────
    PUSH        = auto()   # PUSH <val>
    POP         = auto()   # POP
    DUP         = auto()   # Stack-Top duplizieren
    SWAP        = auto()   # Top zwei tauschen
    ROT         = auto()   # a b c → b c a

    # ── Arithmetik ─────────────────────────────────────
    ADD         = auto()
    SUB         = auto()
    MUL         = auto()
    DIV         = auto()
    MOD         = auto()
    POW         = auto()   # Potenz (**)
    NEG         = auto()
    BITAND      = auto()   # &
    BITOR       = auto()   # |
    BITXOR      = auto()   # ^
    BITNOT      = auto()   # ~
    SHL         = auto()   # <<
    SHR         = auto()   # >>

    # ── Vergleiche ─────────────────────────────────────
    EQ          = auto()
    NEQ         = auto()
    LT          = auto()
    GT          = auto()
    LTE         = auto()
    GTE         = auto()

    # ── Logik ──────────────────────────────────────────
    AND         = auto()
    OR          = auto()
    NOT         = auto()

    # ── Variablen ──────────────────────────────────────
    LOAD        = auto()   # LOAD <name>
    STORE       = auto()   # STORE <name>
    LOAD_IDX    = auto()   # Map/List[key]
    STORE_IDX   = auto()   # Map/List[key] = val
    LOAD_GLOBAL = auto()   # Globale Variable
    STORE_GLOBAL= auto()
    DEL_VAR     = auto()   # delete var

    # ── Sprünge ────────────────────────────────────────
    JUMP        = auto()
    JUMP_IF     = auto()
    JUMP_NOT    = auto()

    # ── Funktionen / Closures ──────────────────────────
    CALL        = auto()   # CALL <name> <argc>
    RETURN      = auto()
    CALL_EXT    = auto()   # ATC:: Stdlib-Aufruf
    CALL_METHOD = auto()   # obj.method(args)
    MAKE_FN     = auto()   # Closure erstellen

    # ── Objekte & Typen ────────────────────────────────
    NEW_MAP     = auto()   # {}
    NEW_LIST    = auto()   # []
    NEW_OBJ     = auto()   # struct / contract instance
    GET_FIELD   = auto()
    SET_FIELD   = auto()
    HAS_KEY     = auto()   # key in map
    DEL_KEY     = auto()   # del map[key]
    LIST_PUSH   = auto()   # list.push(val)
    LIST_POP    = auto()
    LIST_LEN    = auto()
    MAP_KEYS    = auto()
    MAP_VALUES  = auto()
    MAP_ITEMS   = auto()
    CONTAINS    = auto()   # item in list/map
    CAST        = auto()   # Typ-Konvertierung

    # ── String-Operationen ─────────────────────────────
    STR_LEN     = auto()
    STR_SLICE   = auto()
    STR_UPPER   = a