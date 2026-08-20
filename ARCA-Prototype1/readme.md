ARCA — Reference Prototype

A working slice of the AI-Assisted Runtime Compliance Architecture (ARCA) for tokenized real-world assets. The paper describes the full four-layer design; this repository implements the part of it that is worth arguing about, namely that compliance can be enforced below the application layer, where it cannot be routed around, and that a probabilistic AI recommendation can be turned into a deterministic, enforceable rule without letting the model decide anything on its own.

This is a research prototype, not a product. It exists to make three claims falsifiable:

A transfer that fails compliance is rejected inside the runtime, regardless of how it is submitted — through the intended client or as a hand-built raw extrinsic that ignores the client entirely.
An AI-generated rule change has no effect until a governance step has verified its signature and admitted it to the rule registry.
The zero-knowledge overhead this design assumes is measurable on commodity hardware, not hypothetical.

Everything else in the paper (multi-jurisdiction rule sets, cross-chain, the full agent suite) is deliberately out of scope here. See "What is stubbed" below before you file a bug about it.

Layout

The directory tree mirrors the paper's layers so the mapping is legible:

pallets/ — Layer 3 (runtime enforcement) plus the Layer 2/4 pallets it depends on. transaction-validation is the important one; the rest support it.
circuits/ — the single ZK predicate (accreditation threshold), in circom.
compliance-ai/ — Layer 1. The LangGraph agent that proposes actions and the governance gate that refuses to let them through unsigned.
offchain/ — the clients that drive the chain, including the raw-bypass client.
experiments/ — the scripts that produce the numbers and the bypass result.
results/ — where those numbers and the paper figures are generated.

A component-to-paper-module table lives in docs/component-mapping.md.

Building

You need a recent Rust toolchain (pinned in rust-toolchain.toml — don't override it, the version matters), Node 18+ for the circuits, and Python 3.11+ for the AI and experiment layers.

# system deps (macOS / Apple Silicon)
brew install cmake protobuf llvm

rustup target add wasm32-unknown-unknown
cargo build --release        # first build is slow; this is normal, not broken

On Apple Silicon the node builds natively. If you hit a WASM-builder error against an older polkadot-sdk tag, the toolchain pin is usually the cause; failing that, arch -x86_64 cargo build under Rosetta is the escape hatch. All published timings in the paper were taken bare-metal on the machine named in the evaluation section — do not benchmark inside Docker or on shared cloud instances and expect the same figures.

Running the demo
make demo

This starts a --dev node, pushes a governance-signed accreditation rule into the registry, and walks one transaction end to end: the agent proposes the transfer, emits a signed Compliance Recommendation Record, the governance gate checks it, a ZK proof is generated for the accreditation predicate, and the runtime either finalizes or rejects.

The result that matters
python experiments/bypass_experiment.py

This submits the same non-compliant transfer twice: once through the normal client path, and once as a raw extrinsic constructed to bypass the client entirely. Both are rejected at the runtime layer. This is the whole point of the architecture — enforcement is not made harder to circumvent, it is relocated to a layer where circumvention is not a valid state transition. If either path succeeds, the claim is wrong and you have found something interesting.

Latency and ZK figures:

python experiments/bench_latency.py
python experiments/bench_zkp.py
What is stubbed

Being honest about this saves everyone time:

One jurisdiction, one asset class, one compliance predicate. The rule registry is general; the loaded rule set is minimal.
The DID/VC layer is reduced to a hardcoded authorized-issuer key. The ZK verification path is real; the identity plumbing around it is not.
The governance module verifies signatures and admits rules. It does not implement a full on-chain voting process — the point being demonstrated is the gate, not the deliberation.
The AI agents run against a hosted model (Groq / Mistral). Determinism lives in the enforcement layer by design, not in the model.

None of these affect the three claims above. They would all matter for a deployment, and they are exactly the future-work items in the paper.

Citing

If you use this in academic work, cite the paper (Saifuddin, Jadidi, and Muthukkumarasamy, "AI-Assisted Runtime Compliance Architecture for Tokenized Real-World Assets"). Prototype components are ongoing work at Griffith University.

A note on status

This tracks active research. Interfaces will move, pallets will be renamed, and the main branch is not a stable API. If you want the exact state used for a given set of results, use the tagged commit referenced in the paper rather than main.
