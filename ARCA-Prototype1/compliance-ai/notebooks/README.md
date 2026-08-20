# notebooks/

Put `arca_demo.ipynb` here — the presentation version of your existing
langgraph_email_groq_mistral notebook, re-labelled in ARCA vocabulary:

  classify/route  ->  Transaction Risk Scoring Agent
  email agent      ->  Investor Eligibility Evaluation Agent (emits a signed CRR)
  HITL interrupt   ->  governance gate (approve / edit / reject)
  send_email       ->  forward-to-chain (only on approve)

The logic lives in ../src/arca_ai/; the notebook should just import and narrate it,
so the demo and the tested code never drift apart.
