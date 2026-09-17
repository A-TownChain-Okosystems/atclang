"""Compatibility shim for the relocated legacy security reference boundary.

The implementation lives exclusively under ``atclang.legacy.security``.
This module exists only to preserve compatibility for existing reference-VM
imports while callers migrate to the explicit legacy namespace.
"""

from atclang.legacy.security.reference_boundary import (
    ReferenceBoundaryError,
    ecdsa_sign,
    ecdsa_verify,
    fail_closed,
    net_send,
    rpc_call,
    verify_jwt,
    wallet_operation,
)

__all__ = [
    "ReferenceBoundaryError",
    "ecdsa_sign",
    "ecdsa_verify",
    "fail_closed",
    "net_send",
    "rpc_call",
    "verify_jwt",
    "wallet_operation",
]
