"""Regression tests for the deterministic execution boundary."""

import pytest

from atclang.host import HostContext
from atclang.stdlib.chain import ATCChain
from atclang.stdlib.primitives import ATCBlockHeader, ATCTransaction


def test_host_context_uses_only_block_timestamp():
    ctx = HostContext.for_block(
        chain_id=658467,
        block_number=42,
        block_timestamp=1_757_600_000,
        block_hash="0x" + "11" * 32,
    )
    assert ctx.now() == 1_757_600_000


def test_host_context_has_no_wall_clock_capability():
    assert not hasattr(HostContext, "allow_wall_clock")
    ctx = HostContext.for_block(658467, 1, 100, "0x" + "22" * 32)
    assert ctx.now() == 100


def test_chain_timestamp_requires_authenticated_state():
    with pytest.raises(RuntimeError, match="block_timestamp"):
        _ = ATCChain({}).block_timestamp

    chain = ATCChain({"block_timestamp": 1234, "block_number": 7})
    assert chain.block_timestamp == 1234


def test_transaction_timestamp_is_explicit_and_reproducible():
    a = ATCTransaction("ATC" + "1" * 32, "ATC" + "2" * 32, 10, timestamp=500)
    b = ATCTransaction("ATC" + "1" * 32, "ATC" + "2" * 32, 10, timestamp=500)
    assert a.timestamp == b.timestamp == 500
    assert a.compute_hash() == b.compute_hash()


def test_block_header_timestamp_is_explicit_and_reproducible():
    a = ATCBlockHeader(5, "0x" + "0" * 64, "0x" + "1" * 64, timestamp=900)
    b = ATCBlockHeader(5, "0x" + "0" * 64, "0x" + "1" * 64, timestamp=900)
    assert a.compute_hash() == b.compute_hash()
