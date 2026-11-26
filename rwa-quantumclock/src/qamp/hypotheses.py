"""Research hypotheses. Unlike tests, they are allowed to fail.

Each states a prediction and a rule for deciding it. Outcomes: CONFIRMED, REFUTED,
INCONCLUSIVE or PENDING DATA. This list is a draft for the authors to approve."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

ALPHA = 0.01
LIST_BASELINES = ("asap_fifo", "deadline", "annual_review", "mosca", "greedy_risk", "kg_score")


@dataclass
class Hypothesis:
    id: str
    rq: str
    statement: str
    prediction: str
    source_of_prediction: str
    experiment: str
    decide: Callable[[dict], tuple[str, str]]


def _better(tests: dict, k: str) -> bool:
    """True if QAMP is significantly cheaper than policy k."""
    t = tests.get(k)
    return bool(t and t["p_holm"] < ALPHA and t["mean_diff"] > 0)


def h1(r):
    main = r["main"]
    ok = [k for k in LIST_BASELINES if _better(main["tests"], k)]
    ev = ", ".join(f"{k}: diff {main['tests'][k]['mean_diff'] / 1e6:+.2f}M, p_holm {main['tests'][k]['p_holm']:.2g}" for k in LIST_BASELINES)
    return ("CONFIRMED" if len(ok) == len(LIST_BASELINES) else "REFUTED"), ev


def h2(r):
    t = r["main"]["tests"]["qamp_pessimistic"]
    # predicted: pessimistic is cheaper
    if t["p_holm"] < ALPHA and t["mean_diff"] < 0:
        out = "CONFIRMED"
    elif t["p_holm"] < ALPHA and t["mean_diff"] > 0:
        out = "REFUTED"
    else:
        out = "INCONCLUSIVE"
    return out, f"pessimistic - stochastic: {t['mean_diff'] / 1e6:+.2f}M, p_holm {t['p_holm']:.2g}"


def h2b(r):
    s = r["main"]["summary"]
    c = r["main"]["costs"]
    import numpy as np
    from .evaluate import sign_flip_test
    d = np.array(c["qamp_pessimistic"]) - np.array(c["qamp_expected"])
    p = sign_flip_test(d)
    out = "CONFIRMED" if (p < ALPHA and d.mean() < 0) else ("REFUTED" if p < ALPHA else "INCONCLUSIVE")
    return out, f"pessimistic {s['qamp_pessimistic']['mean'] / 1e6:.1f}M vs expected {s['qamp_expected']['mean'] / 1e6:.1f}M, p {p:.2g}"


def h3(r):
    t = r["main"]["tests"]["qamp_no_windows"]
    return ("CONFIRMED" if _better(r["main"]["tests"], "qamp_no_windows") else "REFUTED"), \
        f"no-windows - stochastic: {t['mean_diff'] / 1e6:+.3f}M, p_holm {t['p_holm']:.2g}"


def h4(r):
    t = r["period1"]["tests"]["asap_fifo"]
    rel = abs(t["mean_diff"]) / r["period1"]["summary"]["qamp_stochastic"]["mean"]
    out = "CONFIRMED" if (t["p_holm"] >= 0.05 or rel < 0.001) else "REFUTED"
    return out, f"period-1 calendars: asap - stochastic {t['mean_diff'] / 1e6:+.3f}M ({rel:.4%}), p_holm {t['p_holm']:.2g}"


def h5(r):
    s = r["main"]["summary"]
    a, q, o = s["asap_fifo"]["mean_oracle_subset"], s["qamp_stochastic"]["mean_oracle_subset"], s["oracle"]["mean"]
    gap = a - o
    share = (a - q) / gap if gap > 0 else float("nan")
    out = "CONFIRMED" if share >= 0.5 else "REFUTED"
    return out, f"share of the ASAP-to-oracle gap closed: {share:.3f} (ASAP {a / 1e6:.1f}M, QAMP {q / 1e6:.1f}M, oracle {o / 1e6:.1f}M)"


def h6(r):
    g = r["guard"]
    v = g["violations"]
    under = 1 - g["independent_believed_loss"] / g["mean_cost"]["independent"]
    ok = v["independent"] >= 1 and v["guarded"] == 0 and under >= 0.10
    return ("CONFIRMED" if ok else "REFUTED"), \
        f"violations independent {v['independent']}/{g['components']}, guarded {v['guarded']}; independent planner underestimates its realized loss by {under:.1%}"


def h7(r):
    t = r["guard"]["tests"]["independent"]
    ok = t["p_holm"] < ALPHA and t["mean_diff"] > 0
    return ("CONFIRMED" if ok else "REFUTED"), f"independent - guarded: {t['mean_diff'] / 1e6:+.1f}M, p_holm {t['p_holm']:.2g}"


def h8(r):
    tests = r["accelerated"]["tests"]
    ok = [k for k in LIST_BASELINES if _better(tests, k)]
    return ("CONFIRMED" if len(ok) == len(LIST_BASELINES) else "REFUTED"), \
        f"accelerated timeline (-2 years): QAMP significantly cheaper than {len(ok)}/{len(LIST_BASELINES)} list baselines"


def h11(r):
    t = r["tight"]["tests"]["asap_fifo"]
    rel = t["mean_diff"] / r["tight"]["summary"]["qamp_stochastic"]["mean"]
    ok = t["p_holm"] < ALPHA and rel >= 0.10
    return ("CONFIRMED" if ok else "REFUTED"), f"8-quarter renewals, capacity 1: ASAP - QAMP {t['mean_diff'] / 1e6:+.1f}M ({rel:+.1%}), p_holm {t['p_holm']:.2g}"


def h12(r):
    e = r["explanations"]
    d, c = e["deterministic"], e["counterfactual"]
    ok = d["citation_validity"] == 1.0 and d["faithfulness"] >= 0.99 and c["consistency"] >= 0.95
    return ("CONFIRMED" if ok else "REFUTED"), (f"citation validity {d['citation_validity']:.3f}, faithfulness {d['faithfulness']:.3f} "
                                                f"({d['sentences']} sentences); counterfactual consistency {c['consistency']:.3f} ({c['cases']} cases)")


def h13(r):
    e = r.get("explanations", {})
    if "llm" not in e:
        return "PENDING DATA", "needs `python -m qamp explain-check --llm` with an API key"
    ret = e["llm"]["retained"]
    return ("CONFIRMED" if ret >= 0.95 else "REFUTED"), f"{ret:.3f} of {e['llm']['sentences']} rephrased sentences retained ({e['llm']['model']})"


def _pending(key):
    def f(r):
        if key not in r:
            return "PENDING DATA", "needs labelled inventories (docs/LABELLING.md) and verified source from the extraction notebook"
        return r[key]
    return f


HYPOTHESES = [
    Hypothesis("H1", "RQ2", "Timing-aware stochastic planning beats every list baseline.",
               "QAMP-stochastic has lower realized cost than each of the six list baselines (paired sign-flip test on the mean, Holm, p < 0.01).",
               "design claim of the paper", "main", h1),
    Hypothesis("H2", "RQ2", "Planning with a pessimistic execution time is more robust than stochastic planning.",
               "QAMP-pessimistic has lower realized cost than QAMP-stochastic (p < 0.01).",
               "authors' project-governance paper (pessimistic execution time most robust)", "main", h2),
    Hypothesis("H2b", "RQ2", "Among deterministic planners, a pessimistic margin beats the expected execution time.",
               "QAMP-pessimistic cheaper than QAMP-expected (p < 0.01).",
               "authors' project-governance paper", "main", h2b),
    Hypothesis("H3", "RQ2", "Ignoring renewal boundaries costs value (the decision-window effect).",
               "QAMP without windows (plans as if every quarter were a boundary) costs more than QAMP (p < 0.01).",
               "decision-window theory", "main", h3),
    Hypothesis("H4", "RQ2", "With renewals every quarter, timing-aware planning gives no advantage over ASAP.",
               "On period-1 calendars, QAMP and ASAP differ by < 0.1% or not significantly (p >= 0.05).",
               "authors' project-governance paper (alignment benefit disappears with refundable commitments)", "period1", h4),
    Hypothesis("H5", "RQ2", "Timing-aware planning closes most of the gap to perfect foresight.",
               "QAMP closes at least 50% of the cost gap between ASAP and the oracle.",
               "authors' project-governance paper (renewal-dated gates captured 83% of ideal value)", "main", h5),
    Hypothesis("H6", "RQ3", "Independent planning of bridged instances breaks its own protection claim; the guard prevents it.",
               "At least one mixed-state violation without the guard, none with it, and the independent planner underestimates its realized loss by at least 10%.",
               "authors' bridge composition result", "guard", h6),
    Hypothesis("H7", "RQ3", "Guarded planning is cheaper in realized cost than independent planning.",
               "Independent planning costs more than guarded planning (p < 0.01).",
               "design claim", "guard", h7),
    Hypothesis("H8", "RQ2", "H1 holds when the CRQC timeline is two years earlier.",
               "Same as H1 under shift_years = 2.", "robustness", "accelerated", h8),
    Hypothesis("H11", "RQ2", "Timing pays when commitments are long and capacity is tight.",
               "With 8-quarter renewals and one migration at a time per issuer, QAMP is at least 10% cheaper than ASAP (p < 0.01).",
               "decision-window theory (alignment matters for long, irreversible commitments); informed by the exploratory pilot grid",
               "tight", h11),
    Hypothesis("H12", "RQ4", "The system's own rationales are faithful to the facts they cite.",
               "Citation validity 1.0, faithfulness >= 0.99 and counterfactual consistency >= 0.95.",
               "design claim (verifiable by construction; reported as a property of the system)", "explanations", h12),
    Hypothesis("H13", "RQ4", "An LLM can rephrase rationales for auditors without losing grounding.",
               "At least 95% of LLM-rephrased sentences keep valid citations and pass the faithfulness check.",
               "design claim", "explanations", h13),
    Hypothesis("H9", "RQ1", "Rules-based discovery from ABI and verified source finds the signature surfaces.",
               "Overall recall >= 0.90 against the adjudicated labels.", "design claim", "discovery", _pending("H9")),
    Hypothesis("H10", "RQ1", "A knowledge-grounded LLM classifier improves on rules alone.",
               "LLM F1 > rules F1 with no more than 5% of entries dropped for invalid citations.", "design claim", "discovery", _pending("H10")),
]


def evaluate_all(results: dict) -> list[dict]:
    out = []
    for h in HYPOTHESES:
        if h.experiment not in results and h.id not in ("H9", "H10", "H13"):
            out.append(dict(id=h.id, rq=h.rq, statement=h.statement, prediction=h.prediction, outcome="NOT RUN", evidence=""))
            continue
        outcome, ev = h.decide(results)
        out.append(dict(id=h.id, rq=h.rq, statement=h.statement, prediction=h.prediction,
                        source_of_prediction=h.source_of_prediction, outcome=outcome, evidence=ev))
    return out


def markdown(rows: list[dict], seeds_note: str) -> str:
    s = f"{seeds_note}\n\n| ID | RQ | Hypothesis | Prediction | Outcome | Evidence |\n|---|---|---|---|---|---|\n"
    s += "\n".join(f"| {r['id']} | {r['rq']} | {r['statement']} | {r['prediction']} | **{r['outcome']}** | {r['evidence']} |" for r in rows)
    return s + "\n"
