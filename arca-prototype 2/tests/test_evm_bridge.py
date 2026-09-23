import pathlib

import pytest

_BUILD_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "arca" / "layer3_runtime" / "contracts" / "build" / "contracts.json"
)

pytestmark = pytest.mark.skipif(
    not _BUILD_PATH.exists(),
    reason="Contracts not compiled — run `npm install && node scripts/compile_contracts.js` first.",
)


def test_deploy_and_compliant_transfer():
    from arca.layer3_runtime.evm_bridge import LocalEVM

    evm = LocalEVM()
    owner, alice = evm.owner, evm.accounts[1]
    evm.set_allowed(owner, True)
    evm.set_allowed(alice, True)

    ok, err = evm.transfer(owner, alice, 1000)
    assert ok is True
    assert evm.balance_of(alice) == 1000


def test_transfer_to_non_allowlisted_address_reverts():
    from arca.layer3_runtime.evm_bridge import LocalEVM

    evm = LocalEVM()
    owner, mallory = evm.owner, evm.accounts[3]
    evm.set_allowed(owner, True)
    # mallory deliberately left un-allow-listed

    ok, err = evm.transfer(owner, mallory, 500)
    assert ok is False
    assert "receiver not compliant" in (err or "")
    assert evm.balance_of(mallory) == 0


def test_flagged_address_blocked_even_if_allowlisted():
    from arca.layer3_runtime.evm_bridge import LocalEVM

    evm = LocalEVM()
    owner, alice = evm.owner, evm.accounts[1]
    evm.set_allowed(owner, True)
    evm.set_allowed(alice, True)
    evm.set_flagged(alice, True)

    ok, err = evm.transfer(owner, alice, 100)
    assert ok is False
    assert "receiver not compliant" in (err or "")


def test_only_owner_can_update_registry():
    from arca.layer3_runtime.evm_bridge import LocalEVM

    evm = LocalEVM()
    not_owner = evm.accounts[2]
    with pytest.raises(Exception):
        evm.registry.functions.setAllowed(not_owner, True).transact({"from": not_owner})
