# POST-REGISTRATION: stronger baselines and calendar robustness

Plan committed before the run: docs/BASELINES_CALENDARS_PLAN.md. Seed bases 50000 (held-out) and 90000 (fresh); 20,000 planning and 2,000 evaluation scenarios; frozen code. Costs in USD m. Positive 'minus QAMP' means QAMP is cheaper. Not pre-registered.

Code and rules unchanged during the run: True (git lines changed in src/ and kb/: 0).

## E1. All policies (policy minus QAMP, 95% CI)

### main_seed50000

| Policy | Mean cost | Minus QAMP (95% CI) | Expected misses | Protected 2030 |
|---|---|---|---|---|
| qamp_stochastic | 369.6 | +0.0 (0.0 to 0.0) | 0.0 | 100.0% |
| qamp_no_windows | 399.2 | +29.5 (23.0 to 36.4) | 0.0 | 100.0% |
| qamp_expected | 406.5 | +36.9 (28.0 to 46.4) | 0.0 | 99.9% |
| asap_fifo | 409.2 | +39.5 (31.5 to 48.2) | 0.0 | 100.0% |
| greedy_risk | 399.6 | +30.0 (23.4 to 37.1) | 0.0 | 100.0% |
| mosca | 401.4 | +31.7 (25.0 to 38.9) | 0.0 | 100.0% |
| B1_cal_greedy_risk | 402.4 | +32.8 (26.1 to 39.5) | 0.0 | 100.0% |
| B2_earliest_last_start | 390.7 | +21.1 (15.3 to 27.5) | 0.0 | 100.0% |
| B3_greedy_cost_table | 404.4 | +34.7 (27.4 to 42.3) | 0.0 | 100.0% |
| B4_one_date_mean | 6052.1 | +5682.4 (5269.6 to 6098.0) | 9.57 | 0.0% |
| B5_one_date_median | 3991.2 | +3621.5 (3321.6 to 3940.3) | 9.57 | 26.4% |

One-date baselines planned for arrival quarter 50.0 (mean) and 43.5 (median).

### period1_seed50000

| Policy | Mean cost | Minus QAMP (95% CI) | Expected misses | Protected 2030 |
|---|---|---|---|---|
| qamp_stochastic | 303.9 | +0.0 (0.0 to 0.0) | 0.0 | 100.0% |
| qamp_no_windows | 303.9 | +0.0 (0.0 to 0.0) | 0.0 | 100.0% |
| qamp_expected | 303.9 | +0.0 (-0.0 to 0.0) | 0.0 | 100.0% |
| asap_fifo | 318.8 | +14.9 (12.2 to 17.7) | 0.0 | 100.0% |
| greedy_risk | 311.1 | +7.2 (5.5 to 9.0) | 0.0 | 100.0% |
| mosca | 327.8 | +23.9 (19.4 to 28.4) | 0.0 | 100.0% |
| B1_cal_greedy_risk | 311.1 | +7.2 (5.5 to 9.0) | 0.0 | 100.0% |
| B2_earliest_last_start | 311.1 | +7.2 (5.5 to 9.0) | 0.0 | 100.0% |
| B3_greedy_cost_table | 310.0 | +6.1 (4.2 to 8.0) | 0.0 | 100.0% |
| B4_one_date_mean | 5984.7 | +5680.9 (5268.7 to 6097.7) | 7.22 | 0.0% |
| B5_one_date_median | 3951.9 | +3648.0 (3342.4 to 3974.3) | 7.22 | 21.1% |

One-date baselines planned for arrival quarter 50.0 (mean) and 43.5 (median).

### tight_seed50000

| Policy | Mean cost | Minus QAMP (95% CI) | Expected misses | Protected 2030 |
|---|---|---|---|---|
| qamp_stochastic | 1033.2 | +0.0 (0.0 to 0.0) | 0.0 | 99.9% |
| qamp_no_windows | 1067.7 | +34.5 (28.7 to 40.7) | 0.0 | 99.9% |
| qamp_expected | 1274.4 | +241.2 (212.3 to 273.9) | 0.0 | 97.4% |
| asap_fifo | 1147.4 | +114.2 (96.6 to 133.4) | 0.0 | 99.8% |
| greedy_risk | 1147.3 | +114.1 (96.5 to 133.3) | 0.0 | 99.8% |
| mosca | 1147.4 | +114.2 (96.6 to 133.4) | 0.0 | 99.8% |
| B1_cal_greedy_risk | 1102.5 | +69.3 (56.6 to 82.7) | 0.0 | 99.7% |
| B2_earliest_last_start | 1115.6 | +82.4 (68.8 to 96.5) | 0.0 | 100.0% |
| B3_greedy_cost_table | 1043.1 | +9.8 (1.3 to 18.8) | 0.0 | 99.7% |
| B4_one_date_mean | 5907.9 | +4874.7 (4502.2 to 5238.0) | 8.38 | 0.0% |
| B5_one_date_median | 3750.5 | +2717.3 (2485.6 to 2962.7) | 8.38 | 68.5% |

One-date baselines planned for arrival quarter 50.0 (mean) and 43.5 (median).

### main_seed90000

| Policy | Mean cost | Minus QAMP (95% CI) | Expected misses | Protected 2030 |
|---|---|---|---|---|
| qamp_stochastic | 370.5 | +0.0 (0.0 to 0.0) | 0.0 | 100.0% |
| qamp_no_windows | 400.0 | +29.5 (23.7 to 35.7) | 0.0 | 100.0% |
| qamp_expected | 415.2 | +44.7 (35.0 to 55.6) | 0.0 | 100.0% |
| asap_fifo | 412.7 | +42.2 (33.9 to 50.4) | 0.0 | 100.0% |
| greedy_risk | 402.4 | +31.9 (25.3 to 38.8) | 0.0 | 100.0% |
| mosca | 405.4 | +34.9 (27.4 to 42.4) | 0.0 | 100.0% |
| B1_cal_greedy_risk | 402.7 | +32.2 (25.9 to 38.8) | 0.0 | 100.0% |
| B2_earliest_last_start | 395.8 | +25.3 (19.8 to 31.9) | 0.0 | 100.0% |
| B3_greedy_cost_table | 410.4 | +39.9 (32.3 to 47.7) | 0.0 | 100.0% |
| B4_one_date_mean | 6197.0 | +5826.5 (5399.1 to 6261.9) | 9.57 | 0.0% |
| B5_one_date_median | 4137.2 | +3766.7 (3435.8 to 4112.2) | 9.57 | 26.5% |

One-date baselines planned for arrival quarter 50.1 (mean) and 43.6 (median).

### period1_seed90000

| Policy | Mean cost | Minus QAMP (95% CI) | Expected misses | Protected 2030 |
|---|---|---|---|---|
| qamp_stochastic | 309.5 | +0.0 (0.0 to 0.0) | 0.0 | 100.0% |
| qamp_no_windows | 309.5 | +0.0 (0.0 to 0.0) | 0.0 | 100.0% |
| qamp_expected | 309.5 | +0.0 (-0.0 to 0.0) | 0.0 | 100.0% |
| asap_fifo | 322.1 | +12.7 (10.2 to 15.1) | 0.0 | 100.0% |
| greedy_risk | 314.9 | +5.4 (3.8 to 7.0) | 0.0 | 100.0% |
| mosca | 331.0 | +21.5 (17.4 to 25.6) | 0.0 | 100.0% |
| B1_cal_greedy_risk | 314.9 | +5.4 (3.8 to 7.0) | 0.0 | 100.0% |
| B2_earliest_last_start | 314.9 | +5.4 (3.8 to 7.0) | 0.0 | 100.0% |
| B3_greedy_cost_table | 313.8 | +4.3 (2.6 to 6.1) | 0.0 | 100.0% |
| B4_one_date_mean | 6190.0 | +5880.6 (5449.8 to 6319.5) | 7.18 | 0.0% |
| B5_one_date_median | 4159.9 | +3850.4 (3511.9 to 4199.8) | 7.18 | 18.8% |

One-date baselines planned for arrival quarter 50.1 (mean) and 43.6 (median).

### tight_seed90000

| Policy | Mean cost | Minus QAMP (95% CI) | Expected misses | Protected 2030 |
|---|---|---|---|---|
| qamp_stochastic | 1063.6 | +0.0 (0.0 to 0.0) | 0.0 | 99.9% |
| qamp_no_windows | 1100.6 | +37.1 (30.9 to 43.6) | 0.0 | 99.9% |
| qamp_expected | 1331.6 | +268.0 (235.2 to 300.6) | 0.31 | 97.3% |
| asap_fifo | 1188.4 | +124.9 (107.2 to 143.7) | 0.0 | 99.8% |
| greedy_risk | 1188.4 | +124.8 (107.2 to 143.6) | 0.0 | 99.8% |
| mosca | 1188.4 | +124.9 (107.2 to 143.7) | 0.0 | 99.8% |
| B1_cal_greedy_risk | 1139.2 | +75.7 (62.9 to 88.9) | 0.0 | 99.7% |
| B2_earliest_last_start | 1153.8 | +90.3 (76.6 to 104.4) | 0.0 | 100.0% |
| B3_greedy_cost_table | 1078.6 | +15.1 (7.1 to 23.1) | 0.0 | 99.7% |
| B4_one_date_mean | 6019.1 | +4955.5 (4577.6 to 5333.4) | 8.39 | 0.0% |
| B5_one_date_median | 3921.1 | +2857.5 (2605.7 to 3130.8) | 8.39 | 68.5% |

One-date baselines planned for arrival quarter 50.1 (mean) and 43.6 (median).

## E2. Wrong calendars (plan on frozen calendars, score on different ones for the 47 assumed anchors)

Mean over 10 draws of random phases; range across draws in brackets.

| True calendar | qamp_no_windows | qamp_expected | asap_fifo | greedy_risk | mosca | B1_cal_greedy_risk | B2_earliest_last_start | B3_greedy_cost_table | B4_one_date_mean | B5_one_date_median |
|---|---|---|---|---|---|---|---|---|---|---|
| annual_random_phase (QAMP 393.7) | -3.3 (-18.5 to 10.0) | +47.8 (25.4 to 69.6) | +21.2 (-4.6 to 44.0) | +13.2 (-9.0 to 37.8) | +25.4 (-1.6 to 49.5) | +47.0 (19.5 to 73.0) | +34.8 (17.5 to 54.7) | +58.3 (41.5 to 78.8) | +5718.7 (5667.0 to 5745.3) | +3676.8 (3649.2 to 3709.4) |
| every_2q (QAMP 334.4) | -3.3 (-4.4 to -2.1) | +40.1 (38.2 to 41.5) | +12.4 (11.2 to 13.5) | +4.8 (3.6 to 5.7) | +22.1 (19.8 to 23.7) | +32.8 (32.1 to 33.5) | +29.8 (28.9 to 30.8) | +44.4 (40.7 to 48.8) | +5636.0 (5630.5 to 5640.5) | +3603.5 (3597.4 to 3608.7) |
| every_quarter (QAMP 306.9) | -2.8 (-2.8 to -2.8) | +36.9 (36.9 to 36.9) | +12.0 (12.0 to 12.0) | +4.4 (4.4 to 4.4) | +21.1 (21.1 to 21.1) | +30.7 (30.7 to 30.7) | +28.2 (28.2 to 28.2) | +42.9 (42.9 to 42.9) | +5587.7 (5587.7 to 5587.7) | +3562.0 (3562.0 to 3562.0) |
| every_8q (QAMP 542.5) | -3.3 (-74.0 to 74.0) | +54.4 (-36.8 to 119.8) | +7.4 (-77.5 to 87.8) | +1.6 (-80.4 to 76.7) | +22.0 (-77.5 to 112.0) | +40.9 (-3.3 to 119.9) | +42.7 (-4.7 to 93.4) | +54.4 (-53.6 to 119.9) | +5861.8 (5735.8 to 6106.6) | +3827.8 (3710.2 to 3910.7) |

## E3. Assumed calendars set to another period (planning and scoring)

| Assumed period | QAMP mean | qamp_no_windows | qamp_expected | asap_fifo | greedy_risk | mosca | B1_cal_greedy_risk | B2_earliest_last_start | B3_greedy_cost_table | B4_one_date_mean | B5_one_date_median |
|---|---|---|---|---|---|---|---|---|---|---|---|
| assumed_period_1 | 304.1 | -0.1 (-1.6 to 1.5) | +0.1 (0.0 to 0.2) | +14.8 (11.7 to 17.9) | +7.1 (4.9 to 9.5) | +23.8 (19.1 to 28.5) | +7.1 (4.9 to 9.5) | +7.1 (4.9 to 9.5) | +6.0 (3.6 to 8.4) | +5680.7 (5268.5 to 6098.0) | +3647.1 (3342.4 to 3974.2) |
| assumed_period_2 | 332.2 | +0.3 (0.1 to 0.5) | +27.4 (20.5 to 34.7) | +14.6 (11.3 to 18.1) | +6.8 (4.3 to 9.5) | +22.6 (17.7 to 27.7) | +17.0 (13.0 to 21.4) | +71.8 (59.3 to 84.9) | +5.7 (3.1 to 8.5) | +5694.3 (5281.3 to 6111.2) | +3726.8 (3419.4 to 4058.0) |
| assumed_period_4 | 369.6 | +29.5 (23.0 to 36.4) | +36.9 (28.0 to 46.4) | +39.5 (31.5 to 48.2) | +30.0 (23.4 to 37.1) | +31.7 (25.0 to 38.9) | +32.8 (26.1 to 39.5) | +21.1 (15.3 to 27.5) | +34.7 (27.4 to 42.3) | +5682.4 (5269.6 to 6098.0) | +3621.5 (3321.6 to 3940.3) |
| assumed_period_8 | 525.0 | +19.9 (17.1 to 22.7) | +205.1 (179.0 to 233.7) | +25.9 (16.7 to 35.7) | +22.9 (13.8 to 32.4) | +25.9 (16.7 to 35.7) | +63.7 (50.8 to 77.1) | +63.7 (50.8 to 77.1) | +5.7 (-2.8 to 14.4) | +5495.3 (5096.8 to 5885.2) | +3517.4 (3233.3 to 3822.1) |
