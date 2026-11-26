"""Evidence from verified source code, with file and line. Comments are ignored."""
from __future__ import annotations

import json
import re

from .classify import Finding

SOURCE_PATTERNS: dict[str, list[str]] = {
    "ecrecover_direct": [r"\becrecover\s*\("],
    "ecdsa_library": [r"\bECDSA\s*\.\s*(try)?[Rr]ecover\b", r"\bSignatureChecker\s*\.\s*isValidSignatureNow\b"],
    "eip2612_permit": [r"\bfunction\s+permit\s*\("],
    "eip712_domain": [r"\b_hashTypedDataV4\s*\(", r"\bEIP712\b", r"\bDOMAIN_SEPARATOR\b"],
    "erc1271_contract_signature": [r"\bisValidSignature\s*\("],
    "erc2771_forwarder": [r"\bisTrustedForwarder\s*\(", r"\bERC2771Context\b", r"\b_msgSender\s*\("],
    "p256_verifier": [r"\bP256\b", r"\bsecp256r1\b", r"address\s*\(\s*0x100\s*\)"],
    "bls_precompile": [r"\bBLS12\b", r"address\s*\(\s*0x0?b\s*\)"],
    "access_control_roles": [r"\bonlyRole\s*\(", r"\bAccessControl(Upgradeable|Enumerable)?\b"],
    "ownable_admin": [r"\bonlyOwner\b", r"\bOwnable(2Step)?(Upgradeable)?\b"],
    "upgradeable_proxy": [r"\bupgradeTo(AndCall)?\s*\(", r"\b_authorizeUpgrade\s*\("],
    "external_compliance_module": [r"\bcompliance\s*\(\s*\)", r"\bcanTransfer\s*\(", r"\bisVerified\s*\("],
}
_COMPILED = {k: [re.compile(p) for p in v] for k, v in SOURCE_PATTERNS.items()}
_COMMENT = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def _strip_comments(text: str) -> str:
    """Blanks out comments but keeps line numbers."""
    return _COMMENT.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)


def split_sources(source_code: str) -> dict[str, str]:
    """Splits Etherscan source into files."""
    s = source_code.strip()
    if s.startswith("{{") and s.endswith("}}"):
        s = s[1:-1]
    if s.startswith("{"):
        try:
            j = json.loads(s)
            srcs = j.get("sources", j)
            return {k: (v.get("content", "") if isinstance(v, dict) else str(v)) for k, v in srcs.items()}
        except json.JSONDecodeError:
            pass
    return {"contract.sol": source_code}


def scan_source(token_address: str, source_code: str) -> list[Finding]:
    out = []
    for fname, text in split_sources(source_code).items():
        clean = _strip_comments(text)
        lines = clean.splitlines()
        raw_lines = text.splitlines()
        for surface, pats in _COMPILED.items():
            for ln, line in enumerate(lines, start=1):
                if any(p.search(line) for p in pats):
                    out.append(Finding(evidence_id=f"src:{token_address}:{fname}:{ln}", token=token_address, kind="source",
                                       surface=surface, location=f"{fname}:{ln}", snippet=raw_lines[ln - 1].strip()[:200]))
    return out
