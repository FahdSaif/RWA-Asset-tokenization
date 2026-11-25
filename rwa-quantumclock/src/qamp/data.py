"""Build a Deployment (tokens + trust anchors) from the real census of tokenised-asset contracts.

Input: rwa-threatlab experiment C (``census_raw.json``, ``census_tokens.txt``): 25 Ethereum contracts labelled
"Real World Assets" on Etherscan, fetched 2026-11-08. The controller classification is imported from
``rwa_threatlab.exploratory.census`` so that both studies use one definition.

What is observed and what is not (recorded per anchor in ``provenance``):
  observed   token address, rank, market cap shown by Etherscan, proxy flag, ABI function names, upgrade-admin and
             owner/defaultAdmin controllers (EOA, multisig threshold and owners, timelock delay)
  assumed    commitment calendars, migration times and costs, issuer grouping, key exposure (until the extraction
             notebook ``notebooks/Q1_fetch_anchor_facts.ipynb`` reads nonces), bridged instances
"""
from __future__ import annotations

import json
import sys
import zlib
from pathlib import Path
from typing import Optional

from . import config
from .model import Anchor, Calendar, Deployment, Token


def _threatlab_census():
    src = config.THREATLAB / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    from rwa_threatlab.exploratory import census  # noqa: E402
    return census


def read_tokens(path: Path = config.CENSUS_TOKENS) -> list[dict]:
    """Rows of census_tokens.txt: address, rank, name (symbol), market cap (USD)."""
    out = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split()
        address, rank, cap = parts[0], int(parts[1]), float(parts[-1].replace(",", ""))
        label = " ".join(parts[2:-1])
        symbol = label[label.rfind("(") + 1:label.rfind(")")] if "(" in label else ""
        name = label[:label.rfind("(")].strip() if "(" in label else label
        out.append(dict(address=address.lower(), rank=rank, name=name, symbol=symbol, market_cap_usd=cap))
    return out


def _resolve(addr: Optional[str], controllers: dict, hops: int = 1) -> dict:
    """Controller of an address, following one owner() hop, keeping the final controlling address."""
    census = _threatlab_census()
    if addr is None:
        return dict(type="unknown", address=None)
    a = addr.lower()
    c = census.controller_type(a, controllers, hops_left=hops)
    final = a
    info = controllers.get(a) or {}
    if c.get("via_contract") and info.get("owner"):
        final = info["owner"].lower()
    return dict(c, address=final if c["type"] not in ("none", "unknown") else None)


def _issuer_group(tok: dict, contract_name: str) -> str:
    """Organisation that carries out the migration. ASSUMPTION: Backed proxies form one group; otherwise the first
    word of the token name shown by Etherscan."""
    if contract_name == "BackedTokenProxy":
        return "Backed"
    return tok["name"].split()[0] if tok["name"] else tok["address"][:8]


def _calendar_for(group: str, role: str) -> Calendar:
    """ASSUMED default calendar: annual renewal; the phase is a deterministic function of the issuer group so that
    groups are not all aligned. Replaced by observed or documented calendars when data/calendars.csv exists."""
    phase = zlib.crc32(f"{group}:{role}".encode()) % 4
    return Calendar(period=4, phase=phase, source="assumed")


def _defaults(controller_type: str, n_keys: int) -> tuple[int, float]:
    """ASSUMED planned execution time (quarters) and relative cost of a migration by controller type."""
    if controller_type == "eoa":
        return 1, 1.0
    if controller_type == "multisig":
        return 2, 1.0 + 0.25 * n_keys
    if controller_type == "timelock":
        return 2, 1.5
    return 2, 2.0   # unobserved or role-based: discovery of the holders is part of the work


def load_census(raw_path: Path = config.CENSUS_RAW, tokens_path: Path = config.CENSUS_TOKENS,
                calendars_path: Optional[Path] = None, facts_path: Optional[Path] = None,
                q1_raw_path: Optional[Path] = None) -> Deployment:
    """``q1_raw_path``: observations of the extraction notebook. When given, observed AccessControl role members
    replace the token's unobserved role-holder anchor (one anchor per member key)."""
    census = _threatlab_census()
    raw = json.loads(Path(raw_path).read_text())["tokens"]
    q1 = {}
    if q1_raw_path and Path(q1_raw_path).exists():
        q1 = {t["address"].lower(): t for t in json.loads(Path(q1_raw_path).read_text())["tokens"]}
    meta = {t["address"]: t for t in read_tokens(tokens_path)}
    known_calendars = _read_calendars(calendars_path) if calendars_path else {}
    facts = json.loads(Path(facts_path).read_text()) if facts_path and Path(facts_path).exists() else {}

    tokens: list[Token] = []
    anchors: dict[str, Anchor] = {}

    def add_anchor(key: str, **kw) -> None:
        if key in anchors:
            a = anchors[key]
            for t in kw["tokens"]:
                if t not in a.tokens:
                    a.tokens.append(t)
            for c in kw["capabilities"]:
                if c not in a.capabilities:
                    a.capabilities.append(c)
            a.signs_records = a.signs_records or kw["signs_records"]
            roles = a.provenance.setdefault("roles", [a.role])
            if kw["role"] not in roles:
                roles.append(kw["role"])
            return
        anchors[key] = Anchor(anchor_id=key, **kw)

    for rec in raw:
        addr = rec["address"].lower()
        m = meta[addr]
        cats = census.categories_present(rec.get("abi_functions", []))
        tok = Token(address=addr, rank=m["rank"], name=m["name"], symbol=m["symbol"], market_cap_usd=m["market_cap_usd"],
                    contract_name=rec.get("contract_name") or "", is_proxy=bool(rec.get("is_proxy")),
                    abi_functions=list(rec.get("abi_functions", [])), categories=cats)
        tokens.append(tok)
        group = _issuer_group(m, tok.contract_name)
        ctrls = rec.get("controllers", {})
        caps_all = [k for k, v in cats.items() if v]
        compliance_caps = [c for c in caps_all if c in ("freeze_blacklist", "forced_transfer_recovery", "pause")]

        # 1. upgrade admin (proxies only): controls the code, hence every capability of the token
        if tok.is_proxy:
            admin = rec.get("admin_slot")
            res = _resolve(admin, ctrls) if admin and admin.lower() != "0x" + "0" * 40 else dict(type="not_readable", address=None)
            _add_controller_anchor(add_anchor, "upgrade_admin", res, tok, group, caps_all, compliance_caps, known_calendars, facts)

        # 2. owner() / defaultAdmin()
        own = None
        for k in ("owner", "default_admin"):
            if rec.get(k):
                own = rec[k]
                break
        if own is not None:
            res = _resolve(own, ctrls)
            if res["type"] != "none":
                _add_controller_anchor(add_anchor, "owner_admin", res, tok, group, caps_all, compliance_caps, known_calendars, facts)

        # 3. role holders: observed members (extraction notebook) or one unobserved anchor per token
        obs = q1.get(addr, {})
        members = sorted({m for r in obs.get("roles", {}).values() for m in r.get("members", [])})
        if members:
            for m_addr in members:
                o = obs.get("controllers", {}).get(m_addr, {})
                ctype = "eoa" if o.get("is_contract") is False else ("multisig" if o.get("threshold") else
                                                                      ("timelock" if o.get("min_delay") else "other_contract"))
                res = dict(type=ctype, address=m_addr, threshold=o.get("threshold"), owners=len(o.get("owners") or []) or None,
                           delay_seconds=o.get("min_delay"))
                _add_controller_anchor(add_anchor, "role_holder", res, tok, group,
                                       [c for c in caps_all if c != "upgrade"], compliance_caps, known_calendars, facts)
        elif compliance_caps or cats.get("mint_burn"):
            res = dict(type="unobserved_role", address=None)
            _add_controller_anchor(add_anchor, "role_holder", res, tok, group,
                                   [c for c in caps_all if c != "upgrade"], compliance_caps, known_calendars, facts)

    dep = Deployment(tokens=tokens, anchors=list(anchors.values()),
                     source=f"rwa-threatlab census {Path(raw_path).name} (25 contracts, Etherscan, 2026-11-08)")
    caps = {t.address: t.market_cap_usd for t in tokens}
    for a in dep.anchors:
        a.value_usd = sum(caps[t] for t in a.tokens)
    return dep


def _add_controller_anchor(add_anchor, role: str, res: dict, tok: Token, group: str, caps: list[str],
                           compliance_caps: list[str], known_calendars: dict, facts: dict) -> None:
    ctype = res["type"]
    address = res.get("address")
    n_keys = int(res.get("threshold") or 1) if ctype == "multisig" else 1
    # one anchor per controlling key: the same multisig acting as upgrade admin and owner is migrated once
    key = f"ctrl:{address}" if address else f"{role}:{tok.address}"
    mq, cost = _defaults(ctype, n_keys)
    delay_s = res.get("delay_seconds") or 0
    cal = known_calendars.get(key) or _calendar_for(group, role)
    f = facts.get(address or "", {}) if address else {}
    exposed = f.get("key_exposed") if f else None
    prov = dict(controller="observed" if address else ("observed: not readable" if ctype == "not_readable" else "not observed"),
                calendar=cal.source, migration_time="assumed", cost="assumed", issuer_group="assumed",
                key_exposed="observed" if exposed is not None else "not observed")
    add_anchor(key, role=role, controller_type=ctype, algorithm="secp256k1-ecdsa", n_keys=n_keys, key_exposed=exposed,
               controller_address=address, timelock_quarters=int(-(-delay_s // (91 * 86400))) if delay_s else 0,
               tokens=[tok.address], capabilities=list(caps), signs_records=bool(compliance_caps),
               issuer_group=group, calendar=cal, migration_quarters=mq, migration_cost=cost,
               instances=["ethereum"], provenance=prov)


def _read_calendars(path: Path) -> dict[str, Calendar]:
    """data/calendars.csv: anchor_id,period_quarters,phase_quarter,source (observed or documented calendars)."""
    import csv
    out = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            out[row["anchor_id"]] = Calendar(period=int(row["period_quarters"]), phase=int(row["phase_quarter"]),
                                             source=row.get("source") or "documented")
    return out


def summary(dep: Deployment) -> dict:
    from collections import Counter
    return dict(
        tokens=len(dep.tokens),
        anchors=len(dep.anchors),
        by_role=dict(Counter(a.role for a in dep.anchors)),
        by_controller=dict(Counter(a.controller_type for a in dep.anchors)),
        shared_anchors=sum(len(a.tokens) > 1 for a in dep.anchors),
        value_usd_total=sum(t.market_cap_usd for t in dep.tokens),
        groups=len({a.issuer_group for a in dep.anchors}),
    )
