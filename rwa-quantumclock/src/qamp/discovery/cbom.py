"""CycloneDX 1.6-style cryptography bill of materials (CBOM) and RQ1 scoring."""
from __future__ import annotations

import csv
import uuid
from collections import defaultdict
from pathlib import Path

from .classify import InventoryEntry

_CURVES = {"secp256k1-ecdsa": "secp256k1", "p256-ecdsa": "P-256", "bls12-381": "BLS12-381"}


def to_cbom(entries: list[InventoryEntry], subject: str) -> dict:
    comps = []
    for e in entries:
        ref = f"crypto:{e.token}:{e.surface}"
        comps.append({
            "type": "cryptographic-asset",
            "bom-ref": ref,
            "name": f"{e.surface} ({e.algorithm})",
            "cryptoProperties": {
                "assetType": "algorithm",
                "algorithmProperties": {
                    "primitive": "signature",
                    "parameterSetIdentifier": _CURVES.get(e.algorithm, e.algorithm),
                    "curve": _CURVES.get(e.algorithm),
                    "nistQuantumSecurityLevel": 0 if e.quantum_vulnerable else None,
                },
            },
            "evidence": {"occurrences": [{"location": x} for x in e.evidence]},
            "properties": [
                {"name": "qamp:token", "value": e.token},
                {"name": "qamp:signer", "value": e.signer},
                {"name": "qamp:anchorRole", "value": e.anchor_role},
                {"name": "qamp:complianceRelevant", "value": str(e.compliance_relevant).lower()},
                {"name": "qamp:classifier", "value": e.classifier},
                {"name": "qamp:note", "value": e.note},
            ],
        })
    return {"bomFormat": "CycloneDX", "specVersion": "1.6", "serialNumber": f"urn:uuid:{uuid.uuid5(uuid.NAMESPACE_URL, subject)}",
            "version": 1, "metadata": {"component": {"type": "application", "name": subject}}, "components": comps}


def read_labels(path: Path) -> dict[tuple[str, str], bool]:
    """Ground truth CSV: token,surface,present (1/0),annotator,evidence,notes. Disagreements must be resolved first."""
    out = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            out[(row["token"].lower(), row["surface"])] = row["present"].strip() == "1"
    return out


def score(entries: list[InventoryEntry], labels: dict[tuple[str, str], bool]) -> dict:
    """Precision, recall and F1 per surface type and overall, over (token, surface) pairs that were labelled."""
    pred = {(e.token.lower(), e.surface) for e in entries}
    per = defaultdict(lambda: dict(tp=0, fp=0, fn=0))
    for (t, s), present in labels.items():
        hit = (t, s) in pred
        if present and hit:
            per[s]["tp"] += 1
        elif present and not hit:
            per[s]["fn"] += 1
        elif not present and hit:
            per[s]["fp"] += 1
    unlabelled = sorted(p for p in pred if p not in labels)

    def prf(d):
        p = d["tp"] / (d["tp"] + d["fp"]) if d["tp"] + d["fp"] else None
        r = d["tp"] / (d["tp"] + d["fn"]) if d["tp"] + d["fn"] else None
        f = 2 * p * r / (p + r) if p and r else (0.0 if p is not None and r is not None else None)
        return dict(d, precision=p, recall=r, f1=f)
    tot = dict(tp=sum(v["tp"] for v in per.values()), fp=sum(v["fp"] for v in per.values()), fn=sum(v["fn"] for v in per.values()))
    return dict(overall=prf(tot), per_surface={k: prf(v) for k, v in sorted(per.items())},
                predicted_but_unlabelled=len(unlabelled))


def cohen_kappa(a: dict[tuple[str, str], bool], b: dict[tuple[str, str], bool]) -> float | None:
    keys = sorted(set(a) & set(b))
    if not keys:
        return None
    n = len(keys)
    agree = sum(a[k] == b[k] for k in keys) / n
    pa, pb = sum(a[k] for k in keys) / n, sum(b[k] for k in keys) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (agree - pe) / (1 - pe)
