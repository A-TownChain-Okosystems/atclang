// ╔══════════════════════════════════════════════════════╗
// ║  ATC-8300 — Fungible Token Standard                ║
// ║  ATCLang v0.2.0 | Proprietär (kein ERC-20-Fork)   ║
// ╚══════════════════════════════════════════════════════╝

use ATC::Types::Address

contract ATC8300Token {
    state name_:        string
    state symbol_:      string
    state decimals_:    u8    = 18
    state total_supply_: u128 = 0
    state owner:        Address
    state balances:     Map<Address, u128>
    state allowances:   Map<Address, Map<Address, u128>>

    fn init(name: string, symbol: string, owner_addr: Address) {
        self.name_   = name
        self.symbol_ = symbol
        self.owner   = owner_addr
        emit TokenInitialized(name, symbol, owner_addr)
    }

    fn name()         -> string { return self.name_ }
    fn symbol()       -> string { return self.symbol_ }
    fn decimals()     -> u8     { return self.decimals_ }
    fn total_supply() -> u128   { return self.total_supply_ }

    fn balance_of(addr: Address) -> u128 {
        return self.balances[addr]
    }

    fn transfer(to: Address, amount: u128) -> bool {
        require(is_valid_address(to_string(to)), "Ungültige Adresse")
        require(amount > 0, "Betrag muss > 0 sein")
        require(self.balances[caller] >= amount, "Unzureichendes Guthaben")
        self.balances[caller] = safe_sub(self.balances[caller], amount)
        self.balances[to]     = safe_add(self.balances[to], amount)
        emit Transfer(caller, to, amount)
        return true
    }

    fn approve(spender: Address, amount: u128) -> bool {
        self.allowances[caller][spender] = amount
        emit Approval(caller, spender, amount)
        return true
    }

    fn allowance(owner_: Address, spender: Address) -> u128 {
        return self.allowances[owner_][spender]
    }

    fn transfer_from(from_: Address, to: Address, amount: u128) -> bool {
        require(self.allowances[from_][caller] >= amount, "Nicht genehmigt")
        require(self.balances[from_] >= amount, "Unzureichendes Guthaben")
        self.allowances[from_][caller] = safe_sub(self.allowances[from_][caller], amount)
        self.balances[from_] = safe_sub(self.balances[from_], amount)
        self.balances[to]    = safe_add(self.balances[to], amount)
        emit Transfer(from_, to, amount)
        return true
    }

    fn mint(to: Address, amount: u128) -> bool {
        require(caller == self.owner, "Nur Owner kann minten")
        require(amount > 0, "Betrag muss > 0 sein")
        self.balances[to]    = safe_add(self.balances[to], amount)
        self.total_supply_   = safe_add(self.total_supply_, amount)
        emit Mint(to, amount)
        return true
    }

    fn burn(amount: u128) -> bool {
        require(self.balances[caller] >= amount, "Unzureichendes Guthaben")
        self.balances[caller] = safe_sub(self.balances[caller], amount)
        self.total_supply_    = safe_sub(self.total_supply_, amount)
        emit Burn(caller, amount)
        return true
    }
}

// ATC-Coin — nativer Token
contract ATCoin : ATC8300Token {
    state CHAIN_ID:  u64  = 9000
    state MAX_SUPPLY: u128 = 21_000_000_000_000_000_000_000_000  // 21 Mio ATC

    fn init_atcoin(owner_addr: Address) {
        self.init("A-TownCoin", "ATC", owner_addr)
        emit ATCoinInitialized(owner_addr, self.MAX_SUPPLY)
    }

    fn mint(to: Address, amount: u128) -> bool {
        require(safe_add(self.total_supply_, amount) <= self.MAX_SUPPLY, "Max Supply erreicht")
        return super.mint(to, amount)
    }
}
