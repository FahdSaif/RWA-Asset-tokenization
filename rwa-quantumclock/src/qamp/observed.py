"""Turns raw chain data into model inputs. Every rule is here so it can be cited and changed."""
from __future__ import annotations

import datetime as dt
import statistics
from collections import defaultdict

from . import config
from .keccak import selector
from .model import Calendar

# surfaces that contract code can decide, and their functions
BYTECODE_SURFACES: dict[str, list[str]] = {
    "eip2612_permit": ["permit(address,address,uint256,uint256,uint8,bytes32,bytes32)"],
    "eip712_domain": ["eip712Domain()", "DOMAIN_SEPARATOR()"],
    "erc2771_forwarder": ["isTrustedForwarder(address)", "trustedForwarder()"],
    "erc1271_contract_signature": ["isValidSignature(bytes32,bytes)"],
    "access_control_roles": ["grantRole(bytes32,address)", "hasRole(bytes32,address)"],
    "enumerable_roles": ["getRoleMember(bytes32,uint256)"],
    "upgradeable_proxy": ["upgradeTo(address)", "upgradeToAndCall(address,bytes)"],
}
SURFACE_SELECTORS = {k: {selector(s) for s in v} for k, v in BYTECODE_SURFACES.items()}


# --- contract code

def selectors_from_bytecode(code_hex: str | None) -> set[str]:
    """Function selectors found in contract code (PUSH4 values).

    May include a few false positives; reported as a limitation."""
    if not code_hex or code_hex in ("0x", "0x0"):
        return set()
    b = bytes.fromhex(code_hex[2:] if code_hex.startswith("0x") else code_hex)
    out, i = set(), 0
    while i < len(b):
        op = b[i]
        if 0x60 <= op <= 0x7F:
            n = op - 0x5F
            if op == 0x63 and i + 5 <= len(b):
                out.add("0x" + b[i + 1:i + 5].hex())
            i += 1 + n
        else:
            i += 1
    return out


def bytecode_labels(raw: dict) -> list[dict]:
    """Present / absent labels per token and surface, from contract code. Proxies use both codes."""
    rows = []
    for tok in raw["tokens"]:
        bc = tok.get("bytecode") or {}
        codes = {k: v for k, v in bc.items() if isinstance(v, str) and v.startswith("0x")}
        if not codes:
            continue
        sels = set()
        for v in codes.values():
            sels |= selectors_from_bytecode(v)
        for surface, wanted in SURFACE_SELECTORS.items():
            hit = sorted(wanted & sels)
            present = bool(hit)
            ev = ",".join(hit)
            if surface == "upgradeable_proxy" and (tok.get("impl_slot") or tok.get("admin_slot")):
                present, ev = True, (ev + "," if ev else "") + "eip1967-slot"
            rows.append(dict(token=tok["address"].lower(), surface=surface, present=int(present),
                             annotator="bytecode", evidence=ev, notes="objective label from runtime bytecode"))
    return rows


# --- governance events

KEY_CHANGE_EVENTS = {"AddedOwner(address)", "RemovedOwner(address)", "ChangedThreshold(uint256)",
                     "OwnershipTransferred(address,address)", "AdminChanged(address,address)",
                     "RoleGranted(bytes32,address,address)", "RoleRevoked(bytes32,address,address)",
                     # role holders set through plain setters (Q1b)
                     "NewMinter(address)", "NewBurner(address)", "NewPauser(address)", "NewMultiplierUpdater(address)",
                     "BlacklisterChanged(address)", "MasterMinterChanged(address)", "RescuerChanged(address)"}
ROLE_SET_EVENT_NAMES = {"NewMinter(address)", "NewBurner(address)", "NewPauser(address)", "NewMultiplierUpdater(address)",
                        "BlacklisterChanged(address)", "MasterMinterChanged(address)", "RescuerChanged(address)"}


def _day(ts: int) -> dt.date:
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).date()


def _quarter_index(d: dt.date) -> int:
    return (d.year - config.START_YEAR) * 4 + (d.month - 1) // 3


def change_days(raw: dict, dep) -> dict[str, list[dt.date]]:
    """Days on which an anchor's keys changed (owner, admin, role or Safe signer changes)."""
    by_token = {t["address"].lower(): t for t in raw["tokens"]}
    out: dict[str, set] = defaultdict(set)
    for a in dep.anchors:
        roles = set(a.provenance.get("roles", [a.role]))
        if a.controller_address:
            addr = a.controller_address
            for t in a.tokens:
                for e in by_token.get(t, {}).get("events", []):
                    if e.get("ts") is None or e["event"] not in KEY_CHANGE_EVENTS:
                        continue
                    if e["address"].lower() == addr:
                        out[a.anchor_id].add(_day(e["ts"]))
                    elif e["address"].lower() == t:
                        if ("upgrade_admin" in roles and e["event"].startswith("AdminChanged")) or \
                           ("owner_admin" in roles and e["event"].startswith("OwnershipTransferred")) or \
                           ("role_holder" in roles and (e["event"].startswith("Role") or e["event"] in ROLE_SET_EVENT_NAMES)):
                            out[a.anchor_id].add(_day(e["ts"]))
        elif a.role == "role_holder":
            for t in a.tokens:
                for e in by_token.get(t, {}).get("events", []):
                    if e.get("ts") is not None and e["address"].lower() == t and (
                            e["event"].startswith("Role") or e["event"] in ROLE_SET_EVENT_NAMES):
                        out[a.anchor_id].add(_day(e["ts"]))
    return {k: sorted(v) for k, v in out.items()}


def calendars_from_events(days: dict[str, list[dt.date]], min_changes: int = 3, policy: str = "observed_only",
                          window_end: dt.date | None = None) -> dict[str, Calendar]:
    """Renewal calendar per anchor from its change days.

    observed_only (default): needs 3+ change days; period = median gap in quarters (1-8).
    lower_bound: no change in 2+ years gives period 8.
    Anchors without enough data keep the default."""
    out = {}
    for aid, ds in days.items():
        if len(ds) >= min_changes:
            gaps = [(b - a).days / 91.3125 for a, b in zip(ds, ds[1:])]
            period = int(min(8, max(1, round(statistics.median(gaps)))))
            phase = _quarter_index(ds[-1]) % period
            out[aid] = Calendar(period=period, phase=phase, source=f"observed: {len(ds)} key changes, median gap {statistics.median(gaps):.1f} q")
        elif policy == "lower_bound" and ds and window_end and (window_end - ds[0]).days / 91.3125 >= 8:
            out[aid] = Calendar(period=8, phase=_quarter_index(ds[-1]) % 8, source=f"observed lower bound: {len(ds)} key change(s)")
    return out


def capacity_from_events(days: dict[str, list[dt.date]], dep, cap_max: int = 4) -> dict[str, int]:
    """Per issuer: most anchors changed in one quarter (1 to cap_max)."""
    per: dict[str, dict[int, set]] = defaultdict(lambda: defaultdict(set))
    for a in dep.anchors:
        for d in days.get(a.anchor_id, []):
            per[a.issuer_group][_quarter_index(d)].add(a.anchor_id)
    return {g: int(min(cap_max, max(1, max(len(s) for s in q.values())))) for g, q in per.items() if q}


def issuer_groups(raw_tokens: list[dict], name_group, rank=None) -> dict[str, str]:
    """Tokens that share any controller are one issuer; tokens with the same name rule too.

    Controllers: upgrade admin, owner, default admin, role members and other observed controllers.
    Each group takes the name of its largest token (lowest rank)."""
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    zero = "0x" + "0" * 40   # the zero address means no controller
    owner_of: dict[str, str] = {}
    for t in raw_tokens:
        a = t["address"].lower()
        find(a)
        ctrls = {x.lower() for x in (t.get("admin_slot"), t.get("owner"), t.get("default_admin")) if x}
        ctrls |= {c.lower() for c in (t.get("controllers") or {})}
        for r in (t.get("roles") or {}).values():
            ctrls |= {m.lower() for m in r.get("members", [])}
        ctrls.discard(zero)
        for c in sorted(ctrls):
            if c in owner_of:
                union(owner_of[c], a)
            else:
                owner_of[c] = a
    names = {t["address"].lower(): name_group(t) for t in raw_tokens}
    first_by_name: dict[str, str] = {}
    for a, n in names.items():
        if n in first_by_name:
            union(first_by_name[n], a)
        else:
            first_by_name[n] = a
    rank = rank or {}
    members: dict[str, list[str]] = defaultdict(list)
    for a in names:
        members[find(a)].append(a)
    label = {r: names[min(ms, key=lambda x: (rank.get(x, 10**9), x))] for r, ms in members.items()}
    return {a: label[find(a)] for a in names}


# --- other chains

def topology_from_raw(raw: dict, dep) -> dict[str, dict[str, float]]:
    """Copies of each anchor's tokens on other chains, with value shares.

    A copy counts if the same address has code and the same symbol. Shares follow totalSupply.
    Bridges between copies are assumed. Chains the key could not read count as no copy,
    so this is a lower bound."""
    by_token = {t["address"].lower(): t for t in raw["tokens"]}
    token_shares: dict[str, dict[str, float]] = {}
    for a, t in by_token.items():
        sym = (t.get("symbol") or "").strip().lower()
        inst = {"ethereum": float(t.get("total_supply") or 0)}
        for cid, c in (t.get("chains") or {}).items():
            if c.get("code") and sym and (c.get("symbol") or "").strip().lower() == sym:
                inst[c.get("chain", str(cid))] = float(c.get("total_supply") or 0)
        if len(inst) > 1:
            tot = sum(inst.values())
            token_shares[a] = {k: (v / tot if tot > 0 else 1 / len(inst)) for k, v in inst.items()}
    caps = {t.address: t.market_cap_usd for t in dep.tokens}
    out = {}
    for an in dep.anchors:
        acc: dict[str, float] = defaultdict(float)
        multi = False
        for t in an.tokens:
            sh = token_shares.get(t)
            if sh:
                multi = True
                for k, v in sh.items():
                    acc[k] += caps.get(t, 0) * v
            else:
                acc["ethereum"] += caps.get(t, 0)
        if multi:
            tot = sum(acc.values())
            out[an.anchor_id] = {k: v / tot for k, v in acc.items()} if tot > 0 else {k: 1 / len(acc) for k in acc}
    return out
