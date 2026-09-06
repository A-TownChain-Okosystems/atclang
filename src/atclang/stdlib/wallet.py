# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Stdlib — ATC::Wallet
Standard wallet operations accessible from ATCLang contracts.
Issue: #48 | Wiki: Kap. 36
"""
import hashlib
import secrets
import logging
from typing import Dict, Optional

logger = logging.getLogger("atclang.stdlib.wallet")

ATC_DECIMALS = 8
ATC_TOTAL_SUPPLY = 21_000_000 * (10 ** ATC_DECIMALS)


class ATCWallet:
    """
    ATC::Wallet — ATCLang standard library for wallet operations.
    Available in contracts as: ATC::Wallet.transfer(to, amount)
    """

    @staticmethod
    def transfer(balances: Dict[str, int], sender: str, recipient: str, amount: int) -> bool:
        """Transfer ATC tokens between addresses."""
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if balances.get(sender, 0) < amount:
            raise ValueError(f"Insufficient balance: {balances.get(sender,0)} < {amount}")
        balances[sender] = balances.get(sender, 0) - amount
        balances[recipient] = balances.get(recipient, 0) + amount
        logger.debug(f"Transfer {amount} ATC: {sender[:8]} -> {recipient[:8]}")
        return True

    @staticmethod
    def balance(balances: Dict[str, int], address: str) -> int:
        """Get balance of address in atoshi (1 ATC = 10^8 atoshi)."""
        return balances.get(address, 0)

    @staticmethod
    def mint(balances: Dict[str, int], address: str, amount: int) -> bool:
        """Mint new tokens (genesis only)."""
        if amount <= 0:
            raise ValueError("Mint amount must be positive")
        balances[address] = balances.get(address, 0) + amount
        return True

    @staticmethod
    def burn(balances: Dict[str, int], address: str, amount: int) -> bool:
        """Burn tokens (reduce supply)."""
        if balances.get(address, 0) < amount:
            raise ValueError("Insufficient balance to burn")
        balances[address] -= amount
        return True

    @staticmethod
    def generate_address(public_key: bytes) -> str:
        """Generate ATC address from public key (RIPEMD160(SHA256(pubkey)))."""
        sha = hashlib.sha256(public_key).digest()
        ripe = hashlib.new("ripemd160", sha).hexdigest()
        return f"ATC{ripe[:38]}"

    @staticmethod
    def format_atc(atoshi: int) -> str:
        """Format atoshi as human-readable ATC string."""
        atc = atoshi / (10 ** ATC_DECIMALS)
        return f"{atc:.8f} ATC"

    @staticmethod
    def parse_atc(atc_str: str) -> int:
        """Parse 'X.XXXXXXXX ATC' to atoshi integer."""
        val = float(atc_str.replace(" ATC", ""))
        return int(val * (10 ** ATC_DECIMALS))

    @staticmethod
    def is_valid_address(address: str) -> bool:
        return isinstance(address, str) and address.startswith("ATC") and len(address) == 41
