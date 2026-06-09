# ATCLang — Die Programmiersprache des A-TownChain Ökosystems
Version: 0.1.0-alpha
Datum: 2026-06-06

## Philosophie
ATCLang ist eine statisch typisierte, blockchain-native Sprache.
Keine Abhängigkeit von Python-Syntax. Eigene Grammatik. Eigene VM.

## Syntax-Beispiel

```atclang
// Wallet erstellen
wallet myWallet = ATC::Wallet::new("ShivaCore")
contract ShivaToken : ATC-8300 {
    state balance: Map<Address, UInt256>
    fn transfer(to: Address, amount: UInt256) -> Bool {
        require(balance[caller] >= amount)
        balance[caller] -= amount
        balance[to] += amount
        emit Transfer(caller, to, amount)
        return true
    }
}
```

## Token-Typen
- KEYWORD: wallet, contract, fn, state, emit, require, return
- TYPE: UInt256, Address, Bool, String, Map, List
- OPERATOR: +, -, *, /, >=, <=, ==, !=, ->, ::
- LITERAL: Integer, String, Bool
- SPECIAL: ATC:: (Namespace), @decorator
