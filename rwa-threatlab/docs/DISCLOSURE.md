# Authorship, responsibility and AI-assistance statement

This statement is the single place in the repository that describes how the software and documentation were produced. It
is kept identical in substance to the declaration in the manuscript.

## Research contribution and responsibility

The reference architecture, the mediation surface, the six-class adversary model, the rating method, the attack trees, the
hypotheses and the pre-registered evaluation protocol are the authors' research design, building on their earlier published
work (SDLT 2025 and ARCA). The prototype `rwa-threatlab` was developed as part of this research to implement and test that
design. The authors specified the experiments, review and run the code and take full responsibility for the software, the
experimental results and the conclusions of the publication.

## Use of AI assistance

AI assistance for helping with code. Its use covered the
journal-extension components: the scaled composition check, the floor-dependence and inter-rater tooling, the freeze and
pre-registration tooling, the second oracle and its observer, the real-trace loaders, the replay hook and the runner, the
test suite and continuous-integration workflows for these, the LaTeX table generator, and the accompanying documentation.
AI tools are not authors and bear no responsibility for the content. Further details (earlier components of the repository,
review and testing, tool versions and dates) will be added before journal submission.

## Consequences for the evidence

The second oracle and its specification were written after the fuzzer existed and with knowledge of it. They check the
oracle's logic and are not an independent third-party implementation (see `docs/PREREGISTRATION.md`, addendum A2). The
replication of the official run is carried out within the research effort; independent third-party replication is invited.
