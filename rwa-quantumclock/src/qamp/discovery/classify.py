"""Turns findings into inventory entries.

RulesClassifier: fixed table. LLMClassifier: asks an LLM; drops entries that cite unknown
evidence and logs every prompt and reply. The rules path works on its own."""
from __future__ import annotations

import json
import os
import time
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable


@dataclass
class Finding:
    evidence_id: str
    token: str
    kind: str          # abi, source or controller
    surface: str
    location: str
    snippet: str = ""
    extra: dict = field(default_factory=dict)


@dataclass
class InventoryEntry:
    token: str
    surface: str
    algorithm: str
    signer: str                   # who signs
    anchor_role: str              # role of the key
    quantum_vulnerable: bool
    compliance_relevant: bool
    evidence: list[str]
    classifier: str
    note: str = ""

    def key(self) -> tuple[str, str]:
        return (self.token, self.surface)


# surface -> algorithm, signer, role, compliance-relevant, note
RULES: dict[str, tuple[str, str, str, bool, str]] = {
    "eip2612_permit": ("secp256k1-ecdsa", "token holders", "holder", False, "EIP-2612 permit: holder signatures approve allowances"),
    "eip712_domain": ("secp256k1-ecdsa", "message signers", "holder", False, "EIP-712 typed-data signatures"),
    "erc2771_forwarder": ("secp256k1-ecdsa", "meta-transaction signers via a trusted forwarder", "forwarder", True,
                          "ERC-2771: the token trusts the forwarder's claim about the sender"),
    "erc1271_contract_signature": ("contract-defined", "contract accounts", "holder", False, "ERC-1271 signature validation"),
    "access_control_roles": ("secp256k1-ecdsa", "role holders (EOAs or multisigs)", "role_holder", True,
                             "role-based administration (mint, burn, freeze, pause, compliance roles)"),
    "enumerable_roles": ("secp256k1-ecdsa", "role holders", "role_holder", True, "role members are readable on-chain"),
    "external_compliance_module": ("secp256k1-ecdsa", "compliance-module administrators", "credential_issuer", True,
                                   "external compliance or identity module decides transfers"),
    "signed_parameter_update": ("secp256k1-ecdsa", "parameter updater", "oracle", True, "nonce-protected parameter update"),
    "upgradeable_proxy": ("secp256k1-ecdsa", "upgrade administrator", "upgrade_admin", True, "code can be replaced"),
    "ecrecover_direct": ("secp256k1-ecdsa", "signers checked with ecrecover", "issuer_or_holder", True, "direct signature verification"),
    "ecdsa_library": ("secp256k1-ecdsa", "signers checked with a library", "issuer_or_holder", True, "library signature verification"),
    "p256_verifier": ("p256-ecdsa", "P-256 signers (passkeys)", "holder", False, "secp256r1 verification"),
    "bls_precompile": ("bls12-381", "BLS signers", "quorum", True, "BLS signature verification"),
    "ownable_admin": ("secp256k1-ecdsa", "owner", "owner_admin", True, "single owner administration"),
    "controller_eoa": ("secp256k1-ecdsa", "one externally owned account", "admin", True, "observed controller"),
    "controller_multisig": ("secp256k1-ecdsa", "multisig owners (threshold)", "admin", True, "observed controller"),
    "controller_timelock": ("secp256k1-ecdsa", "timelock proposers", "admin", True, "observed controller; proposer keys not read"),
}


class RulesClassifier:
    name = "rules"

    def classify(self, findings: list[Finding]) -> list[InventoryEntry]:
        from ..kb.facts import QUANTUM_VULNERABLE_ALGORITHMS
        merged: dict[tuple[str, str], InventoryEntry] = {}
        for f in findings:
            if f.surface not in RULES:
                continue
            alg, signer, role, comp, note = RULES[f.surface]
            k = (f.token, f.surface)
            if k in merged:
                merged[k].evidence.append(f.evidence_id)
                continue
            merged[k] = InventoryEntry(token=f.token, surface=f.surface, algorithm=alg, signer=signer, anchor_role=role,
                                       quantum_vulnerable=alg in QUANTUM_VULNERABLE_ALGORITHMS, compliance_relevant=comp,
                                       evidence=[f.evidence_id], classifier=self.name, note=note)
        return list(merged.values())


PROMPT = """You are auditing the cryptographic inventory of a tokenised real-world-asset contract on Ethereum.
Below are evidence items (id, kind, surface hint, location, snippet). Return ONLY a JSON list. Each element:
{"surface": <one of %s>, "algorithm": <e.g. secp256k1-ecdsa, p256-ecdsa, bls12-381, contract-defined>,
 "signer": <who produces the signatures>, "anchor_role": <holder|role_holder|upgrade_admin|owner_admin|credential_issuer|oracle|forwarder|quorum|admin|issuer_or_holder>,
 "compliance_relevant": <true|false>, "evidence": [<evidence ids from the list below, at least one>], "note": <one sentence>}
Do not invent evidence ids. Omit a surface if the evidence does not support it.
Evidence:
%s"""


class LLMClassifier:
    name = "llm"

    def __init__(self, model: str | None = None, transport: Callable[[str], str] | None = None,
                 log_path: Path | None = None, max_tokens: int = 2000):
        # the model name comes from the run, not the code: set QAMP_LLM_MODEL or pass model=
        self.model, self.max_tokens = model or os.environ.get("QAMP_LLM_MODEL", ""), max_tokens
        self.transport = transport or self._anthropic
        self.log_path = log_path
        self.hallucinated = 0
        self.dropped = 0

    def _anthropic(self, prompt: str) -> str:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set; use RulesClassifier or pass a transport")
        if not self.model:
            raise RuntimeError("no model set: set QAMP_LLM_MODEL or pass model=")
        body = json.dumps(dict(model=self.model, max_tokens=self.max_tokens, temperature=0,
                               messages=[dict(role="user", content=prompt)])).encode()
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body, method="POST",
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            j = json.loads(r.read())
        return "".join(b.get("text", "") for b in j.get("content", []))

    def classify(self, findings: list[Finding]) -> list[InventoryEntry]:
        from ..kb.facts import QUANTUM_VULNERABLE_ALGORITHMS
        by_token: dict[str, list[Finding]] = {}
        for f in findings:
            by_token.setdefault(f.token, []).append(f)
        out: list[InventoryEntry] = []
        for tok, fs in by_token.items():
            ids = {f.evidence_id for f in fs}
            ev = "\n".join(f"- {f.evidence_id} | {f.kind} | {f.surface} | {f.location} | {f.snippet}" for f in fs)
            prompt = PROMPT % (sorted(RULES), ev)
            raw = self.transport(prompt)
            self._log(tok, prompt, raw)
            try:
                items = json.loads(raw[raw.find("["): raw.rfind("]") + 1])
            except (json.JSONDecodeError, ValueError):
                self.dropped += 1
                continue
            for it in items:
                cited = [e for e in it.get("evidence", []) if e in ids]
                self.hallucinated += len([e for e in it.get("evidence", []) if e not in ids])
                if not cited or it.get("surface") not in RULES:
                    self.dropped += 1
                    continue
                alg = it.get("algorithm", "unknown")
                out.append(InventoryEntry(token=tok, surface=it["surface"], algorithm=alg, signer=it.get("signer", ""),
                                          anchor_role=it.get("anchor_role", ""), quantum_vulnerable=alg in QUANTUM_VULNERABLE_ALGORITHMS,
                                          compliance_relevant=bool(it.get("compliance_relevant")), evidence=cited,
                                          classifier=f"{self.name}:{self.model}", note=it.get("note", "")))
        return out

    def _log(self, token: str, prompt: str, response: str) -> None:
        if not self.log_path:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a") as fh:
            fh.write(json.dumps(dict(utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), model=self.model,
                                     token=token, prompt=prompt, response=response)) + "\n")


def entries_to_json(entries: list[InventoryEntry]) -> list[dict]:
    return [asdict(e) for e in entries]
