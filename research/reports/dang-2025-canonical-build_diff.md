# Dang 2025 compiled study: before/after record diff

Old: `artifact_before.json` (schema `compiled-study-1`). New: `dang_2025_durian.json` (schema `compiled-study-2`).
Records are matched by identifier; `reordered` means the common records appear in a different order.

| Section | Old | New | Added | Removed | Unchanged | Changed | Reordered |
|---|---:|---:|---:|---:|---:|---:|---|
| sites | 3 | 3 | 0 | 0 | 3 | 0 | no |
| interventions | 3 | 3 | 0 | 0 | 3 | 0 | no |
| arms | 4 | 4 | 0 | 0 | 4 | 0 | no |
| outcomes | 14 | 14 | 0 | 0 | 0 | 14 | no |
| arm_results | 264 | 336 | 72 | 0 | 264 | 0 | yes |
| comparison_families | 66 | 84 | 18 | 0 | 0 | 66 | no |
| contrasts | 198 | 252 | 54 | 0 | 0 | 198 | no |
| associations | 36 | 36 | 0 | 0 | 36 | 0 | no |
| interpretations | 0 | 0 | 0 | 0 | 0 | 0 | no |
| recommendations | 0 | 0 | 0 | 0 | 0 | 0 | no |
| flags | 5 | 8 | 3 | 0 | 3 | 2 | no |

## Changed or added records

### outcomes

- field `post_treatment_selection` changed in 13 records (example `outcome-soil-ph`):
  - before: `null`
  - after: `false`
- field `sampling_rule` changed in 12 records (example `outcome-soil-ph`):
  - before: `null`
  - after: `"Soil at 0-20 cm sampled around the canopy at three points 1 m from the trunk and mixed into one sample; 72 samples in total (4 treatments x 3 repl...`
- field `measurement_time` changed in 5 records (example `outcome-peel-proportion`):
  - before: `null`
  - after: `"Fruit harvesting period"`
- field `notes` changed in 5 records (example `outcome-peel-proportion`):
  - before: `null`
  - after: `"Measured only on the selected fruit; applies to sound fruit of that weight range, not to all fruit of the orchard."`
- field `selection_rule` changed in 5 records (example `outcome-peel-proportion`):
  - before: `null`
  - after: `"Selected fruits weighed 2.2-2.8 kg and had no physical damage due to pest infestation."`

### arm_results

- added: 72 records, e.g. `t3-d1-2022-2023-control-peel` ... `t3-d3-2023-2024-om-ff-aril`

### comparison_families

- added: 18 records, e.g. `comparison-family-table-3-d1-2022-2023-outcome-aril-proportion` ... `comparison-family-table-3-d3-2023-2024-outcome-seed-proportion`
- field `group_letter_semantics` changed in 66 records (example `comparison-family-table-1-d1-2022-2023-outcome-available-p`):
  - before: `"Different letters indicate significant differences among treatment means under the reported Duncan post hoc procedure at p < 0.05."`
  - after: `"Different letters indicate a significant difference between treatment means under the Duncan post hoc procedure at p < 0.05, as stated in Section ...`

### contrasts

- added: 54 records, e.g. `derived-vs-control-table-3-d1-2022-2023-arm-om-outcome-aril-proportion` ... `derived-vs-control-table-3-d3-2023-2024-arm-om-ff-outcome-seed-proportion`
- field `assumptions` changed in 198 records (example `derived-vs-control-table-1-d1-2022-2023-arm-om-outcome-available-p`):
  - before: `["Published arm means correspond to the randomized treatment groups in this site-season stratum.", "This value is a deterministic arm-mean differen...`
  - after: `["The two values are published arm means from one orchard and season, each over three replicates.", "The stored value is a deterministic difference...`
- field `estimand_text` changed in 198 records (example `derived-vs-control-table-1-d1-2022-2023-arm-om-outcome-available-p`):
  - before: `"Difference in published intervention and control arm means within one orchard, season, and outcome stratum."`
  - after: `"Difference between the published arm means of one treatment arm and the control arm (each a mean over three replicates) within one orchard, season...`
- field `evidential_basis` changed in 198 records (example `derived-vs-control-table-1-d1-2022-2023-arm-om-outcome-available-p`):
  - before: `"randomized_within_block_arm_mean_comparison"`
  - after: `"published_arm_mean_difference"`
- field `uncertainty_text` changed in 198 records (example `derived-vs-control-table-1-d1-2022-2023-arm-om-outcome-available-p`):
  - before: `"The paper reports arm means and standard deviations, but the covariance/block-level information required to reconstruct uncertainty for this deriv...`
  - after: `"The paper reports arm means and standard deviations (n = 3) but not the replicate-level data, block structure or randomization unit that an estima...`
- field `unit` changed in 36 records (example `derived-vs-control-table-4-d1-2022-2023-arm-om-outcome-pd-rate`):
  - before: `"%"`
  - after: `"percentage points"`

### flags

- added: 3 records, e.g. `flag-table5-markers-inconsistent-with-n72` ... `flag-comparison-letter-semantics-ambiguous`
- field `detail` changed in 2 records (example `flag-randomization-unit-unclear`):
  - before: `"The article reports a randomized complete block design with three replicates and 12 trees per treatment, but does not explicitly identify the phys...`
  - after: `"The article reports a randomized complete block design with three replicates and 12 trees per treatment, but does not explicitly identify the phys...`
- field `related_record_ids` changed in 2 records (example `flag-randomization-unit-unclear`):
  - before: `[]`
  - after: `["derived-vs-control-table-1-d1-2022-2023-arm-om-outcome-available-p", "derived-vs-control-table-1-d1-2022-2023-arm-ff-outcome-available-p", "deriv...`

## Other top-level fields that differ

- `metadata`
  - before: `{"compilation_method": "manual", "compilation_scope": "study design, sites, population, interventions, arms, outcome definitions, Table 1 soil chem...`
  - after: `{"compilation_method": "manual", "compilation_scope": "study design, sites, population, interventions, arms, outcome definitions, Table 1 soil chem...`
- `schema_version`
  - before: `"compiled-study-1"`
  - after: `"compiled-study-2"`
