# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""
ATCLang Stdlib — ATC::Math
Safe integer arithmetic for smart contracts.
Issue: #48 | Wiki: Kap. 36
"""
import math as _math
from typing import Union

Num = Union[int, float]


class ATCMath:
    """
    ATC::Math — Safe arithmetic for ATCLang contracts.
    All operations check for overflow and division-by-zero.
    """
    MAX_U64 = (1 << 64) - 1
    MAX_U32 = (1 << 32) - 1

    @staticmethod
    def add(a: int, b: int) -> int:
        result = a + b
        if result > ATCMath.MAX_U64:
            raise OverflowError(f"add overflow: {a} + {b}")
        return result

    @staticmethod
    def sub(a: int, b: int) -> int:
        if b > a:
            raise ArithmeticError(f"sub underflow: {a} - {b}")
        return a - b

    @staticmethod
    def mul(a: int, b: int) -> int:
        result = a * b
        if result > ATCMath.MAX_U64:
            raise OverflowError(f"mul overflow: {a} * {b}")
        return result

    @staticmethod
    def div(a: int, b: int) -> int:
        if b == 0:
            raise ZeroDivisionError("ATC::Math.div by zero")
        return a // b

    @staticmethod
    def mod(a: int, b: int) -> int:
        if b == 0:
            raise ZeroDivisionError("ATC::Math.mod by zero")
        return a % b

    @staticmethod
    def pow(base: int, exp: int) -> int:
        result = base ** exp
        if result > ATCMath.MAX_U64:
            raise OverflowError(f"pow overflow: {base}^{exp}")
        return result

    @staticmethod
    def sqrt(x: int) -> int:
        if x < 0:
            raise ValueError("sqrt of negative")
        return int(_math.isqrt(x))

    @staticmethod
    def min(a: int, b: int) -> int:
        return a if a < b else b

    @staticmethod
    def max(a: int, b: int) -> int:
        return a if a > b else b

    @staticmethod
    def clamp(value: int, lo: int, hi: int) -> int:
        return ATCMath.max(lo, ATCMath.min(value, hi))

    @staticmethod
    def percentage(amount: int, bps: int) -> int:
        """Calculate percentage using basis points (100 bps = 1%)."""
        return ATCMath.div(ATCMath.mul(amount, bps), 10000)

    @staticmethod
    def is_power_of_two(n: int) -> bool:
        return n > 0 and (n & (n - 1)) == 0
    # ── Safe Aliases (ATC-94 Spec) ──────────────

    @staticmethod
    def safe_add(a: int, b: int) -> int:
        """Safe addition with overflow check. Gas: 3"""
        return ATCMath.add(a, b)

    @staticmethod
    def safe_sub(a: int, b: int) -> int:
        """Safe subtraction with underflow check. Gas: 3"""
        return ATCMath.sub(a, b)

    @staticmethod
    def safe_mul(a: int, b: int) -> int:
        """Safe multiplication with overflow check. Gas: 5"""
        return ATCMath.mul(a, b)

    @staticmethod
    def safe_div(a: int, b: int) -> int:
        """Safe division with zero check. Gas: 5"""
        return ATCMath.div(a, b)

    @staticmethod
    def safe_mod(a: int, b: int) -> int:
        """Safe modulo with zero check. Gas: 5"""
        return ATCMath.mod(a, b)

    @staticmethod
    def mod_exp(base: int, exp: int, mod: int) -> int:
        """Modular exponentiation. Gas: 50"""
        if mod == 0:
            raise ZeroDivisionError("mod_exp: mod is zero")
        return pow(base, exp, mod)

    @staticmethod
    def abs(x: int) -> int:
        """Absolute value. Gas: 2"""
        return abs(x)

    @staticmethod
    def gcd(a: int, b: int) -> int:
        """Greatest common divisor. Gas: 20"""
        while b:
            a, b = b, a % b
        return abs(a)

    @staticmethod
    def lcm(a: int, b: int) -> int:
        """Least common multiple. Gas: 30"""
        if a == 0 or b == 0:
            return 0
        return abs(a * b) // ATCMath.gcd(a, b)

