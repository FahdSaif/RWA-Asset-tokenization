# Inter-rater data

| File | What it is |
|---|---|
| `assessor_scoring_pack.xlsx` | The blank workbook given to assessors: instructions, system summary, rubric and the 14 scenarios with neutral descriptions. It contains none of the authors' ratings. |
| `scores_R1-R4.csv` | Anonymised factor scores (F1-F3, G1-G3, each 1 to 3) of four assessors (codes R1 to R4) for the 14 scenarios. |
| `assessor_template.csv` | A blank scoring sheet in the CSV format read by `rwa_threatlab.irr`. |

Analysis: `python -m rwa_threatlab.irr docs/irr/scores_R1-R4.csv` (Krippendorff's alpha with an ordinal metric, exact agreement,
agreement within one level, and agreement of residual bands). Results: `docs/results/irr.json` and `irr.md`.

To convert further returned workbooks: `python scripts/xlsx_to_irr.py --out scores.csv file1.xlsx file2.xlsx ...` (needs `openpyxl`). The
converter refuses any workbook that is marked simulated or synthetic. The rating revision that followed this study is described in
`docs/RATINGS_REVISION.md`.
