**baseline (faulty) build**

| Path | Entry point | Mediated by the Gateway | Evidence |
|---|---|---|---|
| P1 | user transaction | yes | ok |
| P2 | VM / contract call | **NO** | ok |
| P3 | system reward hook | **NO** | ok |
| P4 | bridge-inbound mint | **NO** | ok |
| P5 | forced transfer (quorum-authorised) | **NO** | ok |
| P6 | runtime upgrade to a permissive gateway | **NO** | ok |
| P7 | state restore / migration | **NO** | ok |

**hardened build**

| Path | Entry point | Mediated by the Gateway | Evidence |
|---|---|---|---|
| P1 | user transaction | yes | ok |
| P2 | VM / contract call | yes | ok |
| P3 | system reward hook | yes | ok |
| P4 | bridge-inbound mint | yes | ok |
| P5 | forced transfer (quorum-authorised) | yes | ok |
| P6 | runtime upgrade to a permissive gateway | yes | UpgradeRejected |
| P7 | state restore / migration | **NO** | ok |

