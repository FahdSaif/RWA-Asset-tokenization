# Safe multisig wallets: background and why QAMP reads them

**In short:** many token issuers protect their admin keys with a Safe multisig wallet. QAMP does not use a Safe
itself. It only **reads** each issuer's Safe settings from the chain, because a Safe changes how a quantum attack on
those keys would work and how the keys can be migrated.

## What a Safe is

Safe (formerly called Gnosis Safe) is the most widely used multisig wallet on Ethereum. It is a smart contract,
not a single key:

- It stores a list of **owners** (signers) and a **threshold**: the number of owners who must sign before the Safe
  can do anything. For example, 2-of-4 means any 2 of the 4 owners must sign.
- Owners can be ordinary wallets (EOAs), other smart contracts, or passkeys.
- The owners can add or remove owners and change the threshold, but only through a Safe transaction that itself meets
  the threshold.

Official documentation: [Safe smart account concepts](https://docs.safe.global/advanced/smart-account-concepts).

## Why token issuers use one

A token's most powerful rights (upgrade the code, mint, burn, pause, change roles) are given to an address. If that
address is a single wallet, one stolen key is enough to abuse those rights. With a Safe, an attacker needs several
keys at once, and the owners can swap a lost or suspect key without moving the rights elsewhere.

## Why it matters for quantum risk

Ethereum wallets sign with ECDSA. Once a wallet has sent a transaction, its public key can be read from the chain. A
large enough quantum computer could work out the private key from that public key.

- **A single wallet** with an exposed key falls with one key.
- **A Safe** falls only if the attacker can forge at least the threshold number of owner signatures. So QAMP counts
  how many owners have exposed keys and compares that with the threshold.
- **Migration is different too.** A Safe can swap its owners for new, quantum-safe ones without changing its own
  address, so the token's rights stay where they are. A single wallet has to hand its rights to a new address on every
  token it controls. QAMP gives the two cases different migration times and costs.

## How QAMP reads a Safe

All reads are public and read-only. Nothing is signed or sent. Code: `qamp.extraction.Observer.observe_into`.

| What | How |
|---|---|
| Is the controller a Safe? | It answers `getThreshold()` and `getOwners()` |
| Threshold and owners | the values those two functions return |
| Is each owner's key exposed? | the owner is an ordinary wallet that has sent at least one transaction |
| When the owners changed | events `AddedOwner`, `RemovedOwner`, `ChangedThreshold` (used for renewal calendars) |

Owners are followed one step only: an owner that is itself a Safe is recorded, but its own owners are not read.

## What the data show

Q1 and Q1b found 108 controlling addresses behind the 100 sampled tokens; 9 of them are Safes.

| Safe (start of address) | Threshold | Tokens controlled | Owners with an exposed key |
|---|---|---|---|
| `0x49754062` | 2 of 3 | 20 | 2 |
| `0x8768cda7` | 2 of 4 | 20 (Backed pauser) | 3 |
| `0x2e55b738` | 1 of 9 | 2 | 8 |
| `0x1a694a09` | 4 of 7 | 1 | 6 |
| `0x71a4d411` | 4 of 7 | 1 | 6 |
| `0x7607c089` | 3 of 6 | 1 | 3 |
| `0xcf355ad3` | 3 of 7 | 1 | 7 |
| `0xb10b260f` | 3 of 4 | 1 | 3 |
| `0xca3144aa` | 2 of 3 | 1 | not known (owners not read) |

What stands out:

1. **In 8 of the 9 Safes, the owners with exposed keys already meet the threshold.** A multisig slows a quantum attacker
   down only if fewer exposed keys than the threshold exist. Here it would not.
2. **A 1-of-9 Safe** acts on one signature, so it is no stronger than its weakest owner.
3. **Backed's keys overlap.** The pauser Safe (2 of 4) has as one of its owners the same wallet that holds the burner
   role, with 40,785 transactions. Backed's minter is another single wallet, with 4,477 transactions. So the rights to
   mint and burn sit with single wallets whose keys are exposed, not with the Safe.

## Limits

- Owners that are contracts are not followed further, and Safe modules and guards (add-ons that can bypass or check
  signatures) are not read.
- "Exposed" means "has sent a transaction". A wallet that has only received funds is counted as not exposed.
- Addresses are public on-chain data; this page names no people or companies behind them.
