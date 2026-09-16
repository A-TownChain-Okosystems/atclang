"""Fail-closed security boundary for non-canonical ATCLang reference operations.

The Python reference runtime is never a source of consensus/security truth.
Operations that would otherwise require canonical cryptography, identity,
network transport, RPC, or wallet conformance MUST fail closed until they are
bound to a verified implementation.
"""

from __future__ import annotations

from typing import NoReturn


class ReferenceBoundaryError(RuntimeError):
    """Raised when a reference-only security operation has no verified backend."""


def fail_closed(operation: str) -> NoReturn:
    """Reject an operation rather than returning simulated success."""
    raise ReferenceBoundaryError(
        f"reference operation '{operation}' is unavailable: no verified canonical backend is bound"
    )


def ecdsa_sign(*_args: object, **_kwargs: object) -> NoReturn:
    fail_closed("ATC::Crypto::ECDSA::sign")


def ecdsa_verify(*_args: object, **_kwargs: object) -> NoReturn:
    fail_closed("ATC::Crypto::ECDSA::verify")


def verify_jwt(*_args: object, **_kwargs: object) -> NoReturn:
    fail_closed("ATC::Crypto::verify_jwt")


def net_send(*_args: object, **_kwargs: object) -> NoReturn:
    fail_closed("ATC::Net::send")


def rpc_call(*_args: object, **_kwargs: object) -> NoReturn:
    fail_closed("ATC::RPC::call")


def wallet_operation(operation: str, *_args: object, **_kwargs: object) -> NoReturn:
    fail_closed(f"ATC::Wallet::{operation}")
