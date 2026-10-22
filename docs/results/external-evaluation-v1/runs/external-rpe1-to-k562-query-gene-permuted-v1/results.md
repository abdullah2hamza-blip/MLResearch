# Replay results

Run label: `Frozen external negative control rpe1-to-k562/query_gene_permutation; docs/external-evaluation-protocol.md`.

Source-query responses are public; recipient-query responses are scorer-only.

| Policy | Mean error area | Difference vs worst-query | Conditional 95% interval |
| --- | ---: | ---: | ---: |
| fixed_grid | 0.00576227 | -4.48377e-07 | [-3.6923e-06, 3.63161e-06] |
| worst_query | 0.00576272 | 0 | [0, 0] |
| mean_query | 0.00575893 | -3.78841e-06 | [-5.24271e-06, -2.28855e-06] |
| bias_aware | 0.00576258 | -1.36331e-07 | [-2.00188e-06, 2.2476e-06] |

![Acquisition curves](acquisition-curves.png)

![Predictor curves](predictor-curves.png)

Descriptive query-intervention bootstrap conditional on source data, fixed split, acquisition seeds, and fixed assessment/control bank. Excludes biological, guide/batch and common scoring-control uncertainty.

Gaussian coverage and risk-retention tables are diagnostic. Adaptive coverage is unvalidated.

These results do not establish prospective benefit, causal transportability, biological replication, or a novel method.
