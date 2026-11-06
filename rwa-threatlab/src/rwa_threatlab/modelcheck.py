#!/usr/bin/env python3
"""
Bounded explicit-state model of the reference architecture (paper's threat model).

Purpose: mechanically check (i) that the attack paths in the trees are realisable in an
abstract model, (ii) which adversary capabilities are *necessary* for a violation under
each mitigation configuration (minimal cut sets), and (iii) that cross-chain violations
arise from composition even when each instance is individually correct.
This is NOT a verification of any deployed system.

Model
  participants  u (eligible on both chains), x (eligible on O only), w (eligible on both,
                never changes), z (eligible nowhere)
  one regulated asset unit at (chain, holder); initial (O, u)
  truth[c][p]   legally correct eligibility on chain c
  store[c][p]   the chain's active rule/credential state (what its Gateway consults)
  violation     asset is placed with a holder who is NOT eligible on that chain by truth
Actions
  honest/any participant : xfer(c,r), bridge(c->c',r)
  exogenous              : law_change  (u loses eligibility everywhere: sanction or revocation)
                           activate(c)  (the change reaches chain c's store)
  adversary capabilities : raw_path, gw_defect, admin_force, upgrade, gov_collude,
                           suppress_contest, oracle_poison, issuer_forge, issuer_unlisted
Mitigation switches (cfg): dest_mediation, challenge, review_ingest, multi_source, allowlist,
                           priv_via_gateway, guarded_upgrade, tighten_immediate, atomic_activation
"""
import itertools, sys
from collections import deque

U,X,W,Z = 0,1,2,3
NAMES = "uxwz"
O,D = 0,1
CAPS = ["raw_path","gw_defect","admin_force","upgrade","gov_collude",
        "suppress_contest","oracle_poison","oracle_second_feed","issuer_forge","issuer_unlisted"]

def init():
    truth = ((1,1,1,0),(1,0,1,0))            # truth[c][p]
    store = ((1,1,1,0),(1,0,1,0))
    # (loc, holder, truth, store, gw_perm(O,D), prop, blocked, law_done, activated(O,D), bad)
    return (O,U,truth,store,(0,0),None,0,0,(0,0),0)

def put(t,c,p,v):
    l=[list(t[0]),list(t[1])]; l[c][p]=v; return (tuple(l[0]),tuple(l[1]))

def moves(s, caps, cfg, scope):
    loc,h,truth,store,perm,prop,blk,law,act,bad = s
    out=[]
    def place(c,r,s_=s,extra=None):
        ns=list(s_); ns[0]=c; ns[1]=r
        if truth[c][r]==0: ns[9]=1
        return tuple(ns)
    # ---- mediated user paths
    for r in (U,X,W,Z):
        # transfer on current chain
        gw_ok = store[loc][r]==1 or perm[loc]==1 or ("gw_defect" in caps and truth[loc][r]==0) \
                or ("raw_path" in caps)
        if gw_ok and r!=h: out.append(("xfer",place(loc,r)))
        # bridge to the other chain
        if "bridge" in scope:
            o,d=loc,1-loc
            if store[o][r]==1 or perm[o]==1:
                dest_ok = (store[d][r]==1 or perm[d]==1) if cfg["dest_mediation"] else True
                if dest_ok: out.append(("bridge",place(d,r)))
    # ---- privileged administrative / recovery operation (forced transfer)
    if "admin_force" in caps:
        for r in (U,X,W,Z):
            if r==h: continue
            if cfg["priv_via_gateway"]:
                if store[loc][r]==1: out.append(("admin_force",place(loc,r)))
            else: out.append(("admin_force",place(loc,r)))
    # ---- runtime upgrade replacing the Gateway with a permissive one
    if "upgrade" in caps and not cfg["guarded_upgrade"]:
        for c in (O,D):
            if not perm[c] and (c==O or "bridge" in scope):
                ns=list(s); p=list(perm); p[c]=1; ns[4]=tuple(p); out.append(("upgrade",tuple(ns)))
    # ---- exogenous eligibility loss for u (sanction / revocation) + propagation
    if "law" in scope and not law:
        ns=list(s); ns[2]=put(put(truth,O,U,0),D,U,0); ns[7]=1
        if cfg["atomic_activation"]:
            st=put(put(store,O,U,0),D,U,0); ns[3]=st; ns[8]=(1,1)
        elif cfg["tighten_immediate"]:
            ns[3]=put(store,O,U,0); ns[8]=(1,0)       # tightening takes effect on authorising chain at once
        out.append(("law_change",tuple(ns)))
    if "law" in scope and law:
        for c in (O,D):
            if not act[c] and (c==O or "bridge" in scope):
                ns=list(s); ns[3]=put(store,c,U,0); a=list(act); a[c]=1; ns[8]=tuple(a); out.append(("activate",tuple(ns)))
    # ---- governance relaxation of z (rule corruption) : B1 / B3
    def start_prop(src):
        ns=list(s)
        # relaxation proposals are subject to the challenge window if configured
        ns[5]=(O,Z,1,src,"proposed")
        return tuple(ns)
    if prop is None:
        if "gov_collude" in caps: out.append(("gov_propose",start_prop("gov")))
        if "oracle_poison" in caps:
            single_feed_ok = (not cfg["multi_source"]) or ("oracle_second_feed" in caps)
            ingest_ok = (not cfg["review_ingest"]) or ("gov_collude" in caps)
            if single_feed_ok and ingest_ok: out.append(("oracle_ingest",start_prop("oracle")))
    else:
        c,p,v,src,stage = prop
        if stage=="proposed":
            if not cfg["challenge"]:
                ns=list(s); ns[3]=put(store,c,p,v); ns[5]=None; out.append(("activate_rule",tuple(ns)))
            else:
                # honest members contest unauthorised (gov-originated) updates unless suppressed;
                # oracle-originated updates look authorised and are not contestable.
                if src=="gov" and not blk:
                    ns=list(s); ns[5]=None; out.append(("honest_contest",tuple(ns)))
                if "suppress_contest" in caps and src=="gov" and not blk:
                    ns=list(s); ns[6]=1; out.append(("suppress_contest",tuple(ns)))
                if src=="oracle" or blk:
                    ns=list(s); ns[5]=(c,p,v,src,"matured"); out.append(("mature",tuple(ns)))
        elif stage=="matured":
            ns=list(s); ns[3]=put(store,c,p,v); ns[5]=None; out.append(("activate_rule",tuple(ns)))
    # ---- issuer compromise : forged credential for z accepted on both chains
    if "issuer_forge" in caps and store[O][Z]==0:
        out.append(("issuer_forge",s[:3]+(put(put(store,O,Z,1),D,Z,1),)+s[4:]))
    if "issuer_unlisted" in caps and not cfg["allowlist"] and store[O][Z]==0:
        out.append(("issuer_unlisted",s[:3]+(put(put(store,O,Z,1),D,Z,1),)+s[4:]))
    return out

def search(caps, cfg, scope):
    s0=init(); seen={s0:None}; q=deque([s0]); 
    while q:
        s=q.popleft()
        if s[9]:      # violation
            tr=[]; 
            while seen[s] is not None:
                p,a=seen[s]; tr.append(a); s=p
            return list(reversed(tr)), len(seen)
        for a,ns in moves(s,caps,cfg,scope):
            if ns not in seen: seen[ns]=(s,a); q.append(ns)
    return None, len(seen)

BASE = dict(dest_mediation=False,challenge=False,review_ingest=False,multi_source=False,allowlist=False,
            priv_via_gateway=False,guarded_upgrade=False,tighten_immediate=False,atomic_activation=False)
FULL = dict(dest_mediation=True,challenge=True,review_ingest=True,multi_source=True,allowlist=True,
            priv_via_gateway=True,guarded_upgrade=True,tighten_immediate=True,atomic_activation=False)

def minimal_cuts(cfg, scope, universe=CAPS, maxk=3):
    hits=[]
    for k in range(0,maxk+1):
        for comb in itertools.combinations(universe,k):
            cs=set(comb)
            if any(h<=cs for h in hits): continue
            tr,_=search(cs,cfg,scope)
            if tr is not None: hits.append(cs)
    return hits

def fmt(cs): return "{"+", ".join(sorted(cs))+"}" if cs else "{} (no adversary capability)"

LADDER = [
 ("L0", "Runtime mediation of user and bridge-inbound paths only", dict(BASE,dest_mediation=True)),
 ("L1", "+ privileged operations routed through the Gateway; guarded upgrades", dict(BASE,dest_mediation=True,priv_via_gateway=True,guarded_upgrade=True)),
 ("L2", "+ issuer allow-list", dict(BASE,dest_mediation=True,priv_via_gateway=True,guarded_upgrade=True,allowlist=True)),
 ("L3", "+ challenge window on relaxations", dict(BASE,dest_mediation=True,priv_via_gateway=True,guarded_upgrade=True,allowlist=True,challenge=True)),
 ("L4", "+ human review before oracle data is ingested", dict(BASE,dest_mediation=True,priv_via_gateway=True,guarded_upgrade=True,allowlist=True,challenge=True,review_ingest=True)),
 ("L5", "+ multi-source oracle cross-validation", dict(BASE,dest_mediation=True,priv_via_gateway=True,guarded_upgrade=True,allowlist=True,challenge=True,review_ingest=True,multi_source=True)),
]
FAULTS = {"raw_path","gw_defect"}
def run(verbose: bool = True) -> dict:
    res: dict = {}
    comp = [("I1", "Instance O alone, user transactions", {"user"}, BASE),
            ("I2", "Instance D alone, user transactions", {"user"}, BASE),
            ("I3", "O and D joined by a baseline bridge", {"user", "bridge"}, BASE),
            ("I4", "As I3, destination mediates inbound mints", {"user", "bridge"}, dict(BASE, dest_mediation=True))]
    res["composition"] = []
    for k, name, scope, cfg in comp:
        tr, n = search(set(), cfg, scope)
        res["composition"].append(dict(id=k, name=name, violation=bool(tr), trace=tr, states=n))
    lag = [("B2", "One instance, eligibility loss, baseline activation", {"user", "law"}, BASE),
           ("B2m", "As B2, tightening effective immediately", {"user", "law"}, dict(BASE, tighten_immediate=True)),
           ("E1", "Two instances, immediate tightening at origin only", {"user", "bridge", "law"},
            dict(BASE, tighten_immediate=True, dest_mediation=True)),
           ("E1m", "Two instances, atomic cross-instance activation", {"user", "bridge", "law"},
            dict(BASE, atomic_activation=True, dest_mediation=True))]
    res["lag"] = []
    for k, name, scope, cfg in lag:
        tr, n = search(set(), cfg, scope)
        res["lag"].append(dict(id=k, name=name, violation=bool(tr), trace=tr, states=n))
    universe = [c for c in CAPS if c not in FAULTS]
    res["ladder"] = []
    for k, name, cfg in LADDER:
        cuts = minimal_cuts(cfg, {"user"}, universe=universe)
        res["ladder"].append(dict(id=k, name=name, cuts=[sorted(c) for c in cuts]))
    for k, name, cfg in LADDER:
        for f in FAULTS:
            assert search({f}, cfg, {"user"})[0] is not None
    res["faults_singleton_at_all_levels"] = True
    if verbose:
        for c in res["composition"] + res["lag"]:
            print(f" {c['id']:4s} {c['name']:55s} violation={'YES' if c['violation'] else 'no ':3s} {c['trace'] or ''}")
        for l in res["ladder"]:
            print(f" [{l['id']}] {l['name']}")
            for c in l["cuts"]:
                print("      {" + ", ".join(c) + "}")
    return res
