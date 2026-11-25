"""Observation of anchor facts on Ethereum (run by the authors in Colab with their own Etherscan key) and the
classification of those observations (run here, from the committed raw file).

Observed per token (no interpretation in the notebook):
  verified source of the token and, for a proxy, of its implementation (saved verbatim)
  EIP-1967 admin and implementation slots, owner(), defaultAdmin()
  for each controlling address, recursively one hop: code present (contract or EOA), nonce (eth_getTransactionCount),
  Safe getThreshold() / getOwners() (all owners), timelock getMinDelay()
  AccessControlEnumerable role members for the role constants exposed by the ABI (getRoleMemberCount / getRoleMember)

Classified here (``facts_from_raw``):
  key_exposed for an EOA        nonce > 0: a sent transaction reveals the public key (ECDSA public-key recovery)
  key_exposed for a Safe        at least `threshold` owners are EOAs with nonce > 0
  otherwise                     None (not observed)
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Callable

ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
SEL = dict(owner="0x8da5cb5b", default_admin="0x84ef8ffc", threshold="0xe75235b8", owners="0xa0e67e2b",
           min_delay="0xf27a0c92", role_member_count="0xca15c873", role_member="0x9010d07c")
ZERO = "0x" + "0" * 40


def selector(signature: str, keccak: Callable[[bytes], bytes]) -> str:
    return "0x" + keccak(signature.encode()).hex()[:8]


def word_to_address(word: str | None) -> str | None:
    if not word or word in ("0x", "0x0"):
        return None
    h = word[2:] if word.startswith("0x") else word
    if len(h) < 40:
        return None
    a = "0x" + h[-40:].lower()
    return None if a == ZERO else a


def word_to_int(word: str | None) -> int | None:
    if not word or word == "0x":
        return None
    try:
        return int(word, 16)
    except ValueError:
        return None


def decode_address_array(data: str | None) -> list[str] | None:
    """ABI-decode a returned dynamic address[] (offset, length, items)."""
    if not data or len(data) < 2 + 128:
        return None
    h = data[2:]
    words = [h[i:i + 64] for i in range(0, len(h), 64)]
    try:
        off = int(words[0], 16) // 32
        n = int(words[off], 16)
        return ["0x" + w[-40:].lower() for w in words[off + 1: off + 1 + n]]
    except (ValueError, IndexError):
        return None


class Observer:
    """Etherscan V2 proxy and contract module reader. ``get_json(url)`` is injected (requests in Colab, a fake in
    tests). Errors are recorded, never raised for one contract."""

    BASE = "https://api.etherscan.io/v2/api"

    def __init__(self, get_json, key: str, pause: float = 0.25, chainid: int = 1):
        self.get_json, self.key, self.pause, self.chainid = get_json, key, pause, chainid
        self.errors: list[str] = []
        self.calls = 0

    def _q(self, params: dict, what: str, soft: bool = False):
        time.sleep(self.pause)
        self.calls += 1
        q = "&".join(f"{k}={v}" for k, v in {"chainid": self.chainid, **params}.items())
        try:
            d = self.get_json(f"{self.BASE}?{q}&apikey={self.key}")
        except Exception as e:  # noqa: BLE001
            if not soft:
                self.errors.append(f"{what}: {type(e).__name__}")
            return None
        if isinstance(d, dict) and "error" in d:
            if not soft:
                self.errors.append(f"{what}: {str(d['error'])[:80]}")
            return None
        if isinstance(d, dict) and d.get("status") == "0" and not isinstance(d.get("result"), (list, dict)):
            if not soft:
                self.errors.append(f"{what}: {str(d.get('message'))[:40]}")
            return None
        return d.get("result") if isinstance(d, dict) else None

    def call(self, to: str, data: str, what: str):
        r = self._q(dict(module="proxy", action="eth_call", to=to, data=data, tag="latest"), what, soft=True)
        return r if isinstance(r, str) and r not in ("0x",) else None

    def code(self, a: str):
        return self._q(dict(module="proxy", action="eth_getCode", address=a, tag="latest"), f"getCode {a}")

    def nonce(self, a: str):
        return word_to_int(self._q(dict(module="proxy", action="eth_getTransactionCount", address=a, tag="latest"), f"nonce {a}"))

    def slot(self, a: str, s: str):
        return self._q(dict(module="proxy", action="eth_getStorageAt", address=a, position=s, tag="latest"), f"slot {a}")

    def source(self, a: str):
        r = self._q(dict(module="contract", action="getsourcecode", address=a), f"source {a}")
        return r[0] if isinstance(r, list) and r else None

    def block(self):
        return word_to_int(self._q(dict(module="proxy", action="eth_blockNumber"), "blockNumber"))

    # ---------------------------------------------------------------- observations
    def observe_address(self, a: str, hops: int = 1) -> dict:
        code = self.code(a)
        is_contract = None if code is None else (code not in ("0x", "0x0"))
        rec = dict(address=a, is_contract=is_contract)
        if is_contract is False:
            rec["nonce"] = self.nonce(a)
            return rec
        if not is_contract:
            return rec
        rec["threshold"] = word_to_int(self.call(a, SEL["threshold"], "threshold"))
        rec["owners"] = decode_address_array(self.call(a, SEL["owners"], "owners"))
        rec["min_delay"] = word_to_int(self.call(a, SEL["min_delay"], "minDelay"))
        rec["owner"] = word_to_address(self.call(a, SEL["owner"], "owner"))
        if hops > 0:
            subs = list(rec["owners"] or []) + ([rec["owner"]] if rec["owner"] else [])
            rec["sub"] = {s: self.observe_address(s, hops - 1) for s in subs[:20]}
        return rec

    def observe_token(self, address: str, role_selectors: dict[str, str]) -> dict:
        self.errors = []
        src = self.source(address) or {}
        rec = dict(address=address, contract_name=src.get("ContractName"), source=src.get("SourceCode"),
                   is_proxy=str(src.get("Proxy")) == "1", implementation=(src.get("Implementation") or "").lower() or None)
        if rec["is_proxy"] and rec["implementation"]:
            isrc = self.source(rec["implementation"]) or {}
            rec["implementation_source"] = isrc.get("SourceCode")
            rec["implementation_name"] = isrc.get("ContractName")
        rec["admin_slot"] = word_to_address(self.slot(address, ADMIN_SLOT))
        rec["impl_slot"] = word_to_address(self.slot(address, IMPL_SLOT))
        rec["owner"] = word_to_address(self.call(address, SEL["owner"], "owner"))
        rec["default_admin"] = word_to_address(self.call(address, SEL["default_admin"], "defaultAdmin"))
        roles = {}
        for name, sel in role_selectors.items():
            rid = self.call(address, sel, f"role {name}")
            if not rid:
                continue
            rid = "0x" + rid[2:].rjust(64, "0")[-64:]
            cnt = word_to_int(self.call(address, SEL["role_member_count"] + rid[2:], f"count {name}"))
            members = []
            for i in range(min(cnt or 0, 10)):
                m = word_to_address(self.call(address, SEL["role_member"] + rid[2:] + hex(i)[2:].rjust(64, "0"), f"member {name}"))
                if m:
                    members.append(m)
            roles[name] = dict(role_id=rid, count=cnt, members=members)
        rec["roles"] = roles
        ctrl = {x for x in (rec["admin_slot"], rec["owner"], rec["default_admin"]) if x}
        for r in roles.values():
            ctrl.update(r["members"])
        rec["controllers"] = {c: self.observe_address(c) for c in sorted(ctrl)}
        rec["errors"] = list(self.errors)
        return rec


def facts_from_raw(raw: dict) -> dict:
    """Classify observations into anchor facts keyed by controller address (the only place this rule lives)."""
    out = {}

    def exposed(obs: dict):
        if obs.get("is_contract") is False:
            n = obs.get("nonce")
            return None if n is None else n > 0
        if obs.get("threshold") and obs.get("owners") and obs.get("sub"):
            th = obs["threshold"]
            ex = [exposed(obs["sub"].get(o, {})) for o in obs["owners"]]
            if all(e is not None for e in ex):
                return sum(bool(e) for e in ex) >= th
        return None

    for tok in raw["tokens"]:
        for addr, obs in tok.get("controllers", {}).items():
            out[addr] = dict(key_exposed=exposed(obs), is_contract=obs.get("is_contract"), nonce=obs.get("nonce"),
                             threshold=obs.get("threshold"), n_owners=len(obs.get("owners") or []) or None,
                             min_delay=obs.get("min_delay"))
            if obs.get("owner") and obs.get("sub", {}).get(obs["owner"]):
                inner = obs["sub"][obs["owner"]]
                out[obs["owner"]] = dict(key_exposed=exposed(inner), is_contract=inner.get("is_contract"),
                                         nonce=inner.get("nonce"), threshold=inner.get("threshold"),
                                         n_owners=len(inner.get("owners") or []) or None, min_delay=inner.get("min_delay"))
    return out


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()
