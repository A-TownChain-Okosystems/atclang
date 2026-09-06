# ATCLang Language Specification v1.0

**Version:** 1.0.0  
**Datum:** 2026-07-05  
**Status:** STABLE  
**Standard:** ATC-92  
**Autor:** Michael Wroblewski / Aurora  

---

## 1. Übersicht

ATCLang ist eine statisch typisierte, blockchain-native Programmiersprache für das A-TownChain Ökosystem. Sie verfügt über eine eigene Grammatik, einen eigenen Compiler und eine eigene virtuelle Maschine (ATCVM).

### Design-Prinzipien
- **Blockchain-First:** Eingebaute Support für Contracts, Wallets, Events, Gas
- **Statisch Typisiert:** Alle Typen zur Compile-Zeit geprüft
- **Sicher:** Kein undefiniertes Verhalten, keine Null-Pointer-Dereferenzierung
- **Deterministisch:** Gleicher Input → gleicher Output auf jeder Node
- **Eigene VM:** Keine Abhängigkeit von Python-Runtime

---

## 2. Lexikalische Struktur

### 2.1 Keywords (34)

| Keyword | Beschreibung |
|---------|-------------|
| `contract` | Smart Contract Definition |
| `fn` | Funktionsdefinition |
| `state` | Zustandsfeld in Contract |
| `emit` | Event auslösen |
| `require` | Assertion (wirft bei False) |
| `return` | Rückgabe |
| `wallet` | Wallet-Objekt erstellen |
| `let` | Mutable Variable |
| `const` | Immutable Variable |
| `if` / `else` | Bedingte Verzweigung |
| `for` / `in` | Schleife über Iterables |
| `while` | Bedingte Schleife |
| `break` / `continue` | Schleifenkontrolle |
| `match` | Pattern Matching |
| `struct` | Struktur-Definition |
| `enum` | Aufzählungstyp |
| `import` / `use` | Modul-Import |
| `pub` / `priv` | Sichtbarkeit |
| `type` | Typ-Alias |
| `trait` / `impl` | Trait-System |
| `async` / `await` | Asynchrone Operationen |
| `spawn` | Kernel-Prozess starten |
| `self` | Aktueller Contract-Kontext |
| `true` / `false` | Boolean-Literale |

### 2.2 Token-Typen

| Kategorie | Beispiele |
|-----------|----------|
| KEYWORD | `contract`, `fn`, `if`, `let`, `return` |
| TYPE | `UInt256`, `Address`, `Bool`, `String`, `Map`, `List`, `Bytes` |
| OPERATOR | `+`, `-`, `*`, `/`, `%`, `>=`, `<=`, `==`, `!=`, `->`, `::`, `<<`, `>>` |
| LITERAL | `42`, `3.14`, `"hello"`, `true`, `nil` |
| SPECIAL | `ATC::` (Namespace), `@decorator` |
| DELIMITER | `(`, `)`, `{`, `}`, `[`, `]`, `;`, `,`, `:` |

### 2.3 Datentypen

#### Primitive Typen
| Typ | Größe | Bereich |
|-----|-------|---------|
| `Bool` | 1 byte | `true` / `false` |
| `Int8` / `Int16` / `Int32` / `Int64` / `Int128` / `Int256` | 1-32 bytes | Signed Integer |
| `UInt8` / `UInt16` / `UInt32` / `UInt64` / `UInt128` / `UInt256` | 1-32 bytes | Unsigned Integer |
| `Float32` / `Float64` / `Float128` | 4-16 bytes | Floating Point |
| `Address` | 20 bytes | Krypto-Adresse |
| `String` | Variabel | UTF-8 Zeichenkette |
| `Bytes` | Variabel | Byte-Folge |

#### Zusammengesetzte Typen
| Typ | Syntax | Beschreibung |
|-----|--------|-------------|
| `List<T>` | `[1, 2, 3]` | Geordnete Liste |
| `Map<K,V>` | `{a: 1, b: 2}` | Key-Value Mapping |
| `Tuple` | `(1, "a", true)` | Heterogene Sequenz |
| `Range` | `0..10` | Bereichsausdruck |
| `Slice` | `arr[1:3]` | Teilsequenz |

#### Blockchain-Typen
| Typ | Beschreibung |
|-----|-------------|
| `Hash256` / `Hash512` | Krypto-Hash |
| `BlockHash` | Block-Referenz |
| `CID` | Content Identifier |
| `Timestamp` | Unix-Zeitstempel |

---

## 3. Grammatik (EBNF)

```ebnf
program       = { import_stmt | top_decl } ;
import_stmt   = "import" string_lit [ "as" ident ] ";" ;
top_decl      = contract_decl | wallet_decl | struct_decl | enum_decl
              | fn_decl | trait_decl | impl_decl | type_alias ;
contract_decl = "contract" ident [ ":" standard ] "{" { state_field | fn_decl | event_decl } "}" ;
wallet_decl   = "wallet" ident "=" expr ";" ;
struct_decl   = "struct" ident "{" { field_decl } "}" ;
enum_decl     = "enum" ident "{" { ident } "}" ;
fn_decl       = [ "pub" | "priv" ] "fn" ident "(" [ params ] ")" [ "->" type ] block ;
state_field   = "state" ident ":" type [ "=" expr ] ";" ;
event_decl    = "emit" ident "(" [ params ] ")" ";" ;
params        = param { "," param } ;
param         = ident ":" type ;
block         = "{" { stmt } "}" ;
stmt          = let_stmt | const_stmt | expr_stmt | return_stmt
              | if_stmt | for_stmt | while_stmt | emit_stmt
              | require_stmt | break_stmt | continue_stmt
              | match_stmt | assign_stmt ;
let_stmt      = "let" ident [ ":" type ] "=" expr ";" ;
const_stmt    = "const" ident [ ":" type ] "=" expr ";" ;
if_stmt       = "if" expr block [ "else" ( if_stmt | block ) ] ;
for_stmt      = "for" ident "in" expr block ;
while_stmt    = "while" expr block ;
match_stmt    = "match" expr "{" { match_arm } "}" ;
match_arm     = pattern "=>" expr [ "," ] ;
emit_stmt     = "emit" ident "(" [ args ] ")" ";" ;
require_stmt  = "require" expr [ "," string_lit ] ";" ;
return_stmt   = "return" [ expr ] ";" ;
expr          = or_expr ;
or_expr       = and_expr { "or" and_expr } ;
and_expr      = not_expr { "and" not_expr } ;
not_expr      = "not" not_expr | comparison ;
comparison    = add_expr [ ( "==" | "!=" | "<" | ">" | "<=" | ">=" ) add_expr ] ;
add_expr      = mul_expr { ( "+" | "-" ) mul_expr } ;
mul_expr      = unary { ( "*" | "/" | "%" ) unary } ;
unary         = ( "-" | "not" ) unary | postfix ;
postfix       = primary { "." ident | "[" expr "]" | "(" args ")" } ;
primary       = literal | ident | "(" expr ")" | namespace_expr
              | list_lit | map_lit | struct_lit ;
namespace_expr = "ATC::" ident { "::" ident } ;
list_lit      = "[" [ expr { "," expr } ] "]" ;
map_lit       = "{" [ expr ":" expr { "," expr ":" expr } ] "}" ;
```

---

## 4. AST-Knoten (41)

| Knoten | Beschreibung |
|--------|-------------|
| `Program` | Wurzel-Knoten, enthält alle Deklarationen |
| `ContractDef` | Smart Contract Definition |
| `WalletDef` | Wallet-Objekt |
| `FunctionDef` | Funktionsdefinition |
| `StructDef` / `EnumDef` | Typ-Definitionen |
| `ImportStatement` | Modul-Import |
| `LetStatement` / `ReturnStatement` | Anweisungen |
| `EmitStatement` / `RequireStatement` | Blockchain-Anweisungen |
| `IfStatement` / `ForStatement` / `WhileStatement` | Kontrollfluss |
| `MatchStatement` | Pattern Matching |
| `BinaryOp` / `UnaryOp` | Operationen |
| `Assignment` / `IndexAccess` / `DotAccess` | Zugriff |
| `NamespaceAccess` | ATC:: Namespace |
| `FunctionCall` | Funktionsaufruf |
| `IntLiteral` / `FloatLiteral` / `StringLiteral` / `BoolLiteral` | Literale |
| `ListLiteral` / `MapLiteral` / `NullLiteral` | Container |
| `Identifier` / `Parameter` / `StateField` / `EventDef` / `ErrorDef` | Definitionen |
| `StructLiteral` / `TupleExpr` / `RangeExpr` / `SliceExpr` | Ausdrücke |

---

## 5. Contract-System

### 5.1 Contract-Definition
```atclang
contract MyToken : ATC-8300 {
    state balance: Map<Address, UInt256>
    state total_supply: UInt256 = 0
    
    event Transfer(from: Address, to: Address, amount: UInt256)
    
    pub fn mint(to: Address, amount: UInt256) -> Bool {
        require(amount > 0, "Amount must be positive")
        balance[to] = balance[to] + amount
        total_supply = total_supply + amount
        emit Transfer(self, to, amount)
        return true
    }
    
    pub fn transfer(to: Address, amount: UInt256) -> Bool {
        require(balance[caller] >= amount, "Insufficient balance")
        balance[caller] = balance[caller] - amount
        balance[to] = balance[to] + amount
        emit Transfer(caller, to, amount)
        return true
    }
}
```

### 5.2 Standards
- **ATC-8300**: Fungible Token Standard
- **ATC-9000**: NFT Standard (Shivamon)
- **ATC-9900**: Governance Standard

---

## 6. Standard Library (ATC::)

| Namespace | Funktionen |
|-----------|-----------|
| `ATC::Wallet` | `new()`, `transfer()`, `balance()`, `mint()`, `burn()` |
| `ATC::Math` | `add()`, `sub()`, `mul()`, `div()`, `sqrt()`, `pow()` |
| `ATC::Crypto` | `sha256()`, `sha3()`, `sign()`, `verify()`, `base58()` |
| `ATC::IO` | `print()`, `read()`, `write()`, `format()` |
| `ATC::Collections` | `map_new()`, `map_get()`, `map_set()`, `array_new()` |
| `ATC::Encoding` | `json_encode()`, `json_decode()`, `cbor_encode()`, `rlp_encode()` |
| `ATC::Chain` | `block_number()`, `block_hash()`, `timestamp()`, `chain_id()` |
| `ATC::String` | `len()`, `upper()`, `lower()`, `split()`, `join()` |

---

## 7. Decorators

| Decorator | Beschreibung |
|-----------|-------------|
| `@payable` | Funktion akzeptiert ATC-Zahlungen |
| `@view` | Read-only Funktion (kein State-Change) |
| `@pure` | Kein State-Access |
| `@gas(n)` | Explizite Gas-Limit |
| `@external` | Nur von externen Contracts aufrufbar |
| `@inline` | Compiler inline-expandiert |

---

## 8. Error-Handling

```atclang
fn risky_op(x: UInt256) -> UInt256 {
    require(x > 0, "x must be positive")
    if x > 100 {
        return x * 2
    }
    return x
}
```

Errors brechen die Transaktion ab und verbrauchen das gesamte Gas.

---

## 9. Kompilierungs-Pipeline

```
Source (.atc) → Lexer → Token Stream → Parser → AST
    → Type Checker → Optimizer → Compiler → Bytecode
    → ATCVM → Execution
```

---

## 10. Beispiel-Programm

```atclang
import "std/wallet.atc" as Wallet

contract ShivaToken : ATC-8300 {
    state balances: Map<Address, UInt256>
    state owner: Address
    
    event Transfer(from: Address, to: Address, amount: UInt256)
    event Approval(owner: Address, spender: Address, amount: UInt256)
    
    pub fn constructor() {
        owner = caller
        balances[owner] = 21000000
    }
    
    pub fn transfer(to: Address, amount: UInt256) -> Bool {
        require(balances[caller] >= amount, "Insufficient")
        balances[caller] -= amount
        balances[to] += amount
        emit Transfer(caller, to, amount)
        return true
    }
    
    @view
    pub fn balance_of(addr: Address) -> UInt256 {
        return balances[addr]
    }
}
```

---

*ATCLang Spec v1.0 — ATC-92 — 2026-07-05*
