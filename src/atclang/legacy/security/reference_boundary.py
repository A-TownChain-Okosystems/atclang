"""Legacy fail-closed Python security reference boundary.

This module remains only for reference/test compatibility. Canonical
cryptographic/security implementations live in the Rust production boundary.
"""

from __future__ import annotations

from typing import NoReturn


class ReferenceBoundaryError(RuntimeError):
    """Raised when a legacy reference operation has no verified backend."""


def fail_closed(operation: str) -> NoReturn:
    raise ReferenceBoundaryError(
        f"legacy reference operation '{operation}' is unavailable: no verified canonical backend is bound"
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
