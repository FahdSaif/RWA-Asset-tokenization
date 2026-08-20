arca-prototype/
├── Cargo.toml                      # Rust workspace (node + runtime + pallets)
├── rust-toolchain.toml             # PIN the toolchain — saves you the Apple-Silicon pain
├── README.md
├── .gitignore                      # target/, node_modules/, build/, keys/, *.zkey
├── Dockerfile
├── docker-compose.yml              # node + AI service, for the reproducible artifact
├── Makefile                        # make build / make demo / make bench
│
├── node/                           # ── the running blockchain service
│   └── src/
│       ├── main.rs
│       ├── chain_spec.rs           # genesis: dev accounts, initial rules, ZK verif key
│       ├── service.rs
│       ├── rpc.rs
│       └── command.rs
│
├── runtime/                        # ── wires the pallets into one state machine
│   ├── build.rs
│   └── src/
│       └── lib.rs                  # construct_runtime!{...} — lists every pallet below
│
├── pallets/                        # ══ LAYER 3: Runtime Enforcement (your headline) ══
│   ├── transaction-validation/     # Transaction Validation Module — the transfer HOOK
│   │   ├── Cargo.toml
│   │   └── src/
│   │       ├── lib.rs              # intercepts every asset transfer pre-finalization
│   │       ├── mock.rs            # test runtime
│   │       ├── tests.rs           # incl. the raw-bypass rejection unit test
│   │       ├── benchmarking.rs    # feeds your latency numbers
│   │       └── weights.rs
│   ├── rule-registry/              # Compliance Rule Registry Module (predicates)
│   │   └── src/lib.rs
│   ├── audit-log/                  # Audit Log Module (append-only, tamper-evident)
│   │   └── src/lib.rs
│   ├── verification/               # ══ LAYER 2: ZKP verify + DID registry ══
│   │   └── src/lib.rs             # Groth16 verify (arkworks) against embedded vk
│   ├── governance/                 # ══ LAYER 4: Governance Module ══
│   │   └── src/lib.rs             # verifies signed CRR before a rule can activate
│   └── asset-registry/             # Token standard + Asset Registry (Layer 4)
│       └── src/lib.rs
│
├── circuits/                       # ══ LAYER 2: the ZK predicate (circom) ══
│   ├── src/
│   │   └── accreditation.circom    # ONE predicate: net_assets ≥ threshold
│   ├── scripts/
│   │   ├── compile.sh
│   │   ├── setup.sh               # powers-of-tau + groth16 setup
│   │   ├── prove.js               # snarkjs proof generation
│   │   └── verify.js
│   ├── build/                      # .r1cs, *_js/ (wasm), *.zkey  (gitignored)
│   └── export/
│       └── verification_key.json   # baked into pallets/verification + chain_spec
│
├── compliance-ai/                  # ══ LAYER 1: Compliance Intelligence (Python) ══
│   ├── requirements.txt
│   ├── src/arca_ai/
│   │   ├── graph.py               # your LangGraph flow: classify→route→agent→gate
│   │   ├── agents/
│   │   │   ├── eligibility.py     # Investor Eligibility Evaluation Agent
│   │   │   └── risk_scoring.py    # Transaction Risk Scoring Agent (SHAP explain)
│   │   ├── crr.py                 # CRR schema + signing + input commitment
│   │   ├── governance_gate.py     # the HITL / signature-verify step
│   │   └── config.py              # Groq / Mistral
│   ├── notebooks/
│   │   └── arca_demo.ipynb        # the grown-up version of your current notebook
│   └── tests/
│
├── offchain/                       # ── client that drives the chain
│   ├── submit_compliant.py         # normal app-path transfer (substrate-interface)
│   ├── submit_raw_bypass.py        # ★ raw extrinsic that skips the app layer
│   ├── register_rule.py            # push a governance-signed rule into the registry
│   └── keys/                       # dev keys (gitignored)
│
├── experiments/                    # ══ what becomes your evaluation section ══
│   ├── bypass_experiment.py        # ★ runs both paths, asserts BOTH rejected
│   ├── bench_latency.py            # validation latency
│   ├── bench_zkp.py                # prove/verify time + proof size
│   └── plots.py
│
├── results/
│   ├── raw/                        # CSVs from the benchmarks
│   ├── figures/                    # ← generate the REAL Fig 2/3/4 here
│   └── tables/                     # component-mapping + measurement tables
│
└── docs/
    ├── component-mapping.md        # pallet → paper module (your Table)
    ├── architecture.md
    └── reproduce.md                # one-command repro for reviewers
