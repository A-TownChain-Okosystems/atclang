import pytest

from atclang.security.reference_boundary import (
    ReferenceBoundaryError,
    ecdsa_sign,
    ecdsa_verify,
    net_send,
    rpc_call,
    verify_jwt,
    wallet_operation,
)


@pytest.mark.parametrize(
    "operation",
    [
        lambda: ecdsa_sign(b"data", b"key"),
        lambda: ecdsa_verify(b"data", "sig", b"pub"),
        lambda: verify_jwt("eyJ.invalid.token"),
        lambda: net_send("127.0.0.1", 1, b"data"),
        lambda: rpc_call("handler", {}),
        lambda: wallet_operation("to_mnemonic", b"seed"),
    ],
)
def test_reference_security_operations_fail_closed(operation):
    with pytest.raises(ReferenceBoundaryError):
        operation()
