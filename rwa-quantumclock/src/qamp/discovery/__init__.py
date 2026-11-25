"""Discovery: a cryptographic inventory (CBOM) of a tokenised-asset deployment.

Pipeline
  1. evidence     abi.scan (function names), controllers (from the census), solidity.scan (verified source, with
                  line numbers). Every finding carries an evidence id and a location.
  2. classify     a Classifier turns findings into inventory entries (surface type, algorithm, who signs, anchor).
                  RulesClassifier is deterministic; LLMClassifier asks a language model and keeps only entries
                  whose cited evidence ids exist (hallucinated citations are counted and dropped).
  3. cbom         CycloneDX 1.6-style JSON with one cryptographic-asset component per entry.
  4. score        precision, recall and F1 against hand-labelled inventories (RQ1).
"""
from .abi import scan_abi  # noqa: F401
from .classify import Finding, InventoryEntry, LLMClassifier, RulesClassifier  # noqa: F401
from .solidity import scan_source  # noqa: F401
