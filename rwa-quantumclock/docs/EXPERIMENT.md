# The experiment at a glance

QAMP plans when the keys behind tokenised real-world assets should move to quantum-safe cryptography.
This page shows what was done, in what order, and where each output is in this folder.

```mermaid
flowchart TD
    subgraph S1["1 · Fix the sample (before any data)"]
        A["Etherscan 'Real World Assets' list<br/>seen 2026-11-26, sorted by market cap"]
        B["Rule: 25 census tokens + first 75 new<br/>data/sample_tokens.txt"]
        T1(["tag: quantumclock-q1-plan"])
        A --> B --> T1
    end

    subgraph S2["2 · Collect on-chain data (Colab, read-only)"]
        C["Q1 notebook, Etherscan API<br/>100 tokens"]
        C1["Source code and functions"]
        C2["Controllers: admins, owners,<br/>role members, Safe signers"]
        C3["Governance events<br/>(key and signer changes)"]
        C4["Deployed contract code"]
        C5["Same address on 12 other chains"]
        D["data/q1_raw.json<br/>+ SHA-256 in data/q1_summary.json"]
        C --> C1 & C2 & C3 & C4 & C5 --> D
    end

    subgraph S3["3 · Interpret the data (python -m qamp facts)"]
        E1["Key exposure"]
        E2["Renewal calendars<br/>and issuer capacity"]
        E3["Copies on other chains"]
        E4["Objective labels<br/>from contract code"]
    end

    subgraph S4["4 · QAMP expert system"]
        F1["Discovery: which signatures<br/>each contract trusts (CBOM)"]
        F2["Knowledge base: NIST, G7,<br/>FATF, EU AML, SEC rules"]
        F3["Scenarios: when a quantum<br/>computer may arrive (GRI survey)"]
        F4["Planner: start date per key,<br/>inside its renewal window"]
        F5["Guard: checks bridged chains<br/>during the migration"]
        F6["Explanations: every sentence<br/>cites its source"]
        F1 --> F4
        F2 --> F4
        F3 --> F4
        F4 --> F5 --> F6
        F5 -. "unsafe: plan again" .-> F4
    end

    subgraph S5["5 · Evaluate (pre-registered)"]
        G1["Compare with 6 simple policies<br/>and a perfect-foresight oracle"]
        G2["Hypotheses H1-H13<br/>decided once on held-out seeds"]
        T2(["tag: quantumclock-v1.0-frozen"])
        G3["results/held_out/"]
        T2 --> G1 --> G2 --> G3
    end

    T1 --> C
    D --> E1 & E2 & E3 & E4
    E1 & E2 & E3 --> F4
    E4 --> F1
    F6 --> G1
```

## Steps and where to find them

| Step | What happens | Output |
|---|---|---|
| 1. Sample | 100 tokens chosen by a fixed rule and recorded before any data were collected | `data/sample_tokens.txt`, `data/etherscan_rwa_snapshot_2026-11-26.txt` |
| 2. Collection | The Colab notebook reads each token from Etherscan. It only reads; it writes nothing on-chain | `notebooks/Q1_fetch_anchor_facts.ipynb`, `data/q1_raw.json`, `data/q1_summary.json` |
| 3. Interpretation | Raw data become model inputs: exposed keys, renewal calendars, capacity, chain copies, labels | `data/anchor_facts.json`, `data/labels_bytecode.csv`, `results/observed/` |
| 4. Expert system | Inventory, rules, scenarios, planning, bridge check, cited explanations | `src/qamp/`, `kb/` |
| 5. Evaluation | QAMP against simple policies; hypotheses decided once on unseen seeds | `results/held_out/` (after freezing) |

## Order of events (git tags)

| Tag | Meaning |
|---|---|
| `quantumclock-v0.1.1` | First prototype on the 25-token census |
| `quantumclock-v0.2.1` | On-chain data collection and explanation checks added |
| `quantumclock-q1-plan` | 100-token sample fixed, before any data were collected |
| `quantumclock-v1.0-frozen` | Code and hypotheses frozen, before the held-out run (planned) |

Data source: Etherscan.io (label list and API).
