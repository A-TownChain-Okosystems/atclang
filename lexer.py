# ATCLang Lexer v0.2.0
# Vollständige Implementierung → atclang/lexer/lexer.py

"""
ATCLang Lexer — Tokenizer v0.2.0
Eigene Programmiersprache für das A-TownChain Ökosystem
Erweitert: Alle Keywords, Typen, Operatoren für atcos_main.atc
"""

from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Optional


# ══════════════════════════════════════════════════════════
#  TOKEN-TYPEN
# ══════════════════════════════════════════════════════════

class TT(Enum):
    # Literale
    INT        = auto()
    FLOAT      = auto()
    STRING     = auto()
    BOOL       = auto()
    HEX_INT    = auto()    # 0xFF, 0xATC...
    OCTAL_INT  = auto()    # 0o755
    BIN_INT    = auto()    # 0b1010
    BYTES_LIT  = auto()    # b"..."

    # Bezeichner & Keywords
    IDENT      = auto()
    KEYWORD    = auto()

    # Typen
    TYPE       = auto()

    # ATC-Standard-Referenz
    ATC_STD    = auto()    # ATC::Hash::sha3 etc.

    # Operatoren — Arithmetik
    PLUS       = auto()    # +
    MINUS      = auto()    # -
    STAR       = auto()    # *
    SLASH      = auto()    # /
    PERCENT    = auto()    # %
    STARSTAR   = auto()    # **  (Potenz)
    PLUSEQ     = auto()    # +=
    MINUSEQ    = auto()    # -=
    STAREQ     = auto()    # *=
    SLASHEQ    = auto()    # /=

    # Operatoren — Vergleich
    EQ         = auto()    # =
    EQEQ       = auto()    # ==
    NEQ        = auto()    # !=
    LT         = auto()    # <
    GT         = auto()    # >
    LTE        = auto()    # <=
    GTE        = auto()    # >=

    # Operatoren — Bitweise
    AMP        = auto()    # &
    PIPE       = auto()    # |
    CARET      = auto()    # ^
    TILDE      = auto()    # ~
    LSHIFT     = auto()    # <<
    RSHIFT     = auto()    # >>

    # Operatoren — Logik / Sonstiges
    AND        = auto()    # &&
    OR         = auto()    # ||
    NOT        = auto()    # !
    ARROW      = auto()    # ->
    FAT_ARROW  = auto()    # =>
    DCOLON     = auto()    # ::
    ASSIGN     = auto()    # :=
    QUESTION   = auto()    # ?
    DOTDOT     = auto()    # ..  (range)
    DOTDOTEQ   = auto()    # ..= (inkl. range)
    HASH       = auto()    # #   (decorator / annotation)
    AT         = auto()    # @

    # Delimiters
    LPAREN     = auto()    # (
    RPAREN     = auto()    # )
    LBRACE     = auto()    # {
    RBRACE     = auto()    # }
    LBRACKET   = auto()    # [
    RBRACKET   = auto()    # ]
    COMMA      = auto()    # ,
    COLON      = auto()    # :
    SEMICOLON  = auto()    # ;
    DOT        = auto()    # .
    UNDERSCORE = auto()    # _ (Platzhalter)

    # Sonstiges
    NEWLINE    = auto()
    INDENT     = auto()
    DEDENT     = auto()
    EOF        = auto()
    COMMENT    = auto()


# ══════════════════════════════════════════════════════════
#  KEYWORDS
# ══════════════════════════════════════════════════════════

KEYWORDS = {
    # Deklarationen
    "wallet", "contract", "struct", "enum", "impl", "trait",
    "fn", "state", "let", "const", "pub", "priv", "static",
    "type", "interface",

    # Kontro