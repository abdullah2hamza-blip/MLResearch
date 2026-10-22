# Replay results

Run label: `Frozen external negative control k562-to-rpe1/query_gene_permutation; docs/external-evaluation-protocol.md`.

Source-query responses are public; recipient-query responses are scorer-only.

| Policy | Mean error area | Difference vs worst-query | Conditional 95% interval |
| --- | ---: | ---: | ---: |
| fixed_grid | 0.00815919 | 5.75419e-06 | [-5.76897e-05, 8.24079e-05] |
| worst_query | 0.00815343 | 0 | [0, 0] |
| mean_query | 0.0080726 | -8.08371e-05 | [-0.000128026, -3.29445e-05] |
| bias_aware | 0.00805871 | -9.4726e-05 | [-0.000146512, -4.72618e-05] |

![Acquisition curves](acquisition-curves.png)

![Predictor curves](predictor-curves.png)

Descriptive query-intervention bootstrap conditional on source data, fixed split, acquisition seeds, and fixed assessment/control bank. Excludes biological, guide/batch and common scoring-control uncertainty.

Gaussian coverage and risk-retention tables are diagnostic. Adaptive coverage is unvalidated.

These results do not establish prospective benefit, causal transportability, biological replication, or a novel method.
