"""Finds which signatures each contract accepts (a CBOM).

Steps: collect evidence (ABI, controllers, source), classify it (rules or LLM),
write the CBOM, and score it against labels."""
from .abi import scan_abi  # noqa: F401
from .classify import Finding, InventoryEntry, LLMClassifier, RulesClassifier  # noqa: F401
from .solidity import scan_source  # noqa: F401
