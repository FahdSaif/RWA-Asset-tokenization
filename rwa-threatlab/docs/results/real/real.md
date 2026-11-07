| ID | Outcome | Evidence |
|---|---|---|
| H12 | **CONFIRMED** | spread: {'documented-lag': 0, 'adversary': 0, 'UNEXPLAINED': 0} over 600 traces, 3611 real events applied; burst: {'documented-lag': 0, 'adversary': 0, 'UNEXPLAINED': 0} over 600 traces, 3611 real events applied |
| H12b | **CONFIRMED** | baseline violations per variant: {'spread': 216, 'burst': 143} |
| H12c | **CONFIRMED** | independent oracle vs fuzzer oracle on replay traces: 5482 violations compared, 0 disagreements |
| H13a | **CONFIRMED** | H2 under replay: colluding quorum, no censorship, no harmful relaxation (both variants) |
| H13b | **CONFIRMED** | H3 under replay: relaxation harm only with censorship (both variants) |
| H13c | **CONFIRMED** | H4 under replay: issuer-attributed violations only, none unexplained (both variants) |
| H16 | **CONFIRMED** | 2 entries were removed and later re-added in the window |

Label: real traces, simulated compliance layer. Commit 20dd2d74cf6d38a8b16221916ccaac8af573dc2e.
