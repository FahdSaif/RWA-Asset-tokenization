"""
Layer 3 — On-chain Runtime Enforcement demo bridge.

Deploys the compiled ComplianceRegistry + ComplianceToken contracts
(see contracts/*.sol, compiled via `node scripts/compile_contracts.js`)
onto a fully local, in-memory EVM (web3.py's `EthereumTesterProvider` —
a real EVM implementation, not a mock; no network access required, so
this runs identically in CI). This gives the paper's "non-bypassable"
enforcement claim (Sec. VI-B, Threat Class I) a literal on-chain
demonstration: calling `transfer()` on a real deployed contract from a
non-allow-listed account reverts, regardless of which "application" (if
any) constructed the transaction.

The Python RuleRegistryModule / TransactionValidationModule
(rule_registry.py, transaction_validator.py) remain the primary,
richer prototype — this module is the corresponding on-chain artifact
for the specific "allow-listed transfer" predicate, which is the one
compliance check that genuinely belongs at the EVM level rather than
being evaluated off-chain and merely attested to on-chain.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Optional, Tuple

from web3 import Web3
from web3.providers.eth_tester import EthereumTesterProvider

_BUILD_PATH = pathlib.Path(__file__).resolve().parent / "contracts" / "build" / "contracts.json"


def _load_artifacts() -> Dict[str, Any]:
    if not _BUILD_PATH.exists():
        raise FileNotFoundError(
            f"{_BUILD_PATH} not found. Run `node scripts/compile_contracts.js` "
            "(from the repo root, after `npm install`) to compile the contracts first."
        )
    with open(_BUILD_PATH) as f:
        return json.load(f)


class LocalEVM:
    """A local, in-memory Ethereum-compatible chain plus the deployed ARCA
    demo contracts. Every account is pre-funded test ether from eth-tester,
    so no faucet / real network is involved."""

    def __init__(self, owner_index: int = 0, initial_supply: int = 1_000_000 * 10**18):
        self.w3 = Web3(EthereumTesterProvider())
        self.accounts = self.w3.eth.accounts
        self.owner = self.accounts[owner_index]
        self.artifacts = _load_artifacts()

        self.registry = self._deploy("ComplianceRegistry", args=[self.owner])
        self.token = self._deploy(
            "ComplianceToken",
            args=["ARCA Demo Real Estate Token", "ARCA-RE", initial_supply, self.registry.address, self.owner],
        )

    def _deploy(self, contract_name: str, args: list):
        artifact = self.artifacts[contract_name]
        contract = self.w3.eth.contract(abi=artifact["abi"], bytecode=artifact["bytecode"])
        tx_hash = contract.constructor(*args).transact({"from": self.owner})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return self.w3.eth.contract(address=receipt.contractAddress, abi=artifact["abi"])

    # -- governance-side operations (mirror RuleRegistryModule.apply_update) --
    def set_allowed(self, account: str, status: bool) -> None:
        tx_hash = self.registry.functions.setAllowed(account, status).transact({"from": self.owner})
        self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def set_flagged(self, account: str, status: bool) -> None:
        tx_hash = self.registry.functions.setFlagged(account, status).transact({"from": self.owner})
        self.w3.eth.wait_for_transaction_receipt(tx_hash)

    def is_compliant(self, account: str) -> bool:
        return self.registry.functions.isCompliant(account).call()

    # -- transaction submission: this is the "raw transaction" path a --
    # -- bypass attempt (Threat Class I) would use directly. --
    def transfer(self, sender: str, to: str, amount: int) -> Tuple[bool, Optional[str]]:
        """Attempts token.transfer(to, amount) from `sender`. Returns
        (success, revert_reason_or_None). A failure here is the EVM itself
        refusing the state transition — there is no way to construct a
        transaction that reaches a different code path."""
        try:
            tx_hash = self.token.functions.transfer(to, amount).transact({"from": sender})
            self.w3.eth.wait_for_transaction_receipt(tx_hash)
            return True, None
        except Exception as exc:  # eth-tester surfaces reverts as exceptions
            return False, str(exc)

    def balance_of(self, account: str) -> int:
        return self.token.functions.balanceOf(account).call()

    def transfer_events(self) -> list:
        return self.token.events.Transfer().get_logs(from_block=0)
