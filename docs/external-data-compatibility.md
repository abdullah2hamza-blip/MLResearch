# External data compatibility and attribution

The pinned files are the scPerturb v1.4 release at [Zenodo record 13350497](https://zenodo.org/records/13350497), DOI `10.5281/zenodo.13350497`. Its registry declares CC BY 4.0. Credit the release creators and [Peidli et al., scPerturb](https://www.nature.com/articles/s41592-023-02144-y), as well as the original experiments. This repository retains derived metrics, metadata inventories and transformations; downloaded H5AD files and prepared cell matrices are ignored.

The original external experiment is [Replogle et al., Mapping information-rich genotype-phenotype landscapes with genome-scale Perturb-seq](https://pmc.ncbi.nlm.nih.gov/articles/PMC9380471/), Cell 185:2559–2575.e28 (2022), DOI `10.1016/j.cell.2022.05.013`. It uses paired guides targeting one gene. Its essential K562 arm was sampled on day 6 with dCas9-KRAB; RPE1 was sampled on day 7 with a ZIM3-derived KRAB effector. Consequently this pair tests combined biological/protocol transfer, not an isolated cell-line effect. The downloaded H5AD files lack explicit time/effector fields, so arm correspondence is inferred from the essential-file identity and target inventory. They must not be described as a matched-time, matched-effector comparison. The article also documents survival/growth selection and high but unequal knockdown efficacy; per-cell knockdown metadata are not available in these harmonized observations.

The actual audits and preparation establish:

| Property | K562 essential | RPE1 |
| --- | ---: | ---: |
| Input cells | 310,385 | 247,914 |
| Input expression genes | 8,563 | 8,749 |
| Input non-control labels | 2,057 | 2,393 |
| Retained cells | 50,912 | 50,912 |
| Batch labels | 48 | 56 |

There are 525 exact target labels with at least 96 cells each in both files, and 7,226 exactly aligned expression genes. All available input genes enter per-file count normalization before gene intersection. The denominators therefore differ between released panels; absolute control-relative effects can retain compositional panel differences. These are released gene panels, not complete transcriptomes.

[Target-ID evidence](evidence/replogle-target-identifiers.json) preserves the observed target-symbol to Ensembl-ID mapping. K562's 2,057 non-control labels have distinct nonempty IDs. Three RPE1 labels outside the eligible overlap have missing IDs (`NEDD8-MDP1`, `PRSS50`, `RBM14-RBM4`); empty IDs are missingness, not a shared canonical gene. Eligible targets must have nonempty, matching IDs in both files. There are no observed cross-file ID disagreements among shared labels. Episode guide ownership is also validated so guides cannot cross two target identities. Exact symbols alone do not generally resolve aliases; these checks are specific to the retained pair.

The later [canonical freeze](evidence/external-canonical-identifiers-v1.json) rehashes both raw inputs against their verified sidecars and episode provenance, then checks the raw `obs/gene_id`, `obs/guide_id` and `var/ensembl_id` annotations. All 525 retained targets have distinct, matching nonempty canonical IDs; their canonical query/calibration sets are disjoint. All 7,226 aligned expression genes also have matching Ensembl IDs, with unique nonmissing IDs on each complete released panel. Original labels and guide combinations are preserved in the record. Reproduce it with `uv run python scripts/audit-external-identifiers.py --output <fresh-json-path>`. The audit reads metadata and hashes opaque file bytes; it never reads expression arrays for analysis or opens recipient assessment outcomes.

Controls have separate acquisition/assessment cells. Each episode contains 394 calibration candidates and 131 sealed query identities, with 64/32 candidate acquisition/assessment cells and 256/256 control cells. Query acquisition labels are omitted from the acquisition map. Both directions were frozen without opening external scorer outcomes. Source query responses remain explicitly public.

No observed sequencing batch is assumed to be an independent biological replicate. Batch and guide identifiers are retained, while donor/independent biological replicate fields are absent. Random cell splits support a conditional replay analysis, not patient-level inference or prospective validation. Cross-direction results will share original interventions and observations and must not be counted as independent replications.

Frangieh development data originate from [Frangieh et al., Perturb-CITE-seq](https://ccsp.hms.harvard.edu/wp-content/uploads/2021/10/Frangieh-2021.pdf). Their separate perturbation/context setting is not pooled with the external CRISPRi arms. The development RNA preparation uses declared `MOI=1`; dual guides in the Replogle construct still represent one targeted gene and are not excluded as two-gene perturbations.
