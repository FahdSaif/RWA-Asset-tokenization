.PHONY: bootstrap build test demo bench bypass fmt clean

bootstrap:      ## fetch node/runtime template + install python/node deps
	./bootstrap.sh

build:          ## release build of the node
	cargo build --release

test:           ## pallet unit tests (incl. the bypass rejection test)
	cargo test -p pallet-transaction-validation

fmt:
	cargo fmt --all

demo:           ## end-to-end: rule registration -> proposal -> gate -> enforce
	python offchain/register_rule.py
	python compliance-ai/src/arca_ai/graph.py --demo

bypass:         ## THE headline result: app-path vs raw-extrinsic, both rejected
	python experiments/bypass_experiment.py

bench:          ## latency + zk overhead -> results/raw
	python experiments/bench_latency.py
	python experiments/bench_zkp.py

clean:
	cargo clean
