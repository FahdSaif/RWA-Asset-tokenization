"""Reads contract data from Etherscan (run in the Colab notebook with your key).

Only collects data; all interpretation is in observed.py.
Per token: source, ABI, controllers, role members, governance events, bytecode,
and the same address on other chains. Errors are recorded, not raised."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Callable

from .keccak import selector, topic

ADMIN_SLOT = "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103"
IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
ZERO = "0x" + "0" * 40

SEL = {k: selector(v) for k, v in dict(
    owner="owner()", default_admin="defaultAdmin()", threshold="getThreshold()", owners="getOwners()",
    min_delay="getMinDelay()", role_member_count="getRoleMemberCount(bytes32)", role_member="getRoleMember(bytes32,uint256)",
    symbol="symbol()", total_supply="totalSupply()").items()}

TOKEN_EVENTS = ["RoleGranted(bytes32,address,address)", "RoleRevoked(bytes32,address,address)",
                "OwnershipTransferred(address,address)", "AdminChanged(address,address)", "Upgraded(address)"]
CONTROLLER_EVENTS = ["AddedOwner(address)", "RemovedOwner(address)", "ChangedThreshold(uint256)",
                     "OwnershipTransferred(address,address)",
                     "CallScheduled(bytes32,uint256,address,uint256,bytes,bytes32,uint256)",
                     "CallExecuted(bytes32,uint256,address,uint256,bytes)"]
EVENT_TOPICS = {topic(e): e for e in TOKEN_EVENTS + CONTROLLER_EVENTS}

# Other chains to check (Etherscan chain ids).
OTHER_CHAINS = {10: "optimism", 56: "bnb", 137: "polygon", 8453: "base", 42161: "arbitrum", 43114: "avalanche",
                5000: "mantle", 59144: "linea", 534352: "scroll", 100: "gnosis", 81457: "blast", 324: "zksync"}


# --- decoding helpers

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
    """Decodes a returned address list."""
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


def decode_string(data: str | None) -> str | None:
    """Decodes a returned string (or bytes32)."""
    if not data or len(data) < 66:
        return None
    h = data[2:]
    try:
        if len(h) >= 192 and int(h[:64], 16) == 32:
            n = int(h[64:128], 16)
            return bytes.fromhex(h[128:128 + 2 * n]).decode("utf-8", "replace")
        return bytes.fromhex(h[:64]).rstrip(b"\x00").decode("utf-8", "replace") or None
    except ValueError:
        return None


def abi_function_names(abi_json: str | None) -> list[str]:
    try:
        abi = json.loads(abi_json or "[]")
    except json.JSONDecodeError:
        return []
    return sorted({x["name"] for x in abi if isinstance(x, dict) and x.get("type") == "function" and x.get("name")})


# --- reader

class Observer:
    """Etherscan reader. Never stores the API key."""

    BASE = "https://api.etherscan.io/v2/api"

    def __init__(self, get_json, key: str, pause: float = 0.22, chainid: int = 1):
        self.get_json, self.key, self.pause, self.chainid = get_json, key, pause, chainid
        self.errors: list[str] = []
        self.calls = 0

    def on_chain(self, chainid: int) -> "Observer":
        o = Observer(self.get_json, self.key, self.pause, chainid)
        o.errors = self.errors
        return o

    def _q(self, params: dict, what: str, soft: bool = False):
        time.sleep(self.pause)
        self.calls += 1
        q = "&".join(f"{k}={v}" for k, v in {"chainid": self.chainid, **params}.items())
        try:
            d = self.get_json(f"{self.BASE}?{q}&apikey={self.key}")
        except Exception as e:  # noqa: BLE001
            if not soft:
                self.errors.append(f"[{self.chainid}] {what}: {type(e).__name__}")
            return None
        if isinstance(d, dict) and "error" in d:
            if not soft:
                self.errors.append(f"[{self.chainid}] {what}: {str(d['error'])[:80]}")
            return None
        if isinstance(d, dict) and d.get("status") == "0" and not isinstance(d.get("result"), (list, dict)):
            if not soft:
                self.errors.append(f"[{self.chainid}] {what}: {str(d.get('message'))[:40]} {str(d.get('result'))[:60]}")
            return None
        return d.get("result") if isinstance(d, dict) else None

    # basic calls
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

    def logs(self, a: str, topic0: str, what: str, max_pages: int = 10) -> list[dict]:
        out = []
        for page in range(1, max_pages + 1):
            r = self._q(dict(module="logs", action="getLogs", address=a, topic0=topic0, fromBlock=0, toBlock="latest",
                             page=page, offset=1000), what)
            if not isinstance(r, list) or not r:
                break
            for x in r:
                out.append(dict(address=a, event=EVENT_TOPICS.get(topic0, topic0), block=word_to_int(x.get("blockNumber")),
                                ts=word_to_int(x.get("timeStamp")), tx=x.get("transactionHash"),
                                topics=x.get("topics", []), data=x.get("data")))
            if len(r) < 1000:
                break
        return out

    # data collection
    def observe_into(self, flat: dict, a: str, hops: int = 1) -> None:
        if a in flat:
            return
        code = self.code(a)
        is_contract = None if code is None else (code not in ("0x", "0x0"))
        rec = dict(is_contract=is_contract)
        flat[a] = rec
        if is_contract is False:
            rec["nonce"] = self.nonce(a)
            return
        if not is_contract:
            return
        rec["threshold"] = word_to_int(self.call(a, SEL["threshold"], "threshold"))
        owners = decode_address_array(self.call(a, SEL["owners"], "owners"))
        rec["owners"] = owners
        rec["n_owners"] = len(owners) if owners else None
        rec["min_delay"] = word_to_int(self.call(a, SEL["min_delay"], "minDelay"))
        rec["owner"] = word_to_address(self.call(a, SEL["owner"], "owner"))
        if hops > 0:
            for s in (owners or [])[:20] + ([rec["owner"]] if rec["owner"] else []):
                self.observe_into(flat, s, hops - 1)

    def observe_token(self, address: str, other_chains: dict[int, str] | None = None) -> dict:
        self.errors = []
        a = address.lower()
        src = self.source(a) or {}
        rec = dict(address=a, contract_name=src.get("ContractName"), source_verified=bool(src.get("SourceCode")),
                   source=src.get("SourceCode"), is_proxy=str(src.get("Proxy")) == "1",
                   implementation=(src.get("Implementation") or "").lower() or None)
        fns = set(abi_function_names(src.get("ABI")))
        if rec["is_proxy"] and rec["implementation"]:
            isrc = self.source(rec["implementation"]) or {}
            rec["implementation_name"] = isrc.get("ContractName")
            rec["implementation_source"] = isrc.get("SourceCode")
            fns |= set(abi_function_names(isrc.get("ABI")))
        rec["abi_functions"] = sorted(fns)
        rec["admin_slot"] = word_to_address(self.slot(a, ADMIN_SLOT))
        rec["impl_slot"] = word_to_address(self.slot(a, IMPL_SLOT))
        rec["owner"] = word_to_address(self.call(a, SEL["owner"], "owner"))
        rec["default_admin"] = word_to_address(self.call(a, SEL["default_admin"], "defaultAdmin"))
        rec["total_supply"] = word_to_int(self.call(a, SEL["total_supply"], "totalSupply"))
        # roles listed in the ABI
        role_names = [f for f in rec["abi_functions"] if f.endswith("_ROLE") or f.startswith("ROLE_")]
        roles = {}
        for name in role_names:
            rid = self.call(a, selector(name + "()"), f"role {name}")
            if not rid:
                continue
            rid = "0x" + rid[2:].rjust(64, "0")[-64:]
            cnt = word_to_int(self.call(a, SEL["role_member_count"] + rid[2:], f"count {name}"))
            members = []
            for i in range(min(cnt or 0, 10)):
                m = word_to_address(self.call(a, SEL["role_member"] + rid[2:] + hex(i)[2:].rjust(64, "0"), f"member {name}"))
                if m:
                    members.append(m)
            roles[name] = dict(role_id=rid, count=cnt, members=members)
        rec["roles"] = roles
        # controllers
        flat: dict = {}
        ctrl = [x for x in (rec["admin_slot"], rec["owner"], rec["default_admin"]) if x]
        for r in roles.values():
            ctrl += r["members"]
        for c in sorted(set(ctrl)):
            self.observe_into(flat, c)
        rec["controllers"] = flat
        # governance events
        events = []
        for ev in TOKEN_EVENTS:
            events += self.logs(a, topic(ev), f"logs {ev.split('(')[0]}")
        for c, info in flat.items():
            if info.get("is_contract"):
                for ev in CONTROLLER_EVENTS:
                    events += self.logs(c, topic(ev), f"logs {ev.split('(')[0]} {c[:10]}")
        rec["events"] = events
        # contract code
        rec["bytecode"] = dict(token=self.code(a), implementation=self.code(rec["implementation"]) if rec["implementation"] else None)
        # same address on other chains
        chains = {}
        for cid, cname in (other_chains if other_chains is not None else OTHER_CHAINS).items():
            ob = self.on_chain(cid)
            code = ob.code(a)
            if code is None:
                chains[cid] = dict(chain=cname, code=None)
                continue
            present = code not in ("0x", "0x0")
            c = dict(chain=cname, code=present)
            if present:
                c.update(symbol=decode_string(ob.call(a, SEL["symbol"], "symbol")),
                         total_supply=word_to_int(ob.call(a, SEL["total_supply"], "totalSupply")),
                         owner=word_to_address(ob.call(a, SEL["owner"], "owner")),
                         default_admin=word_to_address(ob.call(a, SEL["default_admin"], "defaultAdmin")),
                         admin_slot=word_to_address(ob.slot(a, ADMIN_SLOT)))
            chains[cid] = c
        rec["chains"] = chains
        rec["symbol"] = decode_string(self.call(a, SEL["symbol"], "symbol"))
        rec["errors"] = list(self.errors)
        return rec


def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def facts_from_raw(raw: dict) -> dict:
    """Whether each controller's public key is exposed.

    EOA: exposed if it has sent a transaction. Safe: exposed if enough signers are exposed.
    Otherwise unknown."""
    out = {}
    for tok in raw["tokens"]:
        flat = tok.get("controllers", {})

        def exposed(addr: str, depth: int = 0):
            obs = flat.get(addr, {})
            if obs.get("is_contract") is False:
                n = obs.get("nonce")
                return None if n is None else n > 0
            if depth < 2 and obs.get("threshold") and obs.get("owners"):
                ex = [exposed(o, depth + 1) for o in obs["owners"]]
                if all(e is not None for e in ex):
                    return sum(bool(e) for e in ex) >= obs["threshold"]
            if depth < 2 and obs.get("owner"):
                return exposed(obs["owner"], depth + 1)
            return None

        for addr, obs in flat.items():
            out[addr] = dict(key_exposed=exposed(addr), is_contract=obs.get("is_contract"), nonce=obs.get("nonce"),
                             threshold=obs.get("threshold"), n_owners=obs.get("n_owners"), min_delay=obs.get("min_delay"))
    return out
