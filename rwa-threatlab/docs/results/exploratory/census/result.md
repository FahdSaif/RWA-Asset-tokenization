25 contracts: source verified 25; proxies 21; with at least one read error 0.

**Upgrade control among proxies**

| Type | Count |
|---|---|
| multisig | 10 |
| not_readable | 10 |
| timelock | 1 |

**Owner control (owner() or defaultAdmin())**

| Type | Count |
|---|---|
| no_owner_or_default_admin | 10 |
| multisig | 9 |
| none | 3 |
| eoa | 2 |
| timelock | 1 |

**Function-name categories present (count of contracts)**

| Category | Count |
|---|---|
| pause | 20 |
| freeze_blacklist | 11 |
| forced_transfer_recovery | 3 |
| upgrade | 20 |
| mint_burn | 23 |

| # | Name | Verified | Proxy | Upgrade control | Owner control | pause | freeze/blacklist | forced transfer/recovery | mint/burn | upgrade |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | TokenProxy | yes | yes | multisig 4-of-7 via contract | no_owner_or_default_admin | x | x |  | x | x |
| 2 | ERC1967Proxy | yes | yes | not_readable | none | x |  |  | x | x |
| 3 | ERC1967Proxy | yes | yes | not_readable | eoa | x |  | x | x | x |
| 4 | Tranche | yes | no | no_proxy_detected | no_owner_or_default_admin |  |  |  | x |  |
| 5 | ERC1967Proxy | yes | yes | not_readable | no_owner_or_default_admin |  |  |  | x | x |
| 6 | ERC1967Proxy | yes | yes | not_readable | none | x |  |  | x | x |
| 7 | BackedTokenProxy | yes | yes | multisig 2-of-3 via contract | multisig 2-of-3 | x | x |  | x | x |
| 8 | BackedTokenProxy | yes | yes | multisig 2-of-3 via contract | multisig 2-of-3 | x | x |  | x | x |
| 9 | ERC1967Proxy | yes | yes | not_readable | no_owner_or_default_admin | x |  |  | x | x |
| 10 | BackedTokenProxy | yes | yes | multisig 2-of-3 via contract | multisig 2-of-3 | x | x |  | x | x |
| 11 | BoringVault | yes | no | no_proxy_detected | timelock (172800 s) |  |  |  |  |  |
| 12 | PProxy | yes | yes | not_readable | no_owner_or_default_admin | x |  |  | x | x |
| 13 | ERC1967Proxy | yes | yes | not_readable | no_owner_or_default_admin | x | x | x | x | x |
| 14 | BackedTokenProxy | yes | yes | multisig 2-of-3 via contract | multisig 2-of-3 | x | x |  | x | x |
| 15 | BackedTokenProxy | yes | yes | multisig 2-of-3 via contract | multisig 2-of-3 | x | x |  | x | x |
| 16 | TokenProxy | yes | yes | timelock (7200 s) via contract | no_owner_or_default_admin | x |  |  | x | x |
| 17 | BackedTokenProxy | yes | yes | multisig 2-of-3 via contract | multisig 2-of-3 | x | x |  | x | x |
| 18 | BackedTokenProxy | yes | yes | multisig 2-of-3 via contract | multisig 2-of-3 | x | x |  | x | x |
| 19 | ERC1967Proxy | yes | yes | not_readable | none | x |  |  | x | x |
| 20 | BeaconProxy | yes | yes | not_readable | no_owner_or_default_admin | x |  |  | x |  |
| 21 | ERC1967Proxy | yes | yes | not_readable | eoa | x |  | x | x | x |
| 22 | BackedTokenProxy | yes | yes | multisig 2-of-3 via contract | multisig 2-of-3 | x | x |  | x | x |
| 23 | TransparentUpgradeableProxy | yes | yes | multisig 2-of-3 via contract | no_owner_or_default_admin |  |  |  | x | x |
| 24 | USDKG | yes | no | no_proxy_detected | multisig 3-of-7 | x | x |  |  |  |
| 25 | Tranche | yes | no | no_proxy_detected | no_owner_or_default_admin |  |  |  | x |  |
