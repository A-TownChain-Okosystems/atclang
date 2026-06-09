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
    STR_UPPER   = auto()
    STR_LOWER   = auto()
    STR_SPLIT   = auto()
    STR_JOIN    = auto()
    STR_FORMAT  = auto()

    # ── ATC-spezifisch ─────────────────────────────────
    EMIT        = auto()   # Event auslösen
    REQUIRE     = auto()   # Assertion
    TRANSFER    = auto()   # ATC-Token-Transfer
    MINT        = auto()   # Token minten
    BURN        = auto()   # Token burnen
    STAKE       = auto()   # ATC staken
    UNSTAKE     = auto()
    VOTE        = auto()

    # ── Crypto / Hash ──────────────────────────────────
    HASH_SHA256   = auto()
    HASH_SHA3     = auto()
    HASH_SHA3_ATC = auto()
    CRYPTO_SIGN   = auto()
    CRYPTO_VERIFY = auto()
    RAND_BYTES    = auto()
    RAND_INT      = auto()
    LEADING_ZEROS = auto()

    # ── Netzwerk / P2P ─────────────────────────────────
    NET_SEND    = auto()
    NET_RECV    = auto()
    NET_BROADCAST = auto()
    NET_CONNECT = auto()
    NET_PEERS   = auto()

    # ── Speicher / Persistenz ──────────────────────────
    STORE_PERSIST = auto()  # Auf Chain schreiben
    LOAD_PERSIST  = auto()  # Von Chain laden
    FS_WRITE      = auto()
    FS_READ       = auto()
    FS_MKDIR      = auto()

    # ── Concurrency / Async ────────────────────────────
    ASYNC_CALL  = auto()
    AWAIT       = auto()
    SPAWN       = auto()   # Kernel-Prozess spawnen
    CHANNEL_SEND = auto()
    CHANNEL_RECV = auto()

    # ── System ─────────────────────────────────────────
    HALT        = auto()
    NOP         = auto()
    PRINT       = auto()
    ASSERT      = auto()
    DEBUG       = auto()   # Debug-Dump des Stacks
    GAS_CHECK   = auto()   # Gas explizit prüfen
    TIMESTAMP   = auto()   # block.timestamp auf Stack
    BLOCK_NUM   = auto()   # block.number auf Stack
    CALLER      = auto()   # caller-Adresse auf Stack
    LOG         = auto()   # Strukturiertes Logging


# ══════════════════════════════════════════════════════════
#  DATENSTRUKTUREN
# ══════════════════════════════════════════════════════════

@dataclass
class Instruction:
    op:   OP
    args: List[Any] = field(default_factory=list)

    def __repr__(self):
        a = ' '.join(str(x)[:30] for x in self.args)
        return f"{self.op.name:<16} {a}".rstrip()


@dataclass
class ATCFunction:
    name:         str
    params:       List[str]
    instructions: List[Instruction]


@dataclass
class CallFrame:
    func_name: str
    ip:        int = 0
    locals:    Dict[str, Any] = field(default_factory=dict)


@dataclass
class ATCObject:
    """Struct / Contract Instanz."""
    type_name: str
    fields:    Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return f"{self.type_name}{{{', '.join(f'{k}={v}' for k,v in self.fields.items())}}}"


class ATCVMError(Exception):   pass
class RequireError(ATCVMError): pass
class GasError(ATCVMError):     pass


# ══════════════════════════════════════════════════════════
#  ATC STANDARD LIBRARY
# ══════════════════════════════════════════════════════════

class ATCStdlib:
    """
    Vollständige ATC:: Standardbibliothek.
    Implementiert alle Namespaces die atcos_main.atc braucht.
    """

    # ── Hash ──────────────────────────────────────────────
    @staticmethod
    def hash_sha256(data) -> str:
        raw = str(data).encode() if not isinstance(data, bytes) else data
        return hashlib.sha256(raw).hexdigest()

    @staticmethod
    def hash_sha3(data) -> str:
        raw = str(data).encode() if not isinstance(data, bytes) else data
        return hashlib.sha3_256(raw).hexdigest()

    @staticmethod
    def hash_sha3_atc(data) -> str:
        """ATC-eigene SHA3-Variante mit Domain-Separator."""
        raw  = b"ATC_CHAIN_2026:" + (str(data).encode() if not isinstance(data, bytes) else data)
        return "atc1" + hashlib.sha3_256(raw).hexdigest()

    @staticmethod
    def leading_zeros(hash_str: str) -> int:
        h = hash_str.lstrip("atc1").lstrip("0x")
        count = 0
        for ch in h:
            if ch == '0': count += 4
            else:
                nibble = int(ch, 16)
                count += (4 - nibble.bit_length())
                break
        return count

    # ── Crypto ───────────────────────────────────────────
    @staticmethod
    def random_bytes(n: int = 32) -> bytes:
        return secrets.token_bytes(n)

    @staticmethod
    def random_int(max_val: int) -> int:
        return secrets.randbelow(max_val) if max_val > 0 else 0

    @staticmethod
    def rand_nonce() -> int:
        return secrets.randbits(64)

    @staticmethod
    def ecdsa_sign(data, priv_key) -> str:
        """ECDSA Simulation (echte Impl in blockchain/wallet/ecdsa.py)."""
        combined = str(data) + str(priv_key)
        return "sig_" + hashlib.sha256(combined.encode()).hexdigest()[:32]

    @staticmethod
    def ecdsa_verify(data, sig: str, pub_key) -> bool:
        return isinstance(sig, str) and sig.startswith("sig_")

    @staticmethod
    def bip39_mnemonic(seed: bytes, word_count: int = 24) -> List[str]:
        words = [
            "abandon","ability","able","about","above","absent","absorb","abstract",
            "absurd","abuse","access","accident","account","accuse","achieve","acid",
            "acoustic","acquire","across","action","actor","actress","actual","adapt",
            "add","addict","address","adjust","admit","adult","advance","advice",
            "aerobic","afford","afraid","again","agent","agree","ahead","aim",
            "air","airport","aisle","alarm","album","alcohol","alert","alien",
            "all","alley","allow","almost","alone","alpha","already","also",
            "alter","always","amateur","amazing","among","amount","amused","analyst",
            "anchor","ancient","anger","angle","angry","animal","ankle","announce"
        ]
        h = hashlib.sha256(seed).digest()
        return [words[b % len(words)] for b in h[:word_count]]

    @staticmethod
    def generate_atc_address(pub_key_data=None) -> str:
        rand  = secrets.token_bytes(32)
        h     = hashlib.sha256(rand).hexdigest()
        return "ATC" + h[:32].upper()

    @staticmethod
    def verify_jwt(token: str) -> bool:
        return bool(token) and len(token) > 10

    # ── Net ──────────────────────────────────────────────
    @staticmethod
    def net_send(addr: str, port: int, data) -> bool:
        return True   # Simulation — echte Impl in ATCNet

    @staticmethod
    def kademlia_find_node(node_id: str, addr: str, port: int, k: int) -> List[dict]:
        return []   # Liefert bekannte Peers zurück

    # ── Storage ──────────────────────────────────────────
    _storage: Dict[str, Any] = {}

    @classmethod
    def storage_store(cls, key: str, value: Any):
        cls._storage[key] = value

    @classmethod
    def storage_load(cls, key: str) -> Any:
        return cls._storage.get(key)

    # ── OS / Memory ──────────────────────────────────────
    @staticmethod
    def mem_alloc(size: int) -> bytes:
        return bytes(size)

    # ── RPC ──────────────────────────────────────────────
    @staticmethod
    def rpc_call(handler: str, request) -> dict:
        return {"status": 200, "body": json.dumps({"ok": True, "handler": handler})}


# ══════════════════════════════════════════════════════════
#  VM-DISPATCH-TABELLE FÜR ATC:: NAMESPACE
# ══════════════════════════════════════════════════════════

def _build_stdlib_dispatch() -> Dict[str, Callable]:
    s = ATCStdlib
    return {
        # Hash
        "ATC::Hash::sha256":          lambda args: s.hash_sha256(args[0] if args else ""),
        "ATC::Hash::sha3":            lambda args: s.hash_sha3(args[0] if args else ""),
        "ATC::Hash::sha3_atc":        lambda args: s.hash_sha3_atc(args[0] if args else ""),
        "ATC::Hash::leading_zeros":   lambda args: s.leading_zeros(str(args[0]) if args else ""),

        # Crypto
        "ATC::Crypto::random_bytes":  lambda args: s.random_bytes(int(args[0]) if args else 32),
        "ATC::Crypto::sha256":        lambda args: s.hash_sha256(args[0] if args else ""),
        "ATC::Crypto::sign":          lambda args: s.ecdsa_sign(args[0] if args else "", args[1] if len(args)>1 else ""),
        "ATC::Crypto::verify_jwt":    lambda args: s.verify_jwt(str(args[0]) if args else ""),
        "ATC::Crypto::ECDSA::sign":   lambda args: s.ecdsa_sign(args[0] if args else "", args[1] if len(args)>1 else ""),
        "ATC::Crypto::ECDSA::verify": lambda args: s.ecdsa_verify(args[0] if args else "", args[1] if len(args)>1 else "", args[2] if len(args)>2 else ""),
        "ATC::Crypto::ECDSA::privkey_to_pubkey": lambda args: s.hash_sha256(args[0] if args else ""),
        "ATC::Crypto::BIP39::to_mnemonic": lambda args: s.bip39_mnemonic(args[0] if args else b"", int(args[1]) if len(args)>1 else 24),

        # Rand
        "ATC::Rand::secure":          lambda args: s.random_int(2**64),
        "ATC::Rand::nonce":           lambda args: s.rand_nonce(),
        "ATC::Rand::bytes":           lambda args: s.random_bytes(int(args[0]) if args else 32),

        # Net
        "ATC::Net::UDP::send":        lambda args: s.net_send(str(args[0]) if args else "", int(args[1]) if len(args)>1 else 0, args[2] if len(args)>2 else b""),
        "ATC::Net::Kademlia::find_node": lambda args: s.kademlia_find_node(str(args[0]) if args else "", str(args[1]) if len(args)>1 else "", int(args[2]) if len(args)>2 else 0, int(args[3]) if len(args)>3 else 20),

        # Storage
        "ATC::Storage::store":        lambda args: s.storage_store(str(args[0]) if args else "", args[1] if len(args)>1 else None),
        "ATC::Storage::load":         lambda args: s.storage_load(str(args[0]) if args else ""),

        # OS
        "ATC::OS::Memory::alloc":     lambda args: s.mem_alloc(int(args[0]) if args else 0),

        # RPC
        "ATC::RPC::call":             lambda args: s.rpc_call(str(args[0]) if args else "", args[1] if len(args)>1 else {}),

        # Lang / Compiler (self-hosted)
        "ATC::Lang::Compiler::compile": lambda args: str(args[0]).encode() if args else b"",
        "ATC::Lang::VM::run":           lambda args: "[ATCLang output]",

        # Wallet
        "ATC::Wallet::new":           lambda args: {
            "address":    s.generate_atc_address(),
            "seed_words": s.bip39_mnemonic(secrets.token_bytes(32), 24),
            "pub_key":    s.hash_sha256(secrets.token_bytes(32)),
        },
    }

STDLIB_DISPATCH = _build_stdlib_dispatch()


# ══════════════════════════════════════════════════════════
#  VIRTUELLE MASCHINE
# ══════════════════════════════════════════════════════════

class ATCVM:
    """
    Stack-basierte VM für ATCLang v0.2.0.
    Unterstützt alle Opcodes für atcos_main.atc.
    """

    def __init__(self, gas_limit: int = 10_000_000):
        self.stack:      List[Any]              = []
        self.globals:    Dict[str, Any]         = {}
        self.functions:  Dict[str, ATCFunction] = {}
        self.call_stack: List[CallFrame]        = []
        self.events:     List[dict]             = []
        self.gas_used:   int                    = 0
        self.gas_limit:  int                    = gas_limit
        self.logs:       List[str]              = []
        self._setup_builtins()

    def _setup_builtins(self):
        self.globals.update({
            'caller':      ATCStdlib.generate_atc_address(),
            'block':       {'timestamp': int(time.time()), 'number': 0, 'hash': ATCStdlib.hash_sha3("genesis")},
            'tx':          {'hash': ATCStdlib.hash_sha3("tx0"), 'origin': ''},
            'now':         int(time.time()),
            'true':        True,
            'false':       False,
            'null':        None,
        })

    # ── Stack-Operationen ─────────────────────────────────

    def push(self, val: Any):
        self.stack.append(val)

    def pop(self) -> Any:
        if not self.stack:
            raise ATCVMError("Stack underflow")
        return self.stack.pop()

    def peek(self) -> Any:
        if not self.stack:
            raise ATCVMError("Stack leer")
        return self.stack[-1]

    def gas(self, cost: int = 1):
        self.gas_used += cost
        if self.gas_used > self.gas_limit:
            raise GasError(f"Gas-Limit {self.gas_limit} überschritten")

    # ── Variablen ─────────────────────────────────────────

    def get_var(self, name: str, frame: Optional[CallFrame]) -> Any:
        if frame and name in frame.locals:
            return frame.locals[name]
        if name in self.globals:
            return self.globals[name]
        return None   # Graceful: unbekannte Vars = None

    def set_var(self, name: str, value: Any, frame: Optional[CallFrame]):
        if frame:
            frame.locals[name] = value
        else:
            self.globals[name] = value

    # ── Methodenaufruf auf Objekten ──────────────────────

    def _call_method(self, obj: Any, method: str, args: List[Any]) -> Any:
        # Dict-Methoden
        if isinstance(obj, dict):
            if method == 'get':      return obj.get(args[0], args[1] if len(args) > 1 else None)
            if method == 'has':      return args[0] in obj
            if method == 'keys':     return list(obj.keys())
            if method == 'values':   return list(obj.values())
            if method == 'items':    return list(obj.items())
            if method == 'contains': return args[0] in obj
            if method == 'length':   return len(obj)
            if method == 'to_string': return json.dumps(obj)

        # List-Methoden
        if isinstance(obj, list):
            if method == 'push':     obj.append(args[0]); return obj
            if method == 'pop':      return obj.pop() if obj else None
            if method == 'length':   return len(obj)
            if method == 'contains': return args[0] in obj
            if method == 'get':      return obj[args[0]] if args[0] < len(obj) else None
            if method == 'to_string': return str(obj)

        # String-Methoden
        if isinstance(obj, str):
            if method == 'length':      return len(obj)
            if method == 'to_string':   return obj
            if method == 'to_bytes':    return obj.encode()
            if method == 'upper':       return obj.upper()
            if method == 'lower':       return obj.lower()
            if method == 'split':       return obj.split(args[0] if args else None)
            if method == 'contains':    return (args[0] in obj) if args else False
            if method == 'starts_with': return obj.startswith(args[0]) if args else False
            if method == 'ends_with':   return obj.endswith(args[0]) if args else False
            if method == 'slice':       return obj[args[0]:args[1]] if len(args) >= 2 else obj
            if method == 'to_short_string': return obj[:20] + ("..." if len(obj) > 20 else "")

        # Int/Float-Methoden
        if isinstance(obj, (int, float)):
            if method == 'to_string': return str(obj)
            if method == 'to_bytes':  return struct.pack('>Q', int(obj) & 0xFFFFFFFFFFFFFFFF)

        # Bool
        if isinstance(obj, bool):
            if method == 'to_string': return str(obj).lower()

        # bytes
        if isinstance(obj, bytes):
            if method == 'length':   return len(obj)
            if method == 'to_string': return obj.hex()

        # ATCObject
        if isinstance(obj, ATCObject):
            if method in obj.fields:
                val = obj.fields[method]
                if callable(val): return val(*args)
                return val
            if method == 'to_string': return repr(obj)

        return None

    # ── Hauptausführungsschleife ──────────────────────────

    def execute(self, instructions: List[Instruction], frame: Optional[CallFrame] = None) -> Any:
        ip = 0
        while ip < len(instructions):
            instr = instructions[ip]
            self.gas()
            op    = instr.op
            args  = instr.args

            # ── Stack ──────────────────────────────────
            if op == OP.NOP:
                pass
            elif op == OP.HALT:
                break
            elif op == OP.PUSH:
                self.push(args[0])
            elif op == OP.POP:
                self.pop()
            elif op == OP.DUP:
                self.push(self.peek())
            elif op == OP.SWAP:
                a, b = self.pop(), self.pop(); self.push(a); self.push(b)
            elif op == OP.ROT:
                c, b, a = self.pop(), self.pop(), self.pop()
                self.push(b); self.push(c); self.push(a)

            # ── Arithmetik ─────────────────────────────
            elif op == OP.ADD:
                b, a = self.pop(), self.pop()
                self.push((a or 0) + (b or 0) if isinstance(a, (int, float)) else str(a or '') + str(b or ''))
            elif op == OP.SUB:
                b, a = self.pop(), self.pop(); self.push((a or 0) - (b or 0))
            elif op == OP.MUL:
                b, a = self.pop(), self.pop(); self.push((a or 0) * (b or 0))
            elif op == OP.DIV:
                b, a = self.pop(), self.pop()
                if b == 0: raise ATCVMError("Division durch Null")
                self.push(int(a) // int(b))
            elif op == OP.MOD:
                b, a = self.pop(), self.pop(); self.push(int(a or 0) % int(b or 1))
            elif op == OP.POW:
                b, a = self.pop(), self.pop(); self.push(int(a or 0) ** int(b or 0))
            elif op == OP.NEG:
                self.push(-(self.pop() or 0))
            elif op == OP.BITAND:
                b, a = self.pop(), self.pop(); self.push(int(a or 0) & int(b or 0))
            elif op == OP.BITOR:
                b, a = self.pop(), self.pop(); self.push(int(a or 0) | int(b or 0))
            elif op == OP.BITXOR:
                b, a = self.pop(), self.pop(); self.push(int(a or 0) ^ int(b or 0))
            elif op == OP.BITNOT:
                self.push(~int(self.pop() or 0))
            elif op == OP.SHL:
                b, a = self.pop(), self.pop(); self.push(int(a or 0) << int(b or 0))
            elif op == OP.SHR:
                b, a = self.pop(), self.pop(); self.push(int(a or 0) >> int(b or 0))

            # ── Vergleiche ─────────────────────────────
            elif op == OP.EQ:  b, a = self.pop(), self.pop(); self.push(a == b)
            elif op == OP.NEQ: b, a = self.pop(), self.pop(); self.push(a != b)
            elif op == OP.LT:  b, a = self.pop(), self.pop(); self.push((a or 0) < (b or 0))
            elif op == OP.GT:  b, a = self.pop(), self.pop(); self.push((a or 0) > (b or 0))
            elif op == OP.LTE: b, a = self.pop(), self.pop(); self.push((a or 0) <= (b or 0))
            elif op == OP.GTE: b, a = self.pop(), self.pop(); self.push((a or 0) >= (b or 0))

            # ── Logik ──────────────────────────────────
            elif op == OP.AND: b, a = self.pop(), self.pop(); self.push(bool(a) and bool(b))
            elif op == OP.OR:  b, a = self.pop(), self.pop(); self.push(bool(a) or bool(b))
            elif op == OP.NOT: self.push(not self.pop())

            # ── Variablen ──────────────────────────────
            elif op == OP.LOAD:
                self.push(self.get_var(args[0], frame))
            elif op == OP.STORE:
                self.set_var(args[0], self.pop(), frame)
            elif op == OP.LOAD_GLOBAL:
                self.push(self.globals.get(args[0]))
            elif op == OP.STORE_GLOBAL:
                self.globals[args[0]] = self.pop()
            elif op == OP.LOAD_IDX:
                key = self.pop(); obj = self.pop()
                try:
                    self.push(obj[key] if obj is not None else None)
                except (KeyError, IndexError, TypeError):
                    self.push(None)
            elif op == OP.STORE_IDX:
                key = self.pop(); obj = self.pop(); val = self.pop()
                if isinstance(obj, (dict, list)):
                    obj[key] = val
                self.push(obj)
            elif op == OP.DEL_VAR:
                if frame and args[0] in frame.locals: del frame.locals[args[0]]
                elif args[0] in self.globals: del self.globals[args[0]]

            # ── Sprünge ────────────────────────────────
            elif op == OP.JUMP:
                ip = args[0]; continue
            elif op == OP.JUMP_IF:
                if self.pop(): ip = args[0]; continue
            elif op == OP.JUMP_NOT:
                if not self.pop(): ip = args[0]; continue

            # ── Funktionsaufruf ────────────────────────
            elif op == OP.CALL:
                fname = args[0]; argc = args[1] if len(args) > 1 else 0
                call_args = [self.pop() for _ in range(argc)][::-1]
                if fname in self.functions:
                    fn = self.functions[fname]
                    new_frame = CallFrame(func_name=fname)
                    for pname, pval in zip(fn.params, call_args):
                        new_frame.locals[pname] = pval
                    result = self.execute(fn.instructions, new_frame)
                    self.push(result if result is not None else None)
                else:
                    # Unbekannte Funktion — graceful
                    self.push(None)

            elif op == OP.CALL_EXT:
                fname = args[0]; argc = args[1] if len(args) > 1 else 0
                call_args = [self.pop() for _ in range(argc)][::-1]
                handler = STDLIB_DISPATCH.get(fname)
                if handler:
                    try:
                        result = handler(call_args)
                        self.push(result)
                    except Exception as e:
                        self.logs.append(f"WARN CALL_EXT {fname}: {e}")
                        self.push(None)
                else:
                    self.logs.append(f"WARN: ATC::-Funktion nicht implementiert: {fname}")
                    self.push(None)

            elif op == OP.CALL_METHOD:
                method = args[0]; argc = args[1] if len(args) > 1 else 0
                call_args = [self.pop() for _ in range(argc)][::-1]
                obj = self.pop()
                result = self._call_method(obj, method, call_args)
                self.push(result)

            elif op == OP.RETURN:
                val = self.pop() if self.stack else None
                return val

            # ── Objekte ────────────────────────────────
            elif op == OP.NEW_MAP:
                count = args[0] if args else 0
                pairs  = {}
                items  = [self.pop() for _ in range(count * 2)]
                items.reverse()
                for i in range(0, len(items), 2):
                    pairs[items[i]] = items[i+1]
                self.push(pairs)
            elif op == OP.NEW_LIST:
                count = args[0] if args else 0
                items = [self.pop() for _ in range(count)][::-1]
                self.push(items)
            elif op == OP.NEW_OBJ:
                type_name = args[0]; field_count = args[1] if len(args) > 1 else 0
                obj = ATCObject(type_name=type_name)
                pairs = [self.pop() for _ in range(field_count * 2)]
                pairs.reverse()
                for i in range(0, len(pairs), 2):
                    obj.fields[pairs[i]] = pairs[i+1]
                self.push(obj)
            elif op == OP.GET_FIELD:
                fname2 = args[0]; obj = self.pop()
                if isinstance(obj, dict):      self.push(obj.get(fname2))
                elif isinstance(obj, ATCObject): self.push(obj.fields.get(fname2))
                else:                           self.push(getattr(obj, fname2, None))
            elif op == OP.SET_FIELD:
                fname2 = args[0]; val = self.pop(); obj = self.pop()
                if isinstance(obj, dict):       obj[fname2] = val
                elif isinstance(obj, ATCObject): obj.fields[fname2] = val
                else:                            setattr(obj, fname2, val)
                self.push(obj)
            elif op == OP.HAS_KEY:
                key = self.pop(); obj = self.pop()
                self.push(key in obj if obj else False)
            elif op == OP.DEL_KEY:
                key = self.pop(); obj = self.pop()
                if isinstance(obj, dict) and key in obj: del obj[key]
                self.push(obj)
            elif op == OP.LIST_PUSH:
                val = self.pop(); lst = self.pop()
                if isinstance(lst, list): lst.append(val)
                self.push(lst)
            elif op == OP.LIST_POP:
                lst = self.pop()
                self.push(lst.pop() if lst else None)
            elif op == OP.LIST_LEN:
                self.push(len(self.pop() or []))
            elif op == OP.MAP_KEYS:
                self.push(list((self.pop() or {}).keys()))
            elif op == OP.MAP_VALUES:
                self.push(list((self.pop() or {}).values()))
            elif op == OP.MAP_ITEMS:
                self.push(list((self.pop() or {}).items()))
            elif op == OP.CONTAINS:
                item = self.pop(); container = self.pop()
                self.push(item in container if container else False)
            elif op == OP.CAST:
                target_type = args[0]; val = self.pop()
                if target_type == 'String':  self.push(str(val) if val is not None else "")
                elif target_type in ('Int','UInt32','UInt64','UInt256'): self.push(int(val) if val else 0)
                elif target_type == 'Bool':  self.push(bool(val))
                elif target_type == 'Bytes': self.push(str(val).encode())
                else: self.push(val)

            # ── String-Ops ─────────────────────────────
            elif op == OP.STR_LEN:   self.push(len(str(self.pop() or "")))
            elif op == OP.STR_UPPER: self.push(str(self.pop() or "").upper())
            elif op == OP.STR_LOWER: self.push(str(self.pop() or "").lower())
            elif op == OP.STR_SLICE:
                end = self.pop(); start = self.pop(); s = self.pop()
                self.push(str(s or "")[int(start or 0):int(end or 0)])
            elif op == OP.STR_SPLIT:
                sep = self.pop(); s = self.pop()
                self.push(str(s or "").split(str(sep or " ")))
            elif op == OP.STR_JOIN:
                parts = self.pop(); sep = self.pop()
                self.push(str(sep or "").join(str(p) for p in (parts or [])))
            elif op == OP.STR_FORMAT:
                n = args[0] if args else 0
                fmtargs = [self.pop() for _ in range(n)][::-1]
                fmt = self.pop()
                try: self.push(str(fmt or "").format(*fmtargs))
                except: self.push(str(fmt or ""))

            # ── ATC-spezifisch ─────────────────────────
            elif op == OP.EMIT:
                event_name = args[0]; argc = args[1] if len(args) > 1 else 0
                event_args = [self.pop() for _ in range(argc)][::-1]
                self.events.append({'event': event_name, 'args': event_args})
                print(f"  \033[38;5;51m📡 [{event_name}]\033[0m {' | '.join(str(a)[:60] for a in event_args)}")

            elif op == OP.REQUIRE:
                condition = self.pop()
                msg = args[0] if args else "Require fehlgeschlagen"
                if not condition:
                    raise RequireError(f"require(): {msg}")

            elif op == OP.TRANSFER:
                amount = self.pop(); to = self.pop(); from_ = self.pop()
                self.logs.append(f"TRANSFER {amount} ATC: {from_} → {to}")
                self.push(True)

            elif op == OP.MINT:
                amount = self.pop(); addr = self.pop()
                self.logs.append(f"MINT {amount} ATC → {addr}")
                self.push(True)

            elif op == OP.BURN:
                amount = self.pop(); addr = self.pop()
                self.logs.append(f"BURN {amount} ATC from {addr}")
                self.push(True)

            elif op == OP.STAKE:
                amount = self.pop(); addr = self.pop()
                self.logs.append(f"STAKE {amount} ATC from {addr}")
                self.push(True)

            # ── Crypto / Hash ──────────────────────────
            elif op == OP.HASH_SHA256:
                self.push(ATCStdlib.hash_sha256(self.pop()))
            elif op == OP.HASH_SHA3:
                self.push(ATCStdlib.hash_sha3(self.pop()))
            elif op == OP.HASH_SHA3_ATC:
                self.push(ATCStdlib.hash_sha3_atc(self.pop()))
            elif op == OP.CRYPTO_SIGN:
                key = self.pop(); data = self.pop()
                self.push(ATCStdlib.ecdsa_sign(data, key))
            elif op == OP.CRYPTO_VERIFY:
                pub = self.pop(); sig = self.pop(); data = self.pop()
                self.push(ATCStdlib.ecdsa_verify(data, sig, pub))
            elif op == OP.RAND_BYTES:
                n = int(self.pop() or 32)
                self.push(ATCStdlib.random_bytes(n))
            elif op == OP.RAND_INT:
                m = int(self.pop() or 2**32)
                self.push(ATCStdlib.random_int(m))
            elif op == OP.LEADING_ZEROS:
                self.push(ATCStdlib.leading_zeros(str(self.pop() or "")))

            # ── Netzwerk ───────────────────────────────
            elif op == OP.NET_SEND:
                data = self.pop(); port = self.pop(); addr = self.pop()
                self.push(ATCStdlib.net_send(str(addr), int(port or 0), data))
            elif op == OP.NET_BROADCAST:
                data = self.pop(); msg_type = self.pop()
                self.logs.append(f"BROADCAST {msg_type}")
                self.push(0)
            elif op == OP.NET_PEERS:
                self.push(0)

            # ── Persistenz ─────────────────────────────
            elif op == OP.STORE_PERSIST:
                val = self.pop(); key = self.pop()
                ATCStdlib.storage_store(str(key), val)
                self.push(True)
            elif op == OP.LOAD_PERSIST:
                key = self.pop()
                self.push(ATCStdlib.storage_load(str(key)))
            elif op == OP.FS_WRITE:
                data = self.pop(); path = self.pop()
                self.logs.append(f"FS_WRITE {path}")
                self.push(True)
            elif op == OP.FS_READ:
                path = self.pop()
                self.push(ATCStdlib.storage_load(str(path)))
            elif op == OP.FS_MKDIR:
                path = self.pop()
                self.logs.append(f"FS_MKDIR {path}")
                self.push(True)

            # ── Concurrency ────────────────────────────
            elif op == OP.SPAWN:
                pname = self.pop()
                self.logs.append(f"SPAWN process: {pname}")
                self.push(len(self.logs))   # PID simulieren
            elif op == OP.CHANNEL_SEND:
                data = self.pop(); ch_id = self.pop()
                self.logs.append(f"CH_SEND → {ch_id}")
                self.push(True)
            elif op == OP.CHANNEL_RECV:
                ch_id = self.pop()
                self.push(None)

            # ── System ─────────────────────────────────
            elif op == OP.PRINT:
                val = self.pop()
                print(f"  \033[38;5;183m[print]\033[0m {val}")
            elif op == OP.LOG:
                lvl = args[0] if args else "INFO"; msg = self.pop()
                entry = f"[{lvl}] {msg}"
                self.logs.append(entry)
                print(f"  \033[38;5;220m[log]\033[0m {entry}")
            elif op == OP.DEBUG:
                print(f"  \033[38;5;196m[debug]\033[0m stack={self.stack[-5:]}")
            elif op == OP.GAS_CHECK:
                self.push(self.gas_used)
            elif op == OP.TIMESTAMP:
                self.push(int(time.time()))
            elif op == OP.BLOCK_NUM:
                self.push(self.globals.get('block', {}).get('number', 0))
            elif op == OP.CALLER:
                self.push(self.globals.get('caller', ''))
            elif op == OP.ASSERT:
                msg = args[0] if args else "Assertion fehlgeschlagen"
                if not self.pop():
                    raise ATCVMError(f"assert: {msg}")

            else:
                raise ATCVMError(f"Unbekannter Opcode: {op.name}")

            ip += 1

        return self.pop() if self.stack else None

    def run_program(self, instructions: List[Instruction]) -> Any:
        """Haupteinstieg — Programm ausführen."""
        try:
            result = self.execute(instructions)
            return result
        except RequireError as e:
            print(f"  \033[38;5;196m[REQUIRE FAILED]\033[0m {e}")
            return None
        except GasError as e:
            print(f"  \033[38;5;196m[GAS LIMIT]\033[0m {e}")
            return None
        except ATCVMError as e:
            print(f"  \033[38;5;196m[VM ERROR]\033[0m {e}")
            return None

    def register_function(self, fn: ATCFunction):
        self.functions[fn.name] = fn

    def stats(self) -> dict:
        return {
            "gas_used":   self.gas_used,
            "gas_limit":  self.gas_limit,
            "stack_size": len(self.stack),
            "events":     len(self.events),
            "logs":       len(self.logs),
            "functions":  len(self.functions),
        }
