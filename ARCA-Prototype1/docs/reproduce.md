# Reproducing the results

Reviewers should be able to run this in one pass. On the Mac Studio (state the
exact chip/RAM in the paper):

```bash
# 0. deps + node/runtime template
./bootstrap.sh

# 1. build the node (first build is slow)
cargo build --release

# 2. pallet tests, including the bypass rejection test
cargo test -p pallet-transaction-validation

# 3. compile + set up the ZK circuit
cd circuits && npm run compile && npm run setup && cd ..

# 4. start the node
./target/release/<node-binary> --dev &

# 5. seed a governance-admitted rule
python offchain/register_rule.py

# 6. the headline result
python experiments/bypass_experiment.py

# 7. numbers + figures
python experiments/bench_latency.py
python experiments/bench_zkp.py
python experiments/plots.py
```

All timings reported in the paper were taken bare-metal on a single fixed machine;
do not benchmark inside Docker or on shared cloud hardware.
