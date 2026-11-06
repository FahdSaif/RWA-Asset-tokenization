"""Ledger with a single balance-mutation primitive guarded by a Gateway approval ("narrow waist")."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .crypto import digest


class MediationError(Exception):
    """A state transition reached the ledger without a valid Gateway approval."""


@dataclass(frozen=True)
class Transfer:
    asset: str
    src: str
    dst: str
    amount: int
    memo: str = ""
    origin: str = "user"

    def digest(self) -> str:
        return digest([self.asset, self.src, self.dst, self.amount, self.memo, self.origin])


@dataclass(frozen=True)
class Approval:
    trail_index: int
    mac: str


class Ledger:
    def __init__(self) -> None:
        self._bal: dict[tuple[str, str], int] = {}
        self._verify: Callable[[Transfer, Approval | None], bool] = lambda tx, a: False

    def set_verifier(self, f: Callable[[Transfer, Approval | None], bool]) -> None:
        self._verify = f

    def credit_genesis(self, asset: str, acct: str, amount: int) -> None:
        self._bal[(asset, acct)] = self._bal.get((asset, acct), 0) + amount

    def balance(self, asset: str, acct: str) -> int:
        return self._bal.get((asset, acct), 0)

    def apply(self, tx: Transfer, approval: Approval | None) -> None:
        if not self._verify(tx, approval):
            raise MediationError(f"no valid Gateway approval for {tx.asset}:{tx.src}->{tx.dst}")
        self._move(tx)

    def raw_move(self, tx: Transfer) -> None:
        """The storage primitive. Mediation holds iff no reachable entry point calls this unguarded."""
        self._move(tx)

    def _move(self, tx: Transfer) -> None:
        if self.balance(tx.asset, tx.src) < tx.amount:
            raise ValueError("insufficient balance")
        self._bal[(tx.asset, tx.src)] -= tx.amount
        self._bal[(tx.asset, tx.dst)] = self.balance(tx.asset, tx.dst) + tx.amount

    def snapshot(self) -> dict:
        return dict(self._bal)

    def restore(self, snap: dict) -> None:
        self._bal = dict(snap)
