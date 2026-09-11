# Tests fuer die SCR-0098-Module: ABI-Codec, Contract-Engine, Artifact, Host, Security, Profiles, Package, IR
import json
import pytest

from atclang.abi import ABICodec, method_selector, canonical_signature, ABIError
from atclang.contracts import ContractEngine, ContractCallError
from atclang.artifact import CompiledArtifact, ArtifactError
from atclang.host import HostContext, HostPolicy
from atclang.security import SecurityGate, Severity
from atclang.profiles import get_profile
from atclang.package import PackageManifest, PackageError
from atclang.ir import to_json_ir, ir_hash, validate_ir


# ---- ABI ----
def test_abi_selector_deterministic():
    assert method_selector("transfer", ["Address", "UInt256"]) == method_selector("transfer", ["Address", "UInt256"])
    assert canonical_signature("transfer", ["Address", "UInt256"]) == "transfer(Address,UInt256)"

def test_abi_roundtrip_all_types():
    c = ABICodec()
    cases = [(123, "UInt256"), (5, "UInt8"), (7, "UInt64"), (-9, "Int256"),
             (True, "Bool"), ("0x" + "ab" * 20, "Address"), ("hallo", "String"),
             ([1, 2, 3], "Vec[UInt256]")]
    for val, t in cases:
        enc = c.encode(val, t)
        dec, off = c.decode(enc, t)
        assert dec == val and off == len(enc), f"roundtrip fail: {t}"

def test_abi_uint_overflow_rejected():
    with pytest.raises(ABIError):
        ABICodec().encode(2 ** 8, "UInt8")

def test_abi_encode_call_selector_prefix():
    c = ABICodec()
    sel = method_selector("transfer", ["Address", "UInt256"])
    payload = c.encode_call(sel, ["0x" + "00" * 20, 42], ["Address", "UInt256"])
    assert payload[:4].hex() == sel[2:]


# ---- Contract Engine ----
def test_engine_deploy_and_call():
    e = ContractEngine()
    inst = e.deploy("Token", {"transfer(Address,UInt256)": ["to", "amount"]}, standards=["ATC-8300"])
    assert inst.address.startswith("0x")
    sel = inst.methods["transfer(Address,UInt256)"]
    res = e.call("Token", sel, {"to": "0xb", "amount": 5}, caller="0xa")
    assert res["ok"] and res["fn"] == "transfer"

def test_engine_unknown_selector_fails():
    e = ContractEngine()
    e.deploy("Token", {"transfer(Address,UInt256)": ["to", "amount"]})
    with pytest.raises(ContractCallError):
        e.call("Token", "0xdeadbeef", {})

def test_engine_transfer_and_balances():
    e = ContractEngine()
    inst = e.deploy("Token", {"transfer(Address,UInt256)": ["to", "amount"]})
    inst.storage.set("balance", {"0xa": 500})          # Mint via State-Setup
    assert e.transfer("Token", "balance", "0xa", "0xb", 100) is True
    assert e.balance_of("Token", "balance", "0xb") == 100
    assert e.balance_of("Token", "balance", "0xa") == 400
    with pytest.raises(ContractCallError):              # require: 400 < 1000
        e.transfer("Token", "balance", "0xa", "0xc", 1000)

def test_engine_deploy_twice_fails():
    e = ContractEngine()
    e.deploy("Token", {})
    with pytest.raises(Exception):
        e.deploy("Token", {})

def test_engine_deterministic_addresses():
    a, b = ContractEngine(), ContractEngine()
    i1 = a.deploy("Token", {})
    i2 = b.deploy("Token", {})
    assert i1.address == i2.address  # gleicher Name/Nonce => gleiche Adresse


# ---- Artifact ----
def _artifact(**over):
    kw = dict(name="t", entry="m.atc", compiler_version="1.0.0",
              language_standard="ATC-92 v1.0.0", profile="consensus",
              source_sha256="0x" + "ab" * 32, bytecode={"s": []}, abi=[], contract_standards=[])
    kw.update(over)
    return CompiledArtifact(**kw)

def test_artifact_roundtrip_and_id_stability():
    art = _artifact()
    a2 = CompiledArtifact.from_bytes(art.to_bytes())
    assert a2.artifact_id == art.artifact_id
    assert _artifact().artifact_id == art.artifact_id  # reproduzierbar

def test_artifact_tamper_detected():
    art = _artifact()
    raw = bytearray(art.to_bytes())
    raw[-1] ^= 0xFF
    with pytest.raises(ArtifactError):
        CompiledArtifact.from_bytes(bytes(raw))


# ---- Host ----
def test_host_deterministic_time():
    ctx = HostContext.for_block(658467, 42, 1757600000, "0x" + "11" * 32)
    assert ctx.now() == 1757600000
    ctx2 = HostContext.for_block(658467, 42, 1757600000, "0x" + "11" * 32)
    assert ctx.now() == ctx2.now()

def test_host_gas_limit_enforced():
    ctx = HostContext(gas_limit=10)
    used = ctx.gas_consume(5, 0)
    with pytest.raises(RuntimeError):
        ctx.gas_consume(6, used)


# ---- Security Gate ----
def test_gate_blocks_nondeterminism_in_consensus():
    g = SecurityGate()
    src = 'fn f(x: UInt256) -> Bool { let t = time.time() return true }'
    assert not g.check(src, "consensus")
    assert g.check(src, "off_chain")

def test_gate_blocks_random():
    g = SecurityGate()
    assert not g.check("fn g() -> UInt256 { return random.randint(0, 9) }", "consensus")

def test_gate_allows_clean_code():
    g = SecurityGate()
    assert g.check("fn add(a: UInt256, b: UInt256) -> UInt256 { return a + b }", "consensus")

def test_gate_unsafe_without_require():
    g = SecurityGate()
    src = "fn unsafe_move(a: UInt256) -> Bool { return true }"
    findings = g.analyse(src, "consensus")
    assert any(f.rule == "SEC-004" for f in findings)


# ---- Profiles ----
def test_profiles_registry():
    assert get_profile("consensus").deterministic
    assert not get_profile("debug").deterministic
    with pytest.raises(KeyError):
        get_profile("quantum")


# ---- Package ----
def test_manifest_valid_and_invalid():
    PackageManifest(name="tok", version="1.2.3",
                    license="SPDX-License-Identifier: Apache-2.0", entry="main.atc").validate()
    with pytest.raises(PackageError):
        PackageManifest(name="BadName!", version="1.2.3",
                       license="SPDX-License-Identifier: MIT", entry="m.atc").validate()
    with pytest.raises(PackageError):
        PackageManifest(name="tok", version="1.2", license="SPDX-License-Identifier: MIT",
                        entry="m.atc").validate()


# ---- IR ----
def test_ir_hash_stable():
    class Fake:  # mini AST-Dummy
        pass
    n = Fake()
    n.value = 7
    n.body = [Fake()]
    n.body[0].value = 1
    assert ir_hash(to_json_ir(n)) == ir_hash(to_json_ir(n))
    validate_ir(to_json_ir(n))
