"""
Generates data/synthetic_transactions.csv — a labeled dataset for
training the Transaction Risk Scoring Agent (paper Sec. V-C).

WHY SYNTHETIC: real account-level AML transaction data is confidential
(bank secrecy law, GDPR/Privacy Act obligations, suspicious-activity
report confidentiality) and cannot legally be redistributed in a public
GitHub repository. This is exactly the empirical gap the paper itself
flags in Sec. VII ("Directions for Future Research") — a real deployment
would train this agent on an institution's own transaction history under
appropriate data-governance controls, not on a public CSV.

DESIGN: rather than hand-tuning a single noisy logistic formula (which
either collapses to an easily-memorized rule or to pure noise), each
transaction is drawn from one of four latent behavioural archetypes,
loosely modelled on publicly-documented FATF / Egmont Group red-flag
typologies:

  - "normal"              : ordinary, low-risk activity (~85% of rows)
  - "structuring"         : amounts clustered just under a reporting
                             threshold, elevated velocity (placement)
  - "high_risk_corridor"  : cross-border flows concentrated in
                             FATF grey/black-list jurisdictions
  - "rapid_layering"      : high transaction velocity through many new
                             counterparties in a short window

The *label* is then a probabilistic function of archetype (not a
deterministic rule), so a model has to learn the feature distributions
rather than memorize a formula — while still leaving genuine, learnable
signal, unlike a pure-noise target.

Run: python scripts/generate_synthetic_transactions.py
"""
from __future__ import annotations

import pathlib

import numpy as np
import pandas as pd

RNG_SEED = 42
N_ROWS = 8000
OUT_PATH = pathlib.Path(__file__).resolve().parents[1] / "data" / "synthetic_transactions.csv"

ARCHETYPES = ["normal", "structuring", "high_risk_corridor", "rapid_layering"]
ARCHETYPE_PROBS = [0.85, 0.06, 0.05, 0.04]
LABEL_PROB_BY_ARCHETYPE = {
    "normal": 0.025,
    "structuring": 0.72,
    "high_risk_corridor": 0.80,
    "rapid_layering": 0.75,
}


def generate(n_rows: int = N_ROWS, seed: int = RNG_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    archetype = rng.choice(ARCHETYPES, size=n_rows, p=ARCHETYPE_PROBS)

    n = n_rows
    amount = np.zeros(n)
    jurisdiction_tier = np.zeros(n, dtype=int)
    tx_velocity_24h = np.zeros(n, dtype=int)
    unique_counterparties_7d = np.zeros(n, dtype=int)
    account_age_days = np.zeros(n, dtype=int)
    cross_border = np.zeros(n, dtype=int)
    is_new_counterparty = np.zeros(n, dtype=int)
    is_round_number = np.zeros(n)

    hour_of_day = rng.integers(0, 24, size=n)

    for arche in ARCHETYPES:
        mask = archetype == arche
        cnt = int(mask.sum())
        if cnt == 0:
            continue

        if arche == "normal":
            amt = np.clip(rng.lognormal(8.2, 1.3, cnt), 10, 2_000_000)
            jt = rng.choice([0, 1, 2], size=cnt, p=[0.93, 0.06, 0.01])
            vel = rng.poisson(1.4, cnt)
            uniq = rng.poisson(1.8, cnt)
            age = np.clip(rng.exponential(500, cnt) + 30, 1, 6000).astype(int)
            xb = rng.binomial(1, 0.15, cnt)
            newcp = rng.binomial(1, 0.10, cnt)
            round_flag = rng.binomial(1, 0.03, cnt).astype(float)

        elif arche == "structuring":
            amt = rng.uniform(8200, 9950, cnt)
            round_ix = rng.random(cnt) < 0.55
            n_round = int(round_ix.sum())
            if n_round:
                amt[round_ix] = rng.choice([8500, 9000, 9200, 9500, 9800], size=n_round)
            jt = rng.choice([0, 1, 2], size=cnt, p=[0.55, 0.35, 0.10])
            vel = rng.poisson(4.5, cnt) + 2
            uniq = rng.poisson(1.5, cnt) + 1
            age = np.clip(rng.exponential(200, cnt) + 5, 1, 3000).astype(int)
            xb = rng.binomial(1, 0.40, cnt)
            newcp = rng.binomial(1, 0.30, cnt)
            round_flag = round_ix.astype(float)

        elif arche == "high_risk_corridor":
            amt = np.clip(rng.lognormal(9.5, 1.1, cnt), 500, 3_000_000)
            jt = rng.choice([1, 2], size=cnt, p=[0.45, 0.55])
            vel = rng.poisson(2.2, cnt)
            uniq = rng.poisson(2.5, cnt)
            age = np.clip(rng.exponential(350, cnt) + 10, 1, 5000).astype(int)
            xb = np.ones(cnt, dtype=int)
            newcp = rng.binomial(1, 0.35, cnt)
            round_flag = rng.binomial(1, 0.15, cnt).astype(float)

        else:  # rapid_layering
            amt = np.clip(rng.lognormal(8.8, 1.2, cnt), 200, 1_500_000)
            jt = rng.choice([0, 1, 2], size=cnt, p=[0.7, 0.25, 0.05])
            vel = rng.poisson(9.0, cnt) + 3
            uniq = rng.poisson(8.0, cnt) + 3
            age = np.clip(rng.exponential(60, cnt) + 1, 1, 2000).astype(int)
            xb = rng.binomial(1, 0.5, cnt)
            newcp = rng.binomial(1, 0.70, cnt)
            round_flag = rng.binomial(1, 0.20, cnt).astype(float)

        amount[mask] = np.round(amt, 2)
        jurisdiction_tier[mask] = jt
        tx_velocity_24h[mask] = vel
        unique_counterparties_7d[mask] = uniq
        account_age_days[mask] = age
        cross_border[mask] = xb
        is_new_counterparty[mask] = newcp
        is_round_number[mask] = round_flag

    threshold = 10_000
    structuring_proximity = np.where(
        (amount < threshold) & (amount > threshold * 0.75),
        1.0 - (threshold - amount) / (threshold * 0.25),
        0.0,
    )

    label_prob = np.array([LABEL_PROB_BY_ARCHETYPE[a] for a in archetype])
    is_suspicious = (rng.random(n) < label_prob).astype(int)
    label_noise = rng.random(n) < 0.015  # 1.5% random label flips
    is_suspicious = np.where(label_noise, 1 - is_suspicious, is_suspicious)

    df = pd.DataFrame(
        {
            "amount": amount,
            "jurisdiction_tier": jurisdiction_tier,
            "tx_velocity_24h": tx_velocity_24h,
            "unique_counterparties_7d": unique_counterparties_7d,
            "account_age_days": account_age_days,
            "cross_border": cross_border,
            "is_new_counterparty": is_new_counterparty,
            "hour_of_day": hour_of_day,
            "structuring_proximity": np.round(structuring_proximity, 4),
            "is_round_number": is_round_number,
            "archetype": archetype,  # retained for analysis/notebooks; NOT a model feature
            "is_suspicious": is_suspicious,
        }
    )
    return df


if __name__ == "__main__":
    df = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(df)} rows to {OUT_PATH}")
    print(df["is_suspicious"].value_counts(normalize=True))
    print(df.groupby("archetype")["is_suspicious"].mean())
