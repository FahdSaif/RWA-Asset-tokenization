"""QAMP: Quantum-Aware Migration Planner.

An expert system that plans the post-quantum migration of the compliance trust anchors of tokenised
real-world-asset (RWA) infrastructure: credential issuers, regulatory-data feeds, governance quorums and the
administrative keys that control token contracts.

Modules
  model       data classes: Token, Anchor, Calendar, Deployment
  data        loaders for the real census of tokenised-asset contracts (rwa-threatlab, experiment C)
  discovery   cryptographic inventory (CBOM) from ABIs, controllers and Solidity source; rules or LLM classifier
  kb          rule knowledge base with source clauses and an inference trace
  scenarios   CRQC-arrival distribution and execution-time uncertainty
  loss        exposure model (forgery after CRQC arrival; trust-now-forge-later on retained records)
  planner     decision-window-aware stochastic MILP (scipy / HiGHS)
  baselines   comparison policies and the oracle
  guard       bounded model check of mixed-cryptography states across bridged instances
  explain     grounded, cited rationales
  evaluate    experiment harness and statistics
"""
__version__ = "0.1.1"
