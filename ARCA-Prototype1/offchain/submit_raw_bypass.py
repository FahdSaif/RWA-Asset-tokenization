"""The adversarial path. Construct the SAME transfer as a raw extrinsic, skipping
any client-side compliance logic entirely — the way a technically capable actor
would interact directly with the protocol. Expected outcome: STILL rejected,
because the check lives in the runtime, not the client.

We deliberately pass a forged attestation id that was never verified/recorded by
the Verification pallet."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compliance-ai", "src"))
from arca_ai.config import NODE_WS

FORGED_ATT = "0x" + "bb" * 32     # never recorded on-chain
ADMITTED_CRR = "0x" + "cc" * 32

def submit_raw(asset_id=42, to_uri="//Bob", jurisdiction=36):
    from substrateinterface import SubstrateInterface, Keypair
    sub = SubstrateInterface(url=NODE_WS)
    alice = Keypair.create_from_uri("//Alice")
    bob = Keypair.create_from_uri(to_uri)
    # Same dispatchable, hand-built, no application layer in front of it.
    call = sub.compose_call(
        call_module="TxValidation", call_function="transfer",
        call_params={
            "asset_id": asset_id, "to": bob.ss58_address, "jurisdiction": jurisdiction,
            "zk_attestation_id": FORGED_ATT, "crr_id": ADMITTED_CRR,
        },
    )
    ext = sub.create_signed_extrinsic(call=call, keypair=alice)
    r = sub.submit_extrinsic(ext, wait_for_inclusion=True)
    return r.is_success, r

if __name__ == "__main__":
    ok, r = submit_raw()
    print("accepted" if ok else "rejected", "-", r.error_message)
