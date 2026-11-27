"""QAMP (Quantum-Aware Migration Planner).

Plans when to move the keys behind tokenised assets to quantum-safe cryptography.

Modules:
  model      data classes
  data       builds tokens and anchors from the census or the notebook data
  observed   turns raw chain data into model inputs
  discovery  finds the signatures each contract accepts (CBOM)
  kb         rules with their sources
  scenarios  when a quantum computer may arrive; delays
  loss       what a late migration costs
  planner    chooses start dates (MILP)
  baselines  simple policies to compare with
  guard      checks bridged chains during a migration
  explain    cited explanations and their checks
  evaluate   experiments and statistics"""
__version__ = "0.3.5"
