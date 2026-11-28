# POST-REGISTRATION: negative tests of the explanation checks

Plan committed before the run: docs/EXPLAIN_NEGATIVE_TESTS_PLAN.md. Frozen code; no API calls. Not pre-registered.

Code and rules unchanged during the run: True (git lines changed in src/ and kb/: 0).

Control: 781 correct sentences; accepted by the frozen checks 781, by the strict check 781.

| ID | Error | Wrong sentences | Rejected, frozen checks | Rejected, strict check |
|---|---|---|---|---|
| N1 | Value changed to one not in the cited facts | 471 | 471 (100.0%) | 471 (100.0%) |
| N2 | Two valid values swapped | 150 | 0 (0.0%) | 150 (100.0%) |
| N3 | Valid value in the wrong place | 471 | 361 (76.6%) | 471 (100.0%) |
| N4 | Statement reversed | 450 | 0 (0.0%) | 450 (100.0%) |
| N5 | Wrong regulation named | 75 | 0 (0.0%) | 75 (100.0%) |
| N6 | Unsupported reason added | 781 | 0 (0.0%) | 781 (100.0%) |
| N7 | Right citation, wrong claim | 781 | 471 (60.3%) | 778 (99.6%) |
| N8 | Wrong deadline date | 150 | 150 (100.0%) | 150 (100.0%) |

Sentences reworded by the language model in the frozen H13 run: 821; accepted by the frozen checks 455 (55.4%), by the strict check 0 (0.0%).

## Examples the frozen checks accepted

- N2 original: Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:ctrl:0x1a694a09494e214a3be3652e4b343b7b81a73ad7].
  wrong: Start the migration in 2; with a planned execution time of 2027 Q1 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:ctrl:0x1a694a09494e214a3be3652e4b343b7b81a73ad7].
- N3 original: The decision window for that boundary closes at the start of 2027 Q1; a later start waits 1 quarter(s) for the next boundary [P:ctrl:0x1a694a09494e214a3be3652e4b343b7b81a73ad7].
  wrong: The decision window for that boundary closes at the start of 2027 Q3; a later start waits 1 quarter(s) for the next boundary [P:ctrl:0x1a694a09494e214a3be3652e4b343b7b81a73ad7].
- N4 original: The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
  wrong: The algorithm secp256k1-ecdsa is allowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
- N5 original: The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under NIST IR 8547 [R:NIST8547-DISALLOW].
  wrong: The algorithm secp256k1-ecdsa is disallowed after 2035-12-31 under the EU AML directive [R:NIST8547-DISALLOW].
- N6 original: Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3 [P:ctrl:0x1a694a09494e214a3be3652e4b343b7b81a73ad7].
  wrong: Start the migration in 2027 Q1; with a planned execution time of 2 quarter(s) it takes effect at the renewal boundary 2027 Q3, because the issuer asked for it [P:ctrl:0x1a694a09494e214a3be3652e4b343b7b81a73ad7].
- N7 original: Its public key can be attacked as soon as a CRQC exists [R:EXP-KEY-EXPOSED].
  wrong: Its public key can be attacked as soon as a CRQC exists [E:abi:0x96f6ef951840721adbf46ac996b59e0235cb985c:access_control_roles].
