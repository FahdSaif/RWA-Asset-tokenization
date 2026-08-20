"""Push a governance-signed rule/CRR admission to the chain.

This is the on-chain half of the AI->governance->rule path: after the gate in
graph.py approves a CRR, this submits it via the governance pallet, which verifies
the signature and (on success) admits it to the rule registry.

Requires a running node (make build && ./target/release/... --dev) and
substrate-interface. If the node isn't up, it prints what it WOULD submit so the
demo still narrates end to end.
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compliance-ai", "src"))

from arca_ai.config import NODE_WS

def main():
    try:
        from substrateinterface import SubstrateInterface, Keypair
    except Exception:
        print("substrate-interface not installed; run bootstrap.sh"); return

    try:
        sub = SubstrateInterface(url=NODE_WS)
    except Exception as e:
        print(f"[dry-run] node not reachable at {NODE_WS} ({e}).")
        print("[dry-run] would call Governance.submit_crr(crr_id, signature) then RuleRegistry admit.")
        return

    kp = Keypair.create_from_uri("//Alice")
    call = sub.compose_call(
        call_module="Governance",
        call_function="submit_crr",
        call_params={"crr_id": "0x" + "cc" * 32, "signature": [0] * 64},
    )
    ext = sub.create_signed_extrinsic(call=call, keypair=kp)
    receipt = sub.submit_extrinsic(ext, wait_for_inclusion=True)
    print("included in block:", receipt.block_hash, "success:", receipt.is_success)

if __name__ == "__main__":
    main()
