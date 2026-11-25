"""Evidence from ABI function names (observed in the census) and from controller observations.

An ABI shows that a capability exists, not who may use it or how a signature is checked; the surface types below
are therefore *candidates* that the source scan or a reviewer confirms.
"""
from __future__ import annotations

from .classify import Finding

# surface type -> (required name patterns (any), supporting patterns (any, optional)), matched case-insensitively
ABI_SURFACES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "eip2612_permit": (("permit",), ("domain_separator", "permit_typehash", "nonces")),
    "eip712_domain": (("eip712domain",), ()),
    "erc2771_forwarder": (("istrustedforwarder", "trustedforwarder"), ()),
    "erc1271_contract_signature": (("isvalidsignature",), ()),
    "access_control_roles": (("grantrole", "hasrole"), ("_role",)),
    "enumerable_roles": (("getrolemember",), ()),
    "external_compliance_module": (("setcompliance", "compliance_service", "compliance"), ()),
    "signed_parameter_update": (("withnonce",), ("nonce",)),
    "upgradeable_proxy": (("upgradeto", "setimplementation"), ()),
}


def scan_abi(token_address: str, functions: list[str]) -> list[Finding]:
    low = [f.lower() for f in functions]
    out = []
    for surface, (req, sup) in ABI_SURFACES.items():
        hits = [functions[i] for i, f in enumerate(low) if any(p == f or (len(p) > 6 and p in f) for p in req)]
        if not hits:
            continue
        support = [functions[i] for i, f in enumerate(low) if any(p in f for p in sup)] if sup else []
        roles = sorted({f for f in functions if f.endswith("_ROLE") or f.startswith("ROLE_")}) if surface == "access_control_roles" else []
        out.append(Finding(evidence_id=f"abi:{token_address}:{surface}", token=token_address, kind="abi", surface=surface,
                           location="abi", snippet=", ".join(sorted(set(hits + support)))[:300], extra=dict(roles=roles)))
    return out


def scan_controllers(dep) -> list[Finding]:
    """One finding per observed controlling key (EOA, multisig, timelock) of the census."""
    out = []
    for a in dep.anchors:
        if not a.controller_address:
            continue
        for tok in a.tokens:
            out.append(Finding(evidence_id=f"ctrl:{tok}:{a.controller_address}", token=tok, kind="controller",
                               surface=f"controller_{a.controller_type}", location=a.controller_address,
                               snippet=f"{a.role} {a.controller_type} threshold={a.n_keys}",
                               extra=dict(anchor_id=a.anchor_id, n_keys=a.n_keys)))
    return out
