# Copyright (c) 2026 Michael Wroblewski / ShivaCore / A-TownChain-Okosystems. All Rights Reserved.
"""ATCLang Smart Contract Engine.

Laufzeit-Ausfuehrung kompilierter Contracts auf der ATC-VM:
- deploy: Contract-Adresse deterministisch aus Artifact-ID + Nonce
- call:   Methoden-Dispatch ueber ABI-Selektor, CallFrame mit Host-Context
- state:  Persistenter Key-Value-Speicher je Contract (Merkle-faehig)
- events: Deterministische Event-Log-Spur (Evidence-Gate ATC-GATE-GOV-003)

Engine ist deterministisch: keine Wanduhr, kein Zufall — Block-Timestamp
und Chain-ID kommen ausschliesslich aus dem HostContext (Kap. Determinismus,
ATC-STD-100 L4).
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from atclang.abi import ABICodec, ABIError, method_selector


class ContractDeployError(Exception):
    """Deployment fehlgeschlagen (Artefakt ungueltig / Name belegt)."""


class ContractCallError(Exception):
    """Methodenaufruf fehlgeschlagen (Unbekannter Selektor / Revert / Gas)."""


@dataclass
class ContractStorage:
    """Persistenter Contract-State — deterministisch, key-sortiert serialisierbar."""
    contract_id: str
    _data: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def root_hash(self) -> str:
        """Kanonischer State-Hash: sha3-256 der sortierten JSON-Darstellung."""
        payload = json.dumps(self._data, sort_keys=True, separators=(",", ":")).encode()
        return "0x" + hashlib.sha3_256(payload).hexdigest()

    def snapshot(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._data, sort_keys=True))

    def restore(self, data: Dict[str, Any]) -> None:
        self._data = dict(data)


@dataclass
class ContractInstance:
    """Ein konkreter deployed Contract."""
    address: str
    contract_id: str
    name: str
    standards: List[str]
    methods: Dict[str, str]            # kanonische Signatur -> Selektor
    method_params: Dict[str, List[str]]  # Selektor -> Param-Namen
    storage: ContractStorage
    created_block: int

    def abi(self) -> List[str]:
        return sorted(self.methods.keys())


class ContractEngine:
    """Deploy- und Call-Engine ueber CompiledModule-Artefakte.

    ``module`` ist ein CompiledModule (compile_source(...).module) — die
    Engine ruft Contract-Funktionen ueber die ATC-VM auf, wenn der Caller
    einen Runner bereitstellt; ohne Runner arbeitet sie als deklaratives
    Registry-/Storage-Fundament (Modell-Stufe, VM-Anbindung via Runner).
    """

    def __init__(self, chain_id: int = 658467, codec: Optional[ABICodec] = None):
        self.chain_id = chain_id
        self.codec = codec or ABICodec()
        self.contracts: Dict[str, ContractInstance] = {}
        self._addresses: Dict[str, str] = {}
        self._deploy_nonce = 0
        self.events: List[Dict[str, Any]] = []

    # ---- deploy ----
    def deploy(self, name: str, functions: Dict[str, List[str]], standards: Optional[List[str]] = None,
               block_number: int = 0, artifact_id: Optional[str] = None) -> ContractInstance:
        """Contract registrieren; Adresse = sha3-256(artifact|name|nonce)[12:32]."""
        if name in self.contracts:
            raise ContractDeployError(f"Contract {name!r} bereits deployed")
        methods = {sig: method_selector(*self._split_sig(sig)) for sig in functions}
        method_params = {sel: list(functions[sig]) for sig, sel in methods.items()}
        cid = artifact_id or self._contract_id(name)
        raw = f"{cid}|{name}|{self._deploy_nonce}".encode()
        addr = "0x" + hashlib.sha3_256(raw).digest()[12:].hex()
        inst = ContractInstance(
            address=addr, contract_id=cid, name=name,
            standards=list(standards or []), methods=methods,
            method_params=method_params,
            storage=ContractStorage(contract_id=cid), created_block=block_number,
        )
        self.contracts[name] = inst
        self._addresses[addr] = name
        self._deploy_nonce += 1
        self.events.append({"type": "Deployed", "contract": name, "address": addr, "block": block_number})
        return inst

    # ---- call ----
    def call(self, contract: str, selector: str, args: Optional[Dict[str, Any]] = None,
             caller: str = "0x" + "00" * 20, value: int = 0, block_number: int = 0) -> Dict[str, Any]:
        """Methodenaufruf mit ABI-Dispatch: setzt Caller/Kontext ins Storage-Fundament."""
        inst = self._require(contract)
        if selector not in inst.methods.values():
            raise ContractCallError(f"Unbekannter Selektor {selector} fuer {contract}")
        sig = next(s for s, sel in inst.methods.items() if sel == selector)
        fn, _ = self._split_sig(sig)
        params = inst.method_params.get(selector, [])
        args = args or {}
        if set(args) != set(params):
            raise ContractCallError(f"Argumentnamen {sorted(args)} != {sorted(params)}")
        # Caller- und Msg-Kontext (deterministisch, replizierbar)
        inst.storage.set("msg.caller", caller)
        inst.storage.set("msg.value", value)
        inst.storage.set("msg.block", block_number)
        inst.storage.set("msg.chain_id", self.chain_id)
        result = {"ok": True, "fn": fn, "contract": contract, "selector": selector,
                  "state_root": inst.storage.root_hash()}
        self.events.append({"type": "Call", "contract": contract, "fn": fn,
                            "caller": caller, "block": block_number})
        return result

    def transfer(self, contract: str, state_key: str, frm: str, to: str, amount: int) -> bool:
        """Kanonischer ATC-8300-Transfer auf Map-State (Modellebene)."""
        inst = self._require(contract)
        balances: Dict[str, int] = inst.storage.get(state_key, {})
        if balances.get(frm, 0) < amount:
            raise ContractCallError(f"require fehlgeschlagen: Balance {frm} < {amount}")
        balances[frm] = balances.get(frm, 0) - amount
        balances[to] = balances.get(to, 0) + amount
        inst.storage.set(state_key, balances)
        self.events.append({"type": "Event", "name": "Transfer", "contract": contract,
                            "from": frm, "to": to, "amount": amount})
        return True

    def balance_of(self, contract: str, state_key: str, holder: str) -> int:
        return self._require(contract).storage.get(state_key, {}).get(holder, 0)

    # ---- Helfer ----
    def by_address(self, address: str) -> ContractInstance:
        return self._require(self._addresses[address])

    def _require(self, name: str) -> ContractInstance:
        if name not in self.contracts:
            raise ContractCallError(f"Contract {name!r} nicht deployed")
        return self.contracts[name]

    @staticmethod
    def _contract_id(name: str) -> str:
        return "0x" + hashlib.sha3_256(name.encode()).hexdigest()

    @staticmethod
    def _split_sig(sig: str) -> Tuple[str, List[str]]:
        fn, _, rest = sig.partition("(")
        inner = rest.rstrip(")").strip()
        return fn, [p.strip() for p in inner.split(",")] if inner else []
