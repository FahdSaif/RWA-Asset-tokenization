# Paper section → code → output

| Paper element | Code | Output |
|---|---|---|
| Figure 1 (application setting: tokens, anchors, calendars) | `data.load_census`, `python -m qamp census` | `results/census/census_anchors.md` |
| Threat model: quantum adversary, five attack classes | `kb/30_exposure.yaml`, `loss.py`, `guard.py` | — |
| Knowledge base table (rules, sources) | `kb/*.yaml` | — |
| Problem formulation (decision windows, MILP) | `model.Calendar`, `loss.effective_quarter`, `planner.py` | — |
| RQ1 discovery results | `discovery/`, `observed.bytecode_labels`, `python -m qamp labels`, `discover --labels` | `results/discovery/discovery_*.json` |
| RQ2 main table | `evaluate.run_policies`, `python -m qamp experiments` | `results/<run>/main_table.md` |
| RQ2 hypotheses H1-H5, H8 | `hypotheses.py` | `results/<run>/hypotheses.md` |
| RQ3 guard (H6, H7, example trace) | `evaluate.run_guard`, `guard.py` | `results/<run>/results.json` → `guard` |
| RQ4 explanation checks (H12, H13) | `explain.py`, `python -m qamp explain-check` | `results/explain/checks.json` |
| Rationales shown in the paper | `explain.py`, `python -m qamp plan` | `results/plan/plan.md` |
| Data section (observed calendars, capacity, instances) | `observed.py`, `python -m qamp facts` | `results/observed/observed_summary.json` |
| Reproducibility statement | `pyproject.toml`, `docs/RUNBOOK.md` | `results/<run>/results.json` → `meta` |
