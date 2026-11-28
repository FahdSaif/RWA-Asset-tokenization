# POST HOC: check of the guard result (H6)

Held-out seeds from 50000; frozen code; not pre-registered.

## Frozen numbers, reproduced

- Mean realised cost (USD m): {'independent': 480.0, 'guarded': 450.7, 'independent_pause_revalidate': 401.1}
- Independent plan, expected loss ignoring bridges (USD m): 254.6
- Violations: {'independent': 13, 'guarded': 0, 'independent_pause_revalidate': 0} of 13 components

## Underestimate, like for like (H6 threshold: at least 10%)

| Comparison | Underestimate |
|---|---|
| Frozen code: expected loss vs realised loss plus spend | 47.0% |
| Expected loss vs realised loss | 23.7% |
| Expected loss plus spend vs realised loss plus spend | 16.4% |

Spend of the independent plan: USD 146.5m; its realised loss: USD 333.5m.

## Guarded plan when each bridged copy runs late or early on its own

- Start quarters identical within every component: True
- Components whose copies take effect in different quarters (mean per scenario): 5.54 of 13
- Scenarios with at least one violation, bridges open: 100.0% (mean 5.54 per scenario)
- Scenarios with at least one violation, pause-and-revalidate: 0.0%
