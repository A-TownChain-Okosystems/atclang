# ATCLang 1.0 — Language Specification

**Gate:** G1 (AD-022) · **Status:** PASSED, 07.09.2026 · **Referenz-Implementierung:** Python, src/atclang (Commit a7e1bd4)

**Normativitäts-Regel:** Diese Spezifikation ist aus der Referenz-Implementierung
extrahiert und muss mit ihr uebereinstimmen. Abweichungen zwischen SPEC und
Referenz sind FEHLER: entweder Referenz-Fix oder Spec-Revision mit Versions-Bump.
Maschinenlesbares Extrakt: `specs/language/registry.json`.

## 1. Design-Gruendsaetze

1. **Kernsatz (AD-022):** Compiler erzeugt Code — Verifier entscheidet Gueltigkeit —
   ATVM fuehrt ausschliesslich Verifiziertes deterministisch aus.
2. ATCLang ist deterministisch, capability-freundlich und blockchain-nativ
   (Smart Contracts, Wallets, Events, Require-Checks als Sprachkonstrukte).
3. Layout ist einrueckungsbasiert (NEWLINE/INDENT/DEDENT, Python-Konvention).

## 2. Lexikalische Struktur (Quelle: frontend/lexer/lexer.py)

### 2.1 Token-Inventar (63 Tokens)

| Token | Token | Token | Token | Token |
|---|---|---|---|---|
| INT | FLOAT | STRING | BOOL | HEX_INT |
| OCTAL_INT | BIN_INT | BYTES_LIT | IDENT | KEYWORD |
| TYPE | ATC_STD | PLUS | MINUS | STAR |
| SLASH | PERCENT | STARSTAR | PLUSEQ | MINUSEQ |
| STAREQ | SLASHEQ | EQ | EQEQ | NEQ |
| LT | GT | LTE | GTE | AMP |
| PIPE | CARET | TILDE | LSHIFT | RSHIFT |
| AND | OR | NOT | ARROW | FAT_ARROW |
| DCOLON | ASSIGN | QUESTION | DOTDOT | DOTDOTEQ |
| HASH | AT | LPAREN | RPAREN | LBRACE |
| RBRACE | LBRACKET | RBRACKET | COMMA | COLON |
| SEMICOLON | DOT | UNDERSCORE | NEWLINE | INDENT |
| DEDENT | EOF | COMMENT |

### 2.2 Literale

| Literal | Token | Beispiel |
|---|---|---|
| Dezimal-Integer | INT | `42` |
| Hexadezimal | HEX_INT | `0xFF` |
| Oktal | OCTAL_INT | `0o755` |
| Binaer | BIN_INT | `0b1010` |
| Float | FLOAT | `3.14` |
| String | STRING | `"atc"` |
| Bytes | BYTES_LIT | `b"\x00"` |
| Boolean | BOOL | `true`, `false` |
| Null | KEYWORD `null` | `null` |

### 2.3 Schluesselwoerter (76, gruppiert)

**Deklarationen:** `wallet`, `contract`, `struct`, `enum`, `impl`, `trait`, `fn`, `state`, `let`, `const`, `pub`, `priv`, `static`, `type`, `interface`
**Kontrollfluss:** `if`, `else`, `elif`, `for`, `while`, `loop`, `in`, `break`, `continue`, `return`, `match`, `case`
**Funktions-Modifikatoren:** `async`, `await`, `deploy`, `call`, `new`, `delete`, `import`, `from`, `as`, `use`
**Blockchain-Nativ:** `emit`, `require`, `event`, `error`, `assert`, `genesis`, `mint`, `burn`, `stake`, `unstake`, `vote`, `transfer`, `approve`, `delegate`
**System/OS:** `node`, `consensus`, `kernel`, `process`, `spawn`, `channel`, `syscall`, `interrupt`
**Typen-Kontext:** `self`, `caller`, `block`, `tx`, `null`, `true`, `false`
**Modifikatoren:** `override`, `virtual`, `abstract`, `final`, `inline`, `extern`, `unsafe`, `packed`
**Generics/Traits:** `where`, `with`

Lexikalische Besonderheit (normativ, aus parser.py parse_let): `let`/`const`
akzeptieren reservierte Blockchain-/OS-Keywords als Variablennamen
(state, event, error, transfer, mint, burn, stake, process, channel, node,
consensus, kernel, spawn, ...).

### 2.4 Typ-Bezeichner (84, gruppiert)

**Integer:** UInt8, UInt16, UInt32, UInt64, UInt128, UInt256, Int8, Int16, Int32, Int64, Int128, Int256, USize, ISize
**Float:** Float32, Float64, Float128
**Primitiv:** Bool, Char, Byte, String, Bytes, Str
**Blockchain:** Address, Hash256, Hash512, PubKey, PrivKey, Signature, TxHash, BlockHash, CID
**Kollektionen:** Map, List, Set, Array, Vec, Tuple, Option, Result, Either
**ATC-Standards:** ATC8300, ATC9000, ATCContract, ATCWallet, ATCBlock, ATCTx
**OS:** Process, Thread, Channel, Mutex, Semaphore, INode, FileHandle, DirHandle
**Netzwerk:** Peer, NodeID, Port, IPAddr
**Generisch:** Any, Void, Never
**Rust-Stil-Aliase:** u8, u16, u32, u64, u128, u256, i8, i16, i32, i64, i128, i256, f32, f64, f128, bool, char, byte, string, bytes, usize, isize

### 2.5 ATC-Namespaces (31)

`ATC8300`, `ATC9000`, `ATCContract`, `ATCWallet`, `ATCBlock`, `ATCTx`, `ATC`, `ATC::Hash`, `ATC::Crypto`, `ATC::Rand`, `ATC::Net`, `ATC::Net::UDP`, `ATC::Net::Kademlia`, `ATC::OS`, `ATC::OS::Memory`, `ATC::OS::Kernel`, `ATC::OS::Filesystem`, `ATC::Storage`, `ATC::RPC`, `ATC::Lang`, `ATC::Lang::Compiler`, `ATC::Lang::VM`, `ATC::Blockchain`, `ATC::Blockchain::Core`, `ATC::Consensus`, `ATC::Consensus::Shiva`, `ATC::Gateway`, `ATC::Gateway::API`, `ATC::UI`, `ATC::UI::Dashboard`, `ATC::Wallet`

ATC-Standard-Referenzen der Form `ATC::Hash::sha3(...)` lexieren als ATC_STD.

### 2.6 Kommentare

`#` bis Zeilenende (Token COMMENT, wird vom Parser uebersprungen).

## 3. Grammatik (EBNF, Quelle: frontend/parser/parser.py, 28 Produktionen)

### 3.1 Programm

```text
program    ::= module_decl? statement*
module_decl::= "module" IDENT
```text

### 3.2 Anweisungen

```text
block      ::= NEWLINE INDENT statement+ DEDENT
let_stmt   ::= ("let"|"const") IDENT (":" type)? ("=" expr)? (";"?)
if_stmt    ::= "if" expr block ("elif" expr block)* ("else" block)?
while_stmt ::= "while" expr block
for_stmt   ::= "for" IDENT "in" expr block
match_stmt ::= "match" expr NEWLINE INDENT case_clause+ DEDEND
case       ::= "case" pattern "=>" block
return     ::= "return" expr?
emit       ::= "emit" call_expr
require    ::= "require" "(" expr ("," STRING)? ")"
break      ::= "break" ; continue ::= "continue"
assignment ::= expr ("=" | "+=" | "-=" | "*=" | "/=") expr
expr_stmt  ::= expr ";"?
```text

**Normatives Desugar:** Compound-Zuweisung wird vom Parser desugart:
`x += y` → `Assignment(x, BinaryOp(x, "+", y))` (auch -=, *=, /=). Der AST
enthaelt KEINE Compound-Knoten.

### 3.3 Deklarationen

```text
struct   ::= "struct" IDENT block_field+
enum     ::= "enum" IDENT NEWLINE INDENT variant+ DEDEND
class   ::= "class" IDENT (":" IDENT)? block
contract ::= "contract" IDENT block_contract_body
function ::= "fn" IDENT "(" params ")" ("->" type)? block
```text

Contract-Koerper (AST: StorageBlock, StateField, EventDef, ErrorDef,
FunctionDef): Storage-/State-Deklarationen, Events, Errors und Funktionen.
Wallet-Deklarationen erzeugen WalletDef (parallele Struktur zu ContractDef).

### 3.4 Ausdruecke — Praezedenz (fallend)

| Stufe | Produktion | Operatoren |
|---|---|---|
| 1 (niedrigst) | parse_logical | `\|\|`, `&&` |
| 2 | parse_comparison | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| 3 | parse_addition | `+`, `-` |
| 4 | parse_multiplication | `*`, `/`, `%` |
| 5 | parse_unary | `!`, unäres `-` |
| 6 | parse_postfix | Call `(...)`, Index `[...]`, `.`-Zugriff, `::`-Zugriff, `?` |
| 7 (höchst) | parse_primary | Literale, Ident, `(expr)`, Match-Expr, Lambda, Range |

Grundformen (parse_primary): IntLiteral, FloatLiteral, StringLiteral,
BoolLiteral, NullLiteral, ListLiteral `[...]`, MapLiteral `{...}`, Match-Expr,
Lambda, Identifier, Klammerausdruck. Potenz `**`, Ranges `..`/`..=`, Slices und
Ternaries existieren als AST-Knoten (RangeExpr, SliceExpr, TernaryExpr).

## 4. AST-Referenz (50 Knoten, Quelle: frontend/parser/ast_nodes.py)

Basisklasse ASTNode (line, col). Knoten:

- ASTNode
- Assignment
- BinaryOp
- BoolLiteral
- BreakStatement
- CastExpr
- ClassDef
- ContinueStatement
- ContractDef
- DotAccess
- EmitStatement
- EnumDef
- ErrorDef
- EventDef
- ExprStatement
- FloatLiteral
- ForStatement
- FunctionCall
- FunctionDef
- Identifier
- IfStatement
- ImportStatement
- IndexAccess
- IntLiteral
- LambdaExpr
- LetStatement
- ListLiteral
- MapLiteral
- MatchStatement
- NamespaceAccess
- NullLiteral
- Parameter
- Program
- RangeExpr
- RequireStatement
- ReturnStatement
- SliceExpr
- StateField
- StorageBlock
- StringLiteral
- StructDef
- StructLiteral
- TernaryExpr
- TupleExpr
- TypeAliasDef
- TypeAnnotation
- UnaryOp
- WalletDef
- WhileStatement
- X

## 5. Semantik (Quelle: compiler/type_checker.py)

### 5.1 Scopes und Symboltabellen

SymbolTable mit `define_var`/`lookup_var`, `define_function`/`lookup_function`
und Scope-Kette (`child(...)`). Innere Scopes sehen ausseren; Shadowing erlaubt.

### 5.2 Pruefregeln (Check-Methoden)

- `_check_program`, `_check_stmt`, `_check_let`, `_check_return`, `_check_if`,
  `_check_for`, `_check_function`, `_check_contract` (+ check_and_report).
- `return` muss zum deklarierten Funktionstyp passen.
- `break`/`continue` nur in Loops (BreakOutsideLoopError/ContinueOutsideLoopError).

### 5.3 Built-in-Funktionen (Signaturtabelle aus type_checker)

| `print` | [T_ANY] | T_VOID |
| `len` | [T_ANY] | T_INT |
| `range` | [T_INT] | T_LIST |
| `sha256` | [T_ANY] | T_STRING |
| `int` | [T_ANY] | T_INT |
| `float` | [T_ANY] | T_FLOAT |
| `str` | [T_ANY] | T_STRING |
| `bool` | [T_ANY] | T_BOOL |
| `abs` | [T_INT] | T_INT |
| `min` | [T_INT, T_INT] | T_INT |
| `max` | [T_INT, T_INT] | T_INT |
| `push` | [T_LIST, T_ANY] | T_VOID |
| `pop` | [T_LIST] | T_ANY |

### 5.4 Standardbibliothek (9 Module)

| Modul | Klassen |
|---|---|
| stdlib/math.py | ATCMath |
| stdlib/collections.py | ATCCollections |
| stdlib/string.py | ATCString |
| stdlib/crypto.py | ATCCrypto |
| stdlib/chain.py | ATCChain |
| stdlib/encoding.py | ATCEncoding |
| stdlib/io.py | ATCIO |
| stdlib/primitives.py | ATCAddress, ATCHash, ATCSignature, ATCTransaktion, ATCBlockHeader, ATCPrimitives |
| stdlib/wallet.py | ATCWallet |

## 6. Fehlermodell (Quelle: compiler/errors.py, 45 Klassen)

CompileError-Hierarchie mit CompileErrorCode: ArgumentCountError, BreakOutsideLoopError, CompileBytecodeError, CompileContractError, CompileControlFlowError, CompileError, CompileErrorCode, CompileFunctionError, CompileInternalError, CompileNameError, CompileSyntaxError, CompileTypeError, CompilerDiagnostic, ConstantPoolError, ConstantPoolOverflowError, ContinueOutsideLoopError, DuplicateParameterError, DuplicateSymbolError, ErrorSeverity, InvalidASTError, InvalidBytecodeError, InvalidCallError, InvalidCastError, InvalidConstantError, InvalidContractError, InvalidErrorDefinitionError, InvalidEventError, InvalidFunctionError, InvalidGenericError, InvalidJumpError, InvalidOpcodeError, InvalidOperandError, InvalidOperationError, InvalidOptimizationError, InvalidReturnError, InvalidScopeError, InvalidStateError, InvalidStorageError, OptimizationError, SourceLocation, SourceSpan, TypeMismatchError, UndefinedSymbolError, UnknownTypeError, UnreachableCodeError

LexError (lexer.py) und Parse-Fehler tragen Zeile:Spalte.

## 7. Traceability

| Bereich | Quelldatei |
|---|---|
| Tokens, Keywords, Typen, Namespaces | src/atclang/frontend/lexer/lexer.py |
| EBNF, Praezedenz, Desugar | src/atclang/frontend/parser/parser.py |
| AST-Knoten | src/atclang/frontend/parser/ast_nodes.py |
| Scopes, Typ-Regeln, Builtins | src/atclang/compiler/type_checker.py |
| Fehlermodell | src/atclang/compiler/errors.py |
| Stdlib | src/atclang/stdlib/*.py |

## 8. G1-Kriterien — ERFUELLT

- [x] Token-Inventar vollstaendig (63 Tokens, 2.1)
- [x] Schluesselwoerter und Typ-Bezeichner vollstaendig (2.3, 2.4)
- [x] EBNF ueber alle 28 Parser-Produktionen, inkl. Desugar-Regeln (3.x)
- [x] AST-Referenz ueber 50 Knoten (4)
- [x] Semantik-Regeln und Builtins aus type_checker (5)
- [x] Fehlermodell vollstaendig (6)
- [x] Maschinenlesbares Extrakt registry.json fuer Conformance-/Differential-Tooling
