# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
# STUB: Temporärer Python-Stub — wird in Sprint 2.1 durch ATCLang ersetzt (ATCLang First Policy, AD-006)
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

    # Kontrollfluss
    "if", "else", "elif", "for", "while", "loop",
    "in", "break", "continue", "return", "match", "case",

    # Funktions-Modifikatoren
    "async", "await", "deploy", "call", "new", "delete",
    "import", "from", "as", "use",

    # Blockchain-Native
    "emit", "require", "event", "error", "assert",
    "genesis", "mint", "burn", "stake", "unstake", "vote",
    "transfer", "approve", "delegate",

    # System / OS
    "node", "consensus", "kernel", "process", "spawn",
    "channel", "syscall", "interrupt",

    # Typen-Keywords
    "self", "caller", "block", "tx", "null", "true", "false",

    # Modifikatoren
    "override", "virtual", "abstract", "final",
    "inline", "extern", "unsafe", "packed",

    # Generics / Traits
    "where", "with",
}

# ══════════════════════════════════════════════════════════
#  TYPEN
# ══════════════════════════════════════════════════════════

TYPES = {
    # Integer
    "UInt8", "UInt16", "UInt32", "UInt64", "UInt128", "UInt256",
    "Int8",  "Int16",  "Int32",  "Int64",  "Int128",  "Int256",
    "Int", "UInt",  # Short aliases
    "USize", "ISize",

    # Float
    "Float32", "Float64", "Float128",
    "Float",  # Short alias

    # Primitiv
    "Bool", "Char", "Byte",

    # Strings / Bytes
    "String", "Bytes", "Str",

    # Blockchain-Typen
    "Address", "Hash256", "Hash512", "PubKey", "PrivKey", "Signature",
    "TxHash", "BlockHash", "CID",

    # Kollektionen
    "Map", "List", "Set", "Array", "Vec", "Tuple",
    "Option", "Result", "Either",

    # ATC-Standards
    "ATC8300",       # Fungible Token
    "ATC9000",       # NFT / Shivamon
    "ATCContract",   # Smart Contract Basis
    "ATCWallet",     # Wallet-Typ
    "ATCBlock",      # Block-Typ
    "ATCTx",         # Transaktion

    # OS-Typen
    "Process", "Thread", "Channel", "Mutex", "Semaphore",
    "INode", "FileHandle", "DirHandle",

    # Netzwerk-Typen
    "Peer", "NodeID", "Port", "IPAddr",

    # Generisch
    "Any", "Void", "Never",
}

# ══════════════════════════════════════════════════════════
#  STDLIB-NAMESPACES (ATC::...)
# ══════════════════════════════════════════════════════════

ATC_NAMESPACES = {
    "ATC", "ATC::Hash", "ATC::Crypto", "ATC::Rand",
    "ATC::Net", "ATC::Net::UDP", "ATC::Net::Kademlia",
    "ATC::OS", "ATC::OS::Memory", "ATC::OS::Kernel",
    "ATC::OS::Filesystem",
    "ATC::Storage", "ATC::RPC",
    "ATC::Lang", "ATC::Lang::Compiler", "ATC::Lang::VM",
    "ATC::Blockchain", "ATC::Blockchain::Core",
    "ATC::Consensus", "ATC::Consensus::Shiva",
    "ATC::Gateway", "ATC::Gateway::API",
    "ATC::UI", "ATC::UI::Dashboard",
    "ATC::Wallet",
}


# ══════════════════════════════════════════════════════════
#  TOKEN
# ══════════════════════════════════════════════════════════

@dataclass
class Token:
    type:   TT
    value:  object
    line:   int = 0
    col:    int = 0

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"


class LexError(Exception):
    def __init__(self, msg: str, line: int, col: int):
        super().__init__(f"[LexError] Zeile {line}:{col} — {msg}")
        self.line = line
        self.col  = col


# ══════════════════════════════════════════════════════════
#  LEXER
# ══════════════════════════════════════════════════════════

class ATCLexer:
    """
    ATCLang Tokenizer v0.2.0
    Unterstützt alle Sprachfeatures inkl. ATC::-Namespaces.
    """

    def __init__(self, source: str):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.col    = 1
        self.tokens: List[Token] = []

    def current(self) -> Optional[str]:
        return self.source[self.pos] if self.pos < len(self.source) else None

    def peek(self, offset: int = 1) -> Optional[str]:
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else None

    def advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col   = 1
        else:
            self.col += 1
        return ch

    def match(self, expected: str) -> bool:
        if self.pos < len(self.source) and self.source[self.pos] == expected:
            self.advance()
            return True
        return False

    def add(self, tt: TT, value=None) -> Token:
        t = Token(tt, value, self.line, self.col)
        self.tokens.append(t)
        return t

    def error(self, msg: str):
        raise LexError(msg, self.line, self.col)

    # ── Tokenize ─────────────────────────────────────────

    def tokenize(self) -> List[Token]:
        while self.pos < len(self.source):
            self._next_token()
        self.add(TT.EOF, None)
        return self.tokens

    def _next_token(self):
        ch = self.current()
        if ch is None:
            return

        # ── Whitespace ──────────────────────────────────
        if ch in ' \t\r':
            self.advance()
            return

        if ch == '\n':
            self.advance()
            # Nur signifikante Newlines
            return

        # ── Kommentare ──────────────────────────────────
        if ch == '/' and self.peek() == '/':
            while self.current() and self.current() != '\n':
                self.advance()
            return

        if ch == '/' and self.peek() == '*':
            self.advance(); self.advance()
            while self.pos < len(self.source):
                if self.current() == '*' and self.peek() == '/':
                    self.advance(); self.advance()
                    break
                self.advance()
            return

        # ── Hash-Kommentare (# ...) ─────────────────────
        if ch == '#':
            while self.current() and self.current() != '\n':
                self.advance()
            return

        # ── Strings ─────────────────────────────────────
        if ch == '"':
            self._read_string()
            return

        if ch == "'" and self.peek() and self.peek(2) == "'":
            # Char-Literal 'x'
            self.advance()
            char_val = self.advance()
            self.advance()   # schließendes '
            self.add(TT.INT, ord(char_val))
            return

        # ── Bytes-Literal b"..." ────────────────────────
        if ch == 'b' and self.peek() == '"':
            self.advance()
            s = self._read_raw_string()
            self.add(TT.BYTES_LIT, s.encode())
            return

        # ── Zahlen ──────────────────────────────────────
        if ch.isdigit() or (ch == '0' and self.peek() in ('x','X','o','O','b','B')):
            self._read_number()
            return

        # ── Zahlen mit Unterstrich: 1_000_000 ──────────
        if ch == '_' and self.peek() and self.peek().isdigit():
            self._read_number()
            return

        # ── Bezeichner / Keywords / ATC:: ───────────────
        if ch.isalpha() or ch == '_':
            self._read_ident()
            return

        # ── Operatoren / Delimiter ──────────────────────
        self._read_symbol()

    def _read_string(self) -> str:
        self.advance()   # öffnendes "
        result = []
        while self.pos < len(self.source):
            ch = self.current()
            if ch == '"':
                self.advance()
                break
            if ch == '\\':
                self.advance()
                esc = self.advance()
                result.append({
                    'n': '\n', 't': '\t', 'r': '\r',
                    '"': '"',  '\\': '\\', '0': '\0',
                    'x': self._read_hex_escape(),
                }.get(esc, esc))
            else:
                result.append(self.advance())
        s = ''.join(result)
        self.add(TT.STRING, s)
        return s

    def _read_raw_string(self) -> str:
        self.advance()   # öffnendes "
        result = []
        while self.pos < len(self.source):
            ch = self.current()
            if ch == '"':
                self.advance()
                break
            result.append(self.advance())
        return ''.join(result)

    def _read_hex_escape(self) -> str:
        h = ''
        for _ in range(2):
            if self.current() and self.current() in '0123456789abcdefABCDEF':
                h += self.advance()
        return chr(int(h, 16)) if h else '\x00'

    def _read_number(self):
        start = self.pos
        is_float = False

        # Hex / Octal / Binary
        if self.current() == '0' and self.peek() in ('x','X'):
            self.advance(); self.advance()
            digits = ''
            while self.current() and (self.current() in '0123456789abcdefABCDEF_'):
                if self.current() != '_': digits += self.current()
                self.advance()
            self.add(TT.HEX_INT, int(digits, 16) if digits else 0)
            return

        if self.current() == '0' and self.peek() in ('o','O'):
            self.advance(); self.advance()
            digits = ''
            while self.current() and (self.current() in '01234567_'):
                if self.current() != '_': digits += self.current()
                self.advance()
            self.add(TT.OCTAL_INT, int(digits, 8) if digits else 0)
            return

        if self.current() == '0' and self.peek() in ('b','B'):
            self.advance(); self.advance()
            digits = ''
            while self.current() and (self.current() in '01_'):
                if self.current() != '_': digits += self.current()
                self.advance()
            self.add(TT.BIN_INT, int(digits, 2) if digits else 0)
            return

        # Dezimal (mit optionalem Unterstrich)
        digits = ''
        while self.current() and (self.current().isdigit() or self.current() == '_'):
            if self.current() != '_': digits += self.current()
            self.advance()

        if self.current() == '.' and self.peek() and self.peek().isdigit():
            is_float = True
            digits += '.'
            self.advance()
            while self.current() and (self.current().isdigit() or self.current() == '_'):
                if self.current() != '_': digits += self.current()
                self.advance()

        if self.current() in ('e', 'E'):
            is_float = True
            digits += self.advance()
            if self.current() in ('+', '-'):
                digits += self.advance()
            while self.current() and self.current().isdigit():
                digits += self.advance()

        if is_float:
            self.add(TT.FLOAT, float(digits))
        else:
            self.add(TT.INT, int(digits) if digits else 0)

    def _read_ident(self):
        start_line = self.line
        start_col  = self.col
        word = ''
        while self.current() and (self.current().isalnum() or self.current() == '_'):
            word += self.advance()

        # ATC::-Namespace (möglicherweise mehrere ::)
        if word == 'ATC' and self.current() == ':' and self.peek() == ':':
            full = 'ATC'
            while self.current() == ':' and self.peek() == ':':
                full += '::'
                self.advance(); self.advance()
                part = ''
                while self.current() and (self.current().isalnum() or self.current() == '_'):
                    part += self.advance()
                full += part
            t = Token(TT.ATC_STD, full, start_line, start_col)
            self.tokens.append(t)
            return

        # Bool-Literal
        if word in ('true', 'false'):
            self.tokens.append(Token(TT.BOOL, word == 'true', start_line, start_col))
            return

        # Keyword
        if word in KEYWORDS:
            self.tokens.append(Token(TT.KEYWORD, word, start_line, start_col))
            return

        # Typ
        if word in TYPES:
            self.tokens.append(Token(TT.TYPE, word, start_line, start_col))
            return

        # Normaler Bezeichner
        self.tokens.append(Token(TT.IDENT, word, start_line, start_col))

    def _read_symbol(self):
        ch = self.advance()
        line, col = self.line, self.col

        if ch == '+':
            if self.match('='): self.add(TT.PLUSEQ,  '+=')
            else:               self.add(TT.PLUS,     '+')
        elif ch == '-':
            if self.match('>'): self.add(TT.ARROW,   '->')
            elif self.match('='): self.add(TT.MINUSEQ, '-=')
            else:               self.add(TT.MINUS,    '-')
        elif ch == '*':
            if self.match('*'): self.add(TT.STARSTAR, '**')
            elif self.match('='): self.add(TT.STAREQ, '*=')
            else:               self.add(TT.STAR,     '*')
        elif ch == '/':
            if self.match('='): self.add(TT.SLASHEQ, '/=')
            else:               self.add(TT.SLASH,    '/')
        elif ch == '%':
            self.add(TT.PERCENT, '%')
        elif ch == '=':
            if self.match('='): self.add(TT.EQEQ,    '==')
            elif self.match('>'): self.add(TT.FAT_ARROW, '=>')
            else:               self.add(TT.EQ,       '=')
        elif ch == '!':
            if self.match('='): self.add(TT.NEQ,     '!=')
            else:               self.add(TT.NOT,      '!')
        elif ch == '<':
            if self.match('<'): self.add(TT.LSHIFT,  '<<')
            elif self.match('='): self.add(TT.LTE,   '<=')
            else:               self.add(TT.LT,       '<')
        elif ch == '>':
            if self.match('>'): self.add(TT.RSHIFT,  '>>')
            elif self.match('='): self.add(TT.GTE,   '>=')
            else:               self.add(TT.GT,       '>')
        elif ch == '&':
            if self.match('&'): self.add(TT.AND,     '&&')
            else:               self.add(TT.AMP,      '&')
        elif ch == '|':
            if self.match('|'): self.add(TT.OR,      '||')
            else:               self.add(TT.PIPE,     '|')
        elif ch == '^':         self.add(TT.CARET,    '^')
        elif ch == '~':         self.add(TT.TILDE,    '~')
        elif ch == ':':
            if self.match(':'): self.add(TT.DCOLON,  '::')
            elif self.match('='): self.add(TT.ASSIGN, ':=')
            else:               self.add(TT.COLON,    ':')
        elif ch == '.':
            if self.match('.'):
                if self.match('='): self.add(TT.DOTDOTEQ, '..=')
                else:               self.add(TT.DOTDOT,   '..')
            else:               self.add(TT.DOT,       '.')
        elif ch == '?':         self.add(TT.QUESTION,  '?')
        elif ch == '@':         self.add(TT.AT,         '@')
        elif ch == '#':         self.add(TT.HASH,       '#')
        elif ch == '(':         self.add(TT.LPAREN,     '(')
        elif ch == ')':         self.add(TT.RPAREN,     ')')
        elif ch == '{':         self.add(TT.LBRACE,     '{')
        elif ch == '}':         self.add(TT.RBRACE,     '}')
        elif ch == '[':         self.add(TT.LBRACKET,   '[')
        elif ch == ']':         self.add(TT.RBRACKET,   ']')
        elif ch == ',':         self.add(TT.COMMA,      ',')
        elif ch == ';':         self.add(TT.SEMICOLON,  ';')
        elif ch == '_':         self.add(TT.UNDERSCORE, '_')
        elif ch == '\n':        pass   # Newlines ignorieren
        else:
            pass   # Unbekannte Zeichen still ignorieren (z.B. Unicode in Kommentaren)


# ══════════════════════════════════════════════════════════
#  HILFSFUNKTION
# ══════════════════════════════════════════════════════════

def tokenize(source: str) -> List[Token]:
    return ATCLexer(source).tokenize()
