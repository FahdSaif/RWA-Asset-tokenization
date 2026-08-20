# Running the Layer-1 demo

It's a package, so run it as a module (this resolves the relative imports):

```bash
PYTHONPATH=compliance-ai/src python -m arca_ai.graph --demo
```

Optional LLM rationale: set `GROQ_API_KEY` (and optionally `ARCA_MODEL`) in the
environment. Without a key the decision logic still runs; only the natural-language
rationale line is skipped. The enforcement decision never depends on the model.

Tests:
```bash
cd compliance-ai && PYTHONPATH=src pytest -q
```
