# Authorship, responsibility and AI-assistance statement

The research questions, the extension of the authors' threat model and decision-window theory to post-quantum
migration, the hypotheses (after the authors' review of the draft), the sample rule and the evaluation protocol are the
authors' research design. The authors review and run the code and take full responsibility for the software, the
results and the conclusions.

An AI assistant was used to draft the prototype code, the tests, the extraction notebook and this
documentation, and to check regulatory sources cited in the knowledge base. AI tools are not authors. Tool versions and
dates will be completed before submission, consistent with the manuscript's declaration.

**Ground-truth labels for RQ1.** At the author's request, the 192 hand labels for discovery (6 surfaces × 32 distinct
source codes) were made by the AI assistant reading the verified source, with file and line for every positive label
(`data/labels_A.csv`). Because the same assistant also drafted QAMP's discovery rules, these labels are not
independent of the system under test. A random 40-row sample (`data/labels_check_blank.csv`) is set aside for a blind
check by the author; its agreement with the AI labels will be reported. See `docs/LABELLING.md`.

