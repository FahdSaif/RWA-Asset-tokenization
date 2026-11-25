"""Exposure model: the expected loss of an anchor given when its migration takes effect and when a CRQC arrives.

For an anchor i whose migration takes effect at quarter E (``None``: never within the horizon H) and a CRQC
arriving at quarter T:

  forgeable window    W = max(0, min(E, H) - T) quarters: the old key still controls the anchor after T.
  forgery loss        V_i * w_i * (1 - exp(-h * W / 4))
                      V_i value at risk (market caps of controlled tokens, USD)
                      w_i attack weight: 1 for an exposed (or unobserved) public key; ``hidden_weight`` for a key
                          whose public key is not yet revealed (exposed only in an on-spend window)
                      h   yearly hazard that a capable adversary exploits an open window
  trust-now-forge-later  for anchors that sign retained compliance records (retention R from the KB):
                      records signed in [0, E) stay evidence until t + R; those with t > T - R are repudiable once
                      the CRQC exists. Repudiable record-quarters  M = max(0, min(E, H) - max(0, T - R)) if T < H.
                      loss  rho * V_i * M / 4   (rho: evidentiary value per USD-year of records, small)

All parameters are explicit and recorded; defaults are ASSUMPTIONS for sensitivity analysis, not estimates.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from . import config


@dataclass(frozen=True)
class LossParams:
    hazard_per_year: float = 1.0
    hidden_weight: float = 0.25
    rho_records: float = 0.002
    horizon: int = config.HORIZON_QUARTERS

    def as_dict(self) -> dict:
        return asdict(self)


def attack_weight(anchor, p: LossParams) -> float:
    if anchor.key_exposed is False:
        return p.hidden_weight
    return 1.0   # exposed, or not observed (conservative; KB rule EXP-KEY-UNKNOWN)


def anchor_loss(anchor, effective_q: float | None, crqc_q: float, retention_years: float, p: LossParams) -> float:
    if not anchor.quantum_vulnerable:
        return 0.0
    H = p.horizon
    E = H if effective_q is None else min(effective_q, H)
    if crqc_q >= H:
        return 0.0
    W = max(0.0, E - crqc_q)
    loss = anchor.value_usd * attack_weight(anchor, p) * (1 - math.exp(-p.hazard_per_year * W / 4))
    if anchor.signs_records and retention_years > 0:
        M = max(0.0, E - max(0.0, crqc_q - 4 * retention_years))
        loss += p.rho_records * anchor.value_usd * M / 4
    return loss


def anchor_loss_vec(anchor, effective_q: float | None, crqc_q, retention_years: float, p: LossParams):
    """Vectorised ``anchor_loss`` over an array of CRQC arrival quarters (same formula)."""
    import numpy as np
    T = np.asarray(crqc_q, dtype=float)
    if not anchor.quantum_vulnerable:
        return np.zeros_like(T)
    H = p.horizon
    E = H if effective_q is None else min(effective_q, H)
    live = T < H
    W = np.maximum(0.0, E - T)
    loss = anchor.value_usd * attack_weight(anchor, p) * (1 - np.exp(-p.hazard_per_year * W / 4))
    if anchor.signs_records and retention_years > 0:
        M = np.maximum(0.0, E - np.maximum(0.0, T - 4 * retention_years))
        loss = loss + p.rho_records * anchor.value_usd * M / 4
    return np.where(live, loss, 0.0)


def effective_quarter(anchor, start_q: int | None, delta: int = 0, margin: int = 0) -> int | None:
    """Quarter at which a migration started at ``start_q`` takes effect: completion (planned time + deviation +
    timelock, at least one quarter) rounded up to the anchor's next renewal boundary."""
    if start_q is None:
        return None
    duration = max(1, anchor.migration_quarters + delta + margin) + anchor.timelock_quarters
    return anchor.calendar.next_boundary(start_q + duration)
