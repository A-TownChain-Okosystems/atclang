# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""ATCLang Standard Library — ATC-94

6 Module:
  crypto      — SHA-256, ECDSA, Base58/64, Hex
  collections — Map, Array, Set, Queue, Stack
  io          — Console, File, Network (context-isoliert)
  math        — BigInt, Modular Arithmetic, Standard Math
  encoding    — JSON, CBOR, Hex (RLP/SCALE deprecated)
  primitives  — Address, Hash, Signature, Tx, BlockHeader

+ Extended:
  wallet      — ATC::Wallet operations
  chain       — ATC::Chain state access
  string      — ATC::String operations
"""
from .crypto import ATCCrypto
from .collections import ATCCollections
from .io import ATCIO
from .math import ATCMath
from .encoding import ATCEncoding
from .primitives import ATCPrimitives, ATCAddress, ATCHash, ATCSignature, ATCTransaction, ATCBlockHeader
from .wallet import ATCWallet
from .chain import ATCChain
from .string import ATCString

__all__ = [
    "ATCCrypto", "ATCCollections", "ATCIO", "ATCMath", "ATCEncoding",
    "ATCPrimitives", "ATCAddress", "ATCHash", "ATCSignature",
    "ATCTransaction", "ATCBlockHeader",
    "ATCWallet", "ATCChain", "ATCString",
]
