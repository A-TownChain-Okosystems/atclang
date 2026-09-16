from atclang.security.static_analysis import SecurityGate
from atclang.stdlib.chain import ATCChain


def test_consensus_rejects_wall_clock_and_randomness():
    source = """
import time
import random
fn run() {
    time.time()
    random.randint(0, 1)
}
"""
    findings = SecurityGate().analyse(source, "consensus")
    rules = {finding.rule for finding in findings}
    assert "SEC-001" in rules
    assert "SEC-002" in rules
    assert not SecurityGate().check(source, "consensus")


def test_chain_timestamp_is_host_supplied_and_deterministic():
    first = ATCChain({"block_timestamp": 123, "block_number": 7})
    second = ATCChain({"block_timestamp": 123, "block_number": 7})
    assert first.block_timestamp == second.block_timestamp == 123
    first.emit("Transfer", amount=1)
    assert first.events == [{"event": "Transfer", "block": 7, "args": {"amount": 1}}]
