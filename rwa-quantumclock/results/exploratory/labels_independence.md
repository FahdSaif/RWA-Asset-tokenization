# POST-REGISTRATION: independence of the discovery labels

Plan committed before the run: docs/LABELS_INDEPENDENCE_PLAN.md. Committed files only; no API calls. Not pre-registered.

Code and rules unchanged during the run: True (git lines changed in src/ and kb/: 0). The 40-row human check was not done.

## A. Scores by label source

| Classifier | Labels | Unit | Labels (positives) | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| rules | all | token | 1400 (384) | 0.67 | 0.852 | 0.75 |
| rules | all | code | 448 (111) | 0.649 | 0.865 | 0.741 |
| rules | bytecode | token | 800 (265) | 0.714 | 0.996 | 0.831 |
| rules | bytecode | code | 256 (82) | 0.681 | 0.988 | 0.806 |
| rules | hand | token | 600 (119) | 0.534 | 0.529 | 0.532 |
| rules | hand | code | 192 (29) | 0.517 | 0.517 | 0.517 |
| language_model | all | token | 1400 (384) | 0.667 | 0.089 | 0.156 |
| language_model | all | code | 448 (111) | 0.667 | 0.252 | 0.366 |
| language_model | bytecode | token | 800 (265) | 0.675 | 0.102 | 0.177 |
| language_model | bytecode | code | 256 (82) | 0.676 | 0.28 | 0.397 |
| language_model | hand | token | 600 (119) | 0.636 | 0.059 | 0.108 |
| language_model | hand | code | 192 (29) | 0.625 | 0.172 | 0.27 |

## B. Mechanical check of signature verification (32 distinct codes)

| Check | Compared with | Both | Mechanical only | Other only | Neither | Agreement | Kappa |
|---|---|---|---|---|---|---|---|
| ecdsa | hand_labels | 0 | 2 | 14 | 16 | 0.5 | -0.123 |
| ecdsa | rules | 0 | 2 | 14 | 16 | 0.5 | -0.123 |
| p256 | hand_labels | 0 | 0 | 0 | 32 | 1.0 | 1.0 |
| p256 | rules | 0 | 0 | 0 | 32 | 1.0 | 1.0 |
| bls | hand_labels | 0 | 0 | 0 | 32 | 1.0 | 1.0 |
| bls | rules | 0 | 0 | 0 | 32 | 1.0 | 1.0 |

Disagreements (distinct code):
- ecdsa vs hand_labels: 0x015c477a4e2881c4b3bb8999f59ee4a04e812344, 0x0990b149e915cb08e2143a5c6f669c907eddc8b0, 0x119dd7daff816f29d7ee47596ae5e4bdc4299165, 0x18f52b3fb465118731d9e0d276d4eb3599d57596, 0x2e44f3f609ff5aa4819b323fd74690f07c3607c4, 0x396382f6048ceb0407e5b8f0b6fefeebd244c6f7, 0x4c1746a800d224393fe2470c70a35717ed4ea5f1, 0x54a4fc78431f9201824643e99bec891bb7462a1d, 0x5a0f93d040de44e78f251b03c43be9cf317dcf64, 0x63401cdd577478f9389a1683e866a937f072d1c2, 0x8238884ec9668ef77b90c6dff4d1a9f4f4823bfe, 0xaaa0008c8cf3a7dca931adaf04336a5d808c82cc, 0xad55aebc9b8c03fc43cd9f62260391c13c23e7c0, 0xaeb0a5d56de94479cda178977570fd9079500527, 0xc845b2894dbddd03858fd2d643b4ef725fe0849d, 0xd0ec028a3d21533fdd200838f39c85b03679285d
- ecdsa vs rules: 0x015c477a4e2881c4b3bb8999f59ee4a04e812344, 0x0990b149e915cb08e2143a5c6f669c907eddc8b0, 0x119dd7daff816f29d7ee47596ae5e4bdc4299165, 0x18f52b3fb465118731d9e0d276d4eb3599d57596, 0x2e44f3f609ff5aa4819b323fd74690f07c3607c4, 0x396382f6048ceb0407e5b8f0b6fefeebd244c6f7, 0x4c1746a800d224393fe2470c70a35717ed4ea5f1, 0x54a4fc78431f9201824643e99bec891bb7462a1d, 0x5a0f93d040de44e78f251b03c43be9cf317dcf64, 0x63401cdd577478f9389a1683e866a937f072d1c2, 0x8238884ec9668ef77b90c6dff4d1a9f4f4823bfe, 0xaaa0008c8cf3a7dca931adaf04336a5d808c82cc, 0xad55aebc9b8c03fc43cd9f62260391c13c23e7c0, 0xaeb0a5d56de94479cda178977570fd9079500527, 0xc845b2894dbddd03858fd2d643b4ef725fe0849d, 0xd0ec028a3d21533fdd200838f39c85b03679285d
