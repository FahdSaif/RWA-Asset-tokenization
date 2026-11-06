"""Unit tests for the individual modules of the reference architecture."""
import dataclasses

import pytest

from rwa_threatlab.config import Config
from rwa_threatlab.credentials import Issuer, present
from rwa_threatlab.crypto import Pki
from rwa_threatlab.governance import PState
from rwa_threatlab.ledger import Approval, MediationError, Transfer
from rwa_threatlab.oracle import OracleAggregator, OracleFeed
from rwa_threatlab.rules import RuleSet, classify_change
from rwa_threatlab.scenarios.base import ACCREDITED, ASSET, UNRESTRICTED, make_world


# ---------------- Compliance Trail (T16, T17) ----------------
def test_trail_detects_alteration_and_omission():
    w = make_world(Config.hardened())
    for _ in range(3):
        w.o.transfer(ASSET, "u", "z", 1, None)
    ok, bad = w.o.trail.verify()
    assert ok and bad is None
    t = w.o.trail
    t._entries[1] = dataclasses.replace(t._entries[1], accepted=True)       # retroactive alteration
    assert t.verify() == (False, 1)


def test_trail_detects_omission():
    w = make_world(Config.hardened())
    for _ in range(3):
        w.o.transfer(ASSET, "u", "z", 1, None)
    del w.o.trail._entries[1]
    assert w.o.trail.verify()[0] is False


# ---------------- Ledger narrow waist (P1-P4) ----------------
def test_ledger_refuses_unapproved_and_forged_and_replayed_approvals():
    w = make_world(Config.hardened())
    tx = Transfer(ASSET, "u", "mallory", 1)
    with pytest.raises(MediationError):
        w.o.ledger.apply(tx, None)
    with pytest.raises(MediationError):
        w.o.ledger.apply(tx, Approval(0, "00" * 32))
    ok_tx = Transfer(ASSET, "u", "z", 1)
    dec, appr = w.o.gateway.evaluate(ok_tx, w.proof("u"), 0)           # z is sanctioned -> no approval
    assert not dec.accepted and appr is None
    good = Transfer(ASSET, "treasury", "u", 1)
    dec, appr = w.o.gateway.evaluate(good, w.proof("u"), 0)
    assert dec.accepted
    w.o.ledger.apply(good, appr)
    with pytest.raises(MediationError):                                   # replay
        w.o.ledger.apply(good, appr)
    other = Transfer(ASSET, "treasury", "x", 5)                           # approval bound to its transaction
    dec, appr = w.o.gateway.evaluate(good, w.proof("u"), 0)
    with pytest.raises(MediationError):
        w.o.ledger.apply(other, appr)


# ---------------- Gateway ----------------
def test_gateway_fails_closed_on_malformed_input():
    w = make_world(Config.hardened())
    bad = w.proof("u")
    bad = dataclasses.replace(bad, status=None)                          # corrupt: causes an exception
    dec = w.o.transfer(ASSET, "treasury", "u", 1, bad)
    assert not dec.accepted and dec.code == "ERROR"
    assert w.o.ledger.balance(ASSET, "u") == 100


def test_gateway_logs_every_decision_before_approval():
    w = make_world(Config.hardened())
    n = len(w.o.trail.entries)
    w.o.transfer(ASSET, "treasury", "u", 1, w.proof("u"))
    w.o.transfer(ASSET, "treasury", "z", 1, w.proof("z"))               # rejected: sanctioned
    entries = w.o.trail.entries[n:]
    assert [e.accepted for e in entries] == [True, False]


def test_uniform_errors_hide_the_rejection_reason():
    for cfg, uniform in ((Config.baseline(), False), (Config.hardened(), True)):
        w = make_world(cfg)
        a = w.o.transfer(ASSET, "u", "q", 1, None).public_code
        b = w.o.transfer(ASSET, "u", "z", 1, w.proof("z")).public_code
        assert (a == b) is uniform


# ---------------- Verification module ----------------
def test_verifier_rejects_wrong_subject_tampered_claim_and_revoked():
    w = make_world(Config.hardened())
    assert w.o.transfer(ASSET, "u", "x", 1, w.proof("u")).code == "WRONG_SUBJECT"
    p = w.proof("x", reveal=["kyc", "jur"])
    forged = dataclasses.replace(p, claims={**p.claims, "accredited": "yes"}, sigs={**p.sigs, "accredited": "00"})
    assert w.o.transfer(ASSET, "u", "x", 1, forged).code in ("BAD_SIGNATURE", "MISSING_CLAIM")
    w.issuer.revoke(w.creds["u"].cred_id)
    assert w.o.transfer(ASSET, "treasury", "u", 1, w.proof("u")).code == "REVOKED"


def test_blind_issuance_hides_credential_id_from_issuer_log():
    pki = Pki()
    plain, blind = Issuer("a", pki), Issuer("b", pki, blind=True)
    plain.issue("s", {"k": "v"}, 0)
    blind.issue("s", {"k": "v"}, 0)
    assert "cred_id" in plain.issuance_log[0] and "cred_id" not in blind.issuance_log[0]


# ---------------- Rules ----------------
def test_classify_change():
    base = RuleSet(1, (ACCREDITED,), frozenset({"a"}))
    assert classify_change(base, dataclasses.replace(base, sanctioned=frozenset({"a", "b"}))) == "tighten"
    assert classify_change(base, dataclasses.replace(base, sanctioned=frozenset())) == "relax"
    assert classify_change(base, dataclasses.replace(base, rules=(UNRESTRICTED,))) == "relax"   # mixed -> relax
    assert classify_change(base, base) == "none"


# ---------------- Governance ----------------
def _relax(w):
    return dataclasses.replace(w.o.store.active, sanctioned=frozenset())


def test_threshold_not_met_means_no_activation():
    w = make_world(Config.baseline())
    p = w.o.governance.propose("rules", _relax(w))
    w.sign_with(w.o, p.pid, ["m1", "m2"])                      # threshold is 3
    assert p.state == PState.PROPOSED and "z" in w.o.store.active.sanctioned


def test_non_member_cannot_sign():
    w = make_world(Config.baseline())
    p = w.o.governance.propose("rules", _relax(w))
    assert w.o.governance.sign(p.pid, w.pki.register("outsider")) is False


def test_relaxation_waits_for_challenge_window_and_can_be_contested():
    w = make_world(Config.hardened())
    p = w.o.governance.propose("rules", _relax(w))
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])
    assert p.state == PState.PENDING
    w.clock.advance(w.o.cfg.challenge_window - 1)
    assert "z" in w.o.store.active.sanctioned
    assert w.o.governance.watch() == 1 and p.state == PState.REJECTED
    w.clock.advance(5)
    assert "z" in w.o.store.active.sanctioned


def test_tightening_is_immediate_and_expires_unless_ratified():
    w = make_world(Config.hardened(), sanctioned=())
    tight = dataclasses.replace(w.o.store.active, sanctioned=frozenset({"x"}))
    p = w.o.governance.propose("rules", tight)
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])
    assert p.state == PState.ACTIVE and "x" in w.o.store.active.sanctioned
    w.clock.advance(w.o.cfg.tighten_expiry)
    assert p.state == PState.EXPIRED and "x" not in w.o.store.active.sanctioned

    w2 = make_world(Config.hardened(), sanctioned=())
    p2 = w2.o.governance.propose("rules", dataclasses.replace(w2.o.store.active, sanctioned=frozenset({"x"})))
    w2.sign_with(w2.o, p2.pid, ["m1", "m2", "m3"])
    assert w2.o.governance.ratify(p2.pid, [w2.signers[m] for m in ("m1", "m2", "m3")])
    w2.clock.advance(w2.o.cfg.tighten_expiry)
    assert "x" in w2.o.store.active.sanctioned


# ---------------- Oracle aggregation ----------------
def test_multisource_needs_k_agreeing_feeds_and_flags_bulk_delisting():
    w = make_world(Config.hardened())
    f = [OracleFeed(f"f{i}", w.pki) for i in range(3)]
    agg = OracleAggregator(w.o)
    assert agg.ingest([f[0].publish(set(), 0), f[1].publish({"z"}, 0), f[2].publish({"q"}, 0)]) is None
    assert "no-consensus" in agg.flags
    p = agg.ingest([f[0].publish(set(), 0), f[1].publish(set(), 0)])
    assert p is not None and p.state == PState.PROPOSED and "bulk-delisting" in agg.flags   # needs human review


# ---------------- Bridge ----------------
def test_bridge_refunds_when_destination_rejects():
    w = make_world(Config.hardened(), dest=True, o_rule=ACCREDITED, d_rule=ACCREDITED)
    from rwa_threatlab.scenarios.base import KYC_ONLY
    w.o.store.activate(dataclasses.replace(w.o.store.active, rules=(KYC_ONLY,)), 0, "test")
    res = w.bridge.transfer(ASSET, "u", "x", 10, w.proof("x"), sender_proof=w.proof("u"))
    assert res.status == "rejected_destination_refunded"
    assert w.o.ledger.balance(ASSET, "u") == 100 and w.d.ledger.balance(ASSET, "x") == 0


def test_bridge_quarantines_when_sender_cannot_be_refunded():
    from rwa_threatlab.scenarios.base import KYC_ONLY
    w = make_world(Config.hardened(), dest=True, o_rule=KYC_ONLY, d_rule=ACCREDITED)
    res = w.bridge.transfer(ASSET, "u", "x", 10, w.proof("x"), sender_proof=None)   # destination rejects x
    assert res.status == "quarantined"                                 # sender cannot prove eligibility to be refunded
    assert w.bridge.quarantine == [(ASSET, "u", 10)] and w.d.ledger.balance(ASSET, "x") == 0


# ---------------- Mediation surface (Table 1, executable) ----------------
def test_mediation_surface_matches_table_1():
    w = make_world(Config.hardened())
    rep = {r["path"]: r["mediated"] for r in w.o.mediation_report(ASSET, "u", w.signers)}
    assert [rep[p] for p in ("P1", "P2", "P3", "P4", "P5", "P6")] == [True] * 6
    assert rep["P7"] is False                    # governance-only, by design (paper, Table 1)
    wb = make_world(Config.baseline())
    repb = {r["path"]: r["mediated"] for r in wb.o.mediation_report(ASSET, "u", wb.signers)}
    assert repb["P1"] is True and all(repb[p] is False for p in ("P2", "P3", "P4", "P5", "P6", "P7"))


# ---------------- Regression tests for defects found by the adversarial fuzzer ----------------
def test_pending_relaxation_does_not_overwrite_a_later_tightening():
    """Fuzzer finding #1 (lost update): a stale whole-ruleset snapshot used to undo a newer sanction."""
    w = make_world(Config.hardened(), sanctioned=("z",))
    relax = w.o.governance.propose("rules", dataclasses.replace(w.o.store.active, sanctioned=frozenset()))
    w.sign_with(w.o, relax.pid, ["m1", "m2", "m3"])                       # pending for the challenge window
    w.truth = frozenset({"x"})
    tight = w.o.governance.propose("rules", dataclasses.replace(w.o.store.active, sanctioned=frozenset({"z", "x"})))
    w.sign_with(w.o, tight.pid, ["m1", "m2", "m3"])                       # activates immediately
    w.clock.advance(w.o.cfg.challenge_window)
    assert w.o.store.active.sanctioned == frozenset({"x"})                # z delisted, x still sanctioned


def test_expiry_keeps_a_consistent_sanction_and_only_undoes_its_own_delta():
    """Fuzzer finding #2 (fail-open expiry): a legitimate sanction used to lapse back to the old rule set."""
    w = make_world(Config.hardened(), sanctioned=())
    w.truth = frozenset({"x"})                                            # regulator really designated x
    p = w.o.governance.propose("rules", dataclasses.replace(w.o.store.active, sanctioned=frozenset({"x"})))
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])
    w.clock.advance(w.o.cfg.tighten_expiry + 1)
    assert "x" in w.o.store.active.sanctioned and p.ratified              # consistent with truth: kept
    w2 = make_world(Config.hardened(), sanctioned=("z",))                 # truth = {z}; false tightening of u
    p2 = w2.o.governance.propose("rules", dataclasses.replace(w2.o.store.active, sanctioned=frozenset({"z", "u"})))
    w2.sign_with(w2.o, p2.pid, ["m1", "m2", "m3"])
    w2.clock.advance(w2.o.cfg.tighten_expiry + 1)
    assert w2.o.store.active.sanctioned == frozenset({"z"})               # false tightening undone, z untouched


def test_expiry_never_undoes_a_name_that_is_currently_sanctioned_in_truth():
    """Fuzzer finding #3: an old tightening reaching its review deadline used to undo a re-asserted sanction."""
    w = make_world(Config.hardened(), sanctioned=())
    w.truth = frozenset({"u"})
    p1 = w.o.governance.propose("rules", dataclasses.replace(w.o.store.active, sanctioned=frozenset({"u"})))
    w.sign_with(w.o, p1.pid, ["m1", "m2", "m3"])
    w.truth = frozenset()                                                 # delisted ...
    d = w.o.governance.propose("rules", dataclasses.replace(w.o.store.active, sanctioned=frozenset()))
    w.sign_with(w.o, d.pid, ["m1", "m2", "m3"])
    w.clock.advance(w.o.cfg.challenge_window)
    w.truth = frozenset({"u"})                                            # ... and sanctioned again
    p3 = w.o.governance.propose("rules", dataclasses.replace(w.o.store.active, sanctioned=frozenset({"u"})))
    w.sign_with(w.o, p3.pid, ["m1", "m2", "m3"])
    w.clock.advance(w.o.cfg.tighten_expiry + 1)                           # p1 passes its review deadline
    assert "u" in w.o.store.active.sanctioned


def test_expiry_undoes_only_the_false_names_of_a_mixed_tightening():
    """Strengthens F2: a tightening that adds one true and one false name keeps the true one."""
    w = make_world(Config.hardened(), sanctioned=())
    w.truth = frozenset({"x"})                                            # x is really designated; u is not
    p = w.o.governance.propose("rules", dataclasses.replace(w.o.store.active, sanctioned=frozenset({"x", "u"})))
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])
    assert w.o.store.active.sanctioned == frozenset({"x", "u"})           # active immediately
    w.clock.advance(w.o.cfg.tighten_expiry + 1)
    assert w.o.store.active.sanctioned == frozenset({"x"})                # only the false name was undone


def test_a_proposal_is_judged_by_its_delta_not_by_todays_whole_list():
    """Strengthens F3: later, unrelated sanctions must not make an earlier truthful proposal look inconsistent."""
    w = make_world(Config.hardened(), sanctioned=())
    w.truth = frozenset({"x"})
    p = w.o.governance.propose("rules", dataclasses.replace(w.o.store.active, sanctioned=frozenset({"x"})))
    w.sign_with(w.o, p.pid, ["m1", "m2", "m3"])
    w.truth = frozenset({"x", "k1"})                                      # the regulator later adds another name
    assert w.o.governance.consistent(p) is True
    w.clock.advance(w.o.cfg.tighten_expiry + 1)
    assert p.ratified is True and p.state.value == "active"
