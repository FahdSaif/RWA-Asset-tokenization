import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from arca_ai.crr import CRR

def test_signature_roundtrip(tmp_path):
    key = str(tmp_path / "agent.pem")
    crr = CRR("eligible", True, ["ok"], {"a": 1}, "agent-x")
    signed = crr.sign(key)
    assert signed.verify() is True

def test_tampered_crr_fails(tmp_path):
    key = str(tmp_path / "agent.pem")
    signed = CRR("eligible", True, ["ok"], {"a": 1}, "agent-x").sign(key)
    signed.crr.outcome = False          # tamper after signing
    assert signed.verify() is False
