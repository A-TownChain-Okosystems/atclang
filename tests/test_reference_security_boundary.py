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
from atclang.vm.atcvm import ATCStdlib, ATCVM, Instruction, OP


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


def test_vm_dispatch_uses_fail_closed_security_boundary():
    with pytest.raises(ReferenceBoundaryError):
        ATCStdlib.ecdsa_sign(b"data", b"key")

    vm = ATCVM()
    vm.push(b"data")
    vm.push(b"key")
    with pytest.raises(ReferenceBoundaryError):
        vm.execute([Instruction(OP.CRYPTO_SIGN)])

    with pytest.raises(ReferenceBoundaryError):
        vm.execute(
            [Instruction(OP.PUSH, ["token"]), Instruction(OP.CALL_EXT, ["ATC::Crypto::verify_jwt", 1])]
        )

    with pytest.raises(ReferenceBoundaryError):
        vm.execute(
            [Instruction(OP.PUSH, ["127.0.0.1"]), Instruction(OP.PUSH, [1]), Instruction(OP.PUSH, [b"data"]), Instruction(OP.NET_SEND)]
        )
