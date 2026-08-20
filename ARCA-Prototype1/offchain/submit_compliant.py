"""Submit a compliant transfer through the intended path (with valid attestation
and admitted CRR). Expected outcome: accepted."""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "compliance-ai", "src"))
from arca_ai.config import NODE_WS

VALID_ATT = "0x" + "aa" * 32
ADMITTED_CRR = "0x" + "cc" * 32

def submit(asset_id=42, to_uri="//Bob", jurisdiction=36):
    from substrateinterface import SubstrateInterface, Keypair
    sub = SubstrateInterface(url=NODE_WS)
    alice = Keypair.create_from_uri("//Alice")
    bob = Keypair.create_from_uri(to_uri)
    call = sub.compose_call(
        call_module="TxValidation", call_function="transfer",
        call_params={
            "asset_id": asset_id, "to": bob.ss58_address, "jurisdiction": jurisdiction,
            "zk_attestation_id": VALID_ATT, "crr_id": ADMITTED_CRR,
        },
    )
    ext = sub.create_signed_extrinsic(call=call, keypair=alice)
    r = sub.submit_extrinsic(ext, wait_for_inclusion=True)
    return r.is_success, r

if __name__ == "__main__":
    ok, r = submit()
    print("accepted" if ok else "rejected", "-", r.error_message)
