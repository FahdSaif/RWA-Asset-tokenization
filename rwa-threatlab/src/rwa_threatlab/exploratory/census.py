"""Experiment C: census of privileged control in real tokenised-asset contracts (docs/EXPLORATORY_PLAN_C_ADDENDUM.md).

Input: the raw observations written by the Colab notebook (`census_raw.json`). The classification rules of the addendum are applied here, in code.
Output: counts and shares only; a per-token table. No inference about intent or risk of any token.
"""
from __future__ import annotations

import re
from collections import Counter

ZERO = "0x" + "0" * 40

# function-name categories, case-insensitive substring match (section 3 of the addendum)
CATEGORIES: dict[str, tuple[str, ...]] = {
    "pause": ("pause",),
    "freeze_blacklist": ("freeze", "frozen", "blacklist", "blocklist", "denylist", "sanction"),
    "forced_transfer_recovery": ("forcedtransfer", "forcetransfer", "clawback", "seize", "confiscate", "recoveryaddress", "recoveraddress", "forceburn"),
    "upgrade": ("upgradeto", "setimplementation"),
}
MINT_BURN = re.compile(r"^(mint|burn)", re.I)


def categories_present(functions: list[str]) -> dict[str, bool]:
    low = [f.lower() for f in functions]
    out = {k: any(any(p in f for p in pats) for f in low) for k, pats in CATEGORIES.items()}
    out["mint_burn"] = any(MINT_BURN.match(f) for f in functions)
    return out


def controller_type(addr: str | None, controllers: dict[str, dict], hops_left: int = 1) -> dict:
    """Controller type of an address, following at most one 'owner()' hop through a plain contract."""
    if addr is None:
        return dict(type="unknown")
    a = addr.lower()
    if a == ZERO:
        return dict(type="none")
    info = controllers.get(a)
    if info is None:
        return dict(type="unknown")
    if info.get("is_contract") is False:
        return dict(type="eoa")
    if info.get("is_contract") is None:
        return dict(type="unknown")
    if info.get("threshold") is not None:
        return dict(type="multisig", threshold=info["threshold"], owners=info.get("n_owners"))
    if info.get("min_delay") is not None:
        return dict(type="timelock", delay_seconds=info["min_delay"])
    if info.get("owner") and hops_left > 0:
        inner = controller_type(info["owner"], controllers, hops_left - 1)
        return dict(inner, via_contract=True)
    return dict(type="other_contract")


def upgrade_control(rec: dict) -> dict:
    if not rec.get("is_proxy"):
        return dict(type="no_proxy_detected")
    admin = rec.get("admin_slot")
    if admin is None or admin.lower() == ZERO:
        return dict(type="not_readable")
    return controller_type(admin, rec.get("controllers", {}))


def owner_control(rec: dict) -> dict:
    for key in ("owner", "default_admin"):
        if rec.get(key) is not None:
            return controller_type(rec[key], rec.get("controllers", {}))
    return dict(type="no_owner_or_default_admin")


def label(c: dict) -> str:
    t = c["type"]
    if t == "multisig" and c.get("threshold") is not None:
        t = f"multisig {c['threshold']}-of-{c['owners']}" if c.get("owners") else f"multisig (threshold {c['threshold']})"
    if t == "timelock" and c.get("delay_seconds") is not None:
        t = f"timelock ({c['delay_seconds']} s)"
    return t + (" via contract" if c.get("via_contract") else "")


def analyse(raw: list[dict]) -> dict:
    rows = []
    for r in raw:
        cats = categories_present(r.get("abi_functions", []))
        up, ow = upgrade_control(r), owner_control(r)
        rows.append(dict(rank=r.get("rank"), address=r["address"], name=r.get("contract_name"), source_verified=bool(r.get("source_verified")),
                         is_proxy=bool(r.get("is_proxy")), upgrade_control=label(up), upgrade_type=up["type"], owner_control=label(ow), owner_type=ow["type"],
                         categories=cats, errors=len(r.get("errors", []))))
    n = len(rows)
    proxies = [x for x in rows if x["is_proxy"]]
    res = dict(n_tokens=n, source_verified=sum(x["source_verified"] for x in rows), proxies=len(proxies),
               upgrade_control_among_proxies=dict(Counter(x["upgrade_type"] for x in proxies)),
               owner_control=dict(Counter(x["owner_type"] for x in rows)),
               categories={k: sum(x["categories"][k] for x in rows) for k in (*CATEGORIES, "mint_burn")},
               with_errors=sum(x["errors"] > 0 for x in rows), tokens=rows)
    return res


def markdown(res: dict) -> str:
    n = res["n_tokens"]
    head = (f"{n} contracts: source verified {res['source_verified']}; proxies {res['proxies']}; "
            f"with at least one read error {res['with_errors']}.\n\n")
    def table(title: str, d: dict) -> str:
        return f"**{title}**\n\n| Type | Count |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in sorted(d.items(), key=lambda kv: -kv[1])) + "\n\n"
    cat = "**Function-name categories present (count of contracts)**\n\n| Category | Count |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in res["categories"].items()) + "\n\n"
    tok = "| # | Name | Verified | Proxy | Upgrade control | Owner control | pause | freeze/blacklist | forced transfer/recovery | mint/burn | upgrade |\n|---|---|---|---|---|---|---|---|---|---|---|\n"
    tok += "\n".join(f"| {t['rank']} | {t['name']} | {'yes' if t['source_verified'] else 'no'} | {'yes' if t['is_proxy'] else 'no'} | {t['upgrade_control']} | {t['owner_control']} | "
                     + " | ".join('x' if t['categories'][k] else '' for k in ('pause', 'freeze_blacklist', 'forced_transfer_recovery', 'mint_burn', 'upgrade')) + " |"
                     for t in res["tokens"])
    return head + table("Upgrade control among proxies", res["upgrade_control_among_proxies"]) + table("Owner control (owner() or defaultAdmin())", res["owner_control"]) + cat + tok
