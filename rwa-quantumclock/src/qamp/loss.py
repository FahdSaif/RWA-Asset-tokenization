"""Loss model: what it costs if an anchor is still on the old key when a quantum computer arrives.

Forgery loss = value x attack weight x (1 - exp(-hazard x years left open)).
Records loss = small share of value x years of signed records that can be disputed later.
All parameters are assumptions and are varied in the sensitivity analysis."""
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
    return 1.0   # exposed or unknown: assume exposed


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
    """Same as anchor_loss, for many arrival dates at once."""
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
    """Quarter when a migration takes effect: finish date, moved up to the next renewal date."""
    if start_q is None:
        return None
    duration = max(1, anchor.migration_quarters + delta + margin) + anchor.timelock_quarters
    return anchor.calendar.next_boundary(start_q + duration)
