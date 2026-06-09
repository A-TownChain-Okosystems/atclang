"""
ATCLang Standard Library v0.3.0
Eingebaute Funktionen, Typen und ATC-spezifische Operationen.
"""

# ── Built-in Functions ────────────────────────────
BUILTINS = {
    # I/O
    "print":    lambda *args: print(*args),
    "input":    lambda prompt="": input(prompt),
    "read":     lambda f: open(f).read(),
    "write":    lambda f, d: open(f, "w").write(d),

    # Typen
    "int":      int,
    "float":    float,
    "str":      str,
    "bool":     bool,
    "list":     list,
    "dict":     dict,
    "len":      len,
    "range":    range,
    "type":     type,

    # Math
    "abs":      abs,
    "min":      min,
    "max":      max,
    "sum":      sum,
    "round":    round,
    "pow":      pow,

    # Blockchain-Builtins
    "sha256":   lambda s: __import__("hashlib").sha256(str(s).encode()).hexdigest(),
    "sha3":     lambda s: __import__("hashlib").sha3_256(str(s).encode()).hexdigest(),
    "timestamp": lambda: __import__("time").time(),
    "uuid":     lambda: str(__import__("uuid").uuid4()),

    # ATC-spezifische
    "atc_addr": lambda pk: "ATC" + __import__("hashlib").sha256(pk.encode()).hexdigest()[:32],
    "atc_sign": lambda msg, key: __import__("hashlib").sha256(f"{msg}{key}".encode()).hexdigest(),
    "atc_verify": lambda msg, key, sig: sig == __import__("hashlib").sha256(f"{msg}{key}".encode()).hexdigest(),
}

# ── ATC Standard Types ────────────────────────────
ATC_TYPES = {
    "Address":    str,
    "Hash":       str,
    "Amount":     float,
    "Timestamp":  float,
    "NodeId":     str,
    "DID":        str,
    "TxHash":     str,
}

# ── Error Types ───────────────────────────────────
class ATCError(Exception):
    """Basis-Fehlertyp für ATCLang."""
    pass

class ATCTypeError(ATCError): pass
class ATCRuntimeError(ATCError): pass
class ATCAccessDenied(ATCError): pass
class ATCContractError(ATCError): pass

# ── Version ───────────────────────────────────────
ATCLANG_VERSION = "0.3.0"
STDLIB_VERSION  = "0.3.0"
