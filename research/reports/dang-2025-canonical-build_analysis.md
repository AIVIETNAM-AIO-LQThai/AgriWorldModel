# Canonical, source-faithful compilation of the Dang 2025 durian study: scientific and implementation analysis

Phase B of the AgriWorldModel evidence programme. Subject: the compiled record
of Dang LV, Quyen NK, Ngoc NP, Ly LM, Thao PTP, Hung NN, *Combining Organic and
Foliar Fertilization to Enhance Soil Fertility and Mitigate Physiological
Disorders of Durian (Durio zibethinus Murr.) Fruit in the Tropics*, *Plants*
2025;14(8):1185, DOI 10.3390/plants14081185 (PDF SHA-256
`5e8a648d…eb0e`, registry id `dang-2025-plants-14-1185`).

## Research question, hypothesis and prespecified success/failure criteria

**Question.** Can the compiled study be rebuilt deterministically from
version-controlled transcriptions alone, without old Git checkouts or
mutation of an already-compiled file, while every derived record says no more
than the source supports?

**Hypotheses tested.**
1. The existing artifact can be reproduced exactly from declarative inputs.
2. The existing transcription is faithful to the PDF.
3. Four semantic defects exist and can be corrected without changing any
   published number:
   - derived contrasts labelled as randomized within-block comparisons;
   - percentage-point differences labelled `%`;
   - post-treatment fruit selection recorded for PD only;
   - Table 5 significance annotations that are internally inconsistent but
     unflagged.

**Prespecified acceptance criteria** (from the approved plan):

| # | Criterion | Result |
|---|---|---|
| 1 | Before any semantic change, the new builder reproduces the committed artifact byte-for-byte | **Met.** LF-normalized SHA-256 `cf0b402f…` for both. The CRLF working copy hashed `64b681f2…`; see line endings below. |
| 2 | Two builds identical; build from a copy without `.git` and in another working directory identical; `--check` passes | **Met.** `1ae0b50d36b22d42…` for every run. |
| 3 | All pre-existing record IDs preserved; 0 changes to published values, SDs, n or contrast effect values | **Met** (564 IDs pinned in `tests/data/dang_2025_pre_phase_b_baseline.csv`). |
| 4 | Every difference of `%` outcomes in percentage points; other units unchanged; validator rejects violations | **Met.** 90 of 252 contrasts. |
| 5 | Table 5 flag lists exactly the computed inconsistent records; no r, star or n altered | **Met.** 17 records. |
| 6 | Exactly the selected-fruit outcomes carry the selection rule; yield, soil and leaf do not | **Met.** 6 outcomes. |
| 7 | Independent PDF verification of every printed input | **Met.** 336 cells, 84 markers, 36 correlations, 0 mismatches. |
| 8 | Full test suite passes; tamper tests fail as intended | **Met.** 213 passed, 0 skipped. All 8 injected errors are caught by pytest after the review fixes. |

## Study/corpus scope, documents and provenance (source identifiers/hashes)

- **Study design.** Ri6 durian, three orchards (D1 Phong Dien, Can Tho; D2
  Chau Thanh and D3 Phung Hiep, Hau Giang), seasons 2022–2023 and 2023–2024.
- **Arms.** Background NPK in all arms; control, organic manure (OM),
  foliar fertilizer (FF), OM+FF.
- **Replication.** RCBD per orchard; three replicates of 12 trees per
  treatment; the physical randomization unit is not reported.
- **Compiled tables:**
  - Table 1: soil chemistry, 120 cells;
  - Table 2: leaf K and Ca, 48 cells;
  - Table 3: fruit proportions, 72 cells (new in this phase);
  - Table 4: yield, aril b*, TSS and PD, 96 cells;
  - Table 5: 36 Pearson correlations.
- **Inputs:** `research/evidence/dang_2025/` (`study.yaml`, `cells.csv`,
  `markers.csv`, `table5.csv`).
- **Verification anchor:** `research/evidence/dang_2025/pdf_extraction.sha256`.
- **Artifact:** `research/evidence/dang_2025_durian.json`.
- **Record diff:** `research/reports/dang-2025-canonical-build_diff.md`.

## Tested environment, code revision, dependencies and exact commands

- **Machine and tools:** Windows 11; project `.venv`, Python 3.12.10; uv
  0.12.5; pypdf 6.19.0; PyYAML 6.0.3; SciPy (locked); no dependency changes.
- **Base revision:** `ddfdd294`. Phase B changes are in the working tree
  until committed.
- **Database:** Postgres/pgvector in Docker, needed only for the existing DB
  tests. Docker Desktop was down during part of the work. The final full-suite
  run was made after it restarted, with the DB host forced to `127.0.0.1` for
  the test process (the configured `localhost` resolves to IPv6 and stalls).

```text
python research/scripts/build_dang_2025.py --check
python research/scripts/build_dang_2025.py --out <path>          # run twice, compare SHA-256
python research/scripts/verify_dang_transcription.py [--write-digest]
python research/scripts/diff_compiled_study.py <old.json> <new.json> <out.md>
python -m pytest -q                                              # DB host 127.0.0.1
```

## Implementation architecture, algorithms, invariants and design tradeoffs

**Inputs.**
- **Printed cells:** every number enters as the verbatim printed string
  (`"13.9 b ± 035"`). The builder parses mean, letter and SD. An SD without a
  decimal point is left `null`, and the build fails unless a flag references
  that record.
- **Family markers:** stored per (table, site, season, variable). Missing,
  duplicate or unused markers abort the build.
- **Table 5:** stores the printed r with the U+2212 minus as printed.
- **Wording and design:** all wording of derived records, outcome definitions
  and hand-authored flags lives in `study.yaml`, so each scientific statement
  is reviewable text, not code.

**Builder** (`src/agriworldmodel/compiled_evidence/dang_2025_build.py`), in
six stages:
1. arm results (record IDs unchanged from the legacy scheme);
2. comparison families;
3. treatment-minus-control contrasts (exact `round(a − b, 10)`; the unit maps
   `%` → `percentage points`);
4. associations;
5. flags: hand-authored, plus computed and evidence-linked ones;
6. metadata consistency checks, then Pydantic validation.

It uses no Git, clock or network. The output is canonical JSON with LF line
endings; `.gitattributes` pins `research/evidence/** text eol=lf`.

**Schema changes** (`compiled-study-1` → `compiled-study-2`):
- `ContrastEvidentialBasis` now has the single value
  `published_arm_mean_difference`.
- The difference-unit rule `difference_unit("%") == "percentage points"` is
  enforced in validation.
- A comparison family may carry no letters only when its printed marker is
  `ns`.

**Verifier** (`dang_2025_verify.py`). Re-parses Tables 1–5 from the PDF with
pypdf, with no code shared with the builder, and compares them
string-for-string with the inputs. With 0 mismatches it can write a digest of
the extraction, which tests compare against the inputs.

**Legacy removal.** The seven mutation scripts (`compile_dang_*`,
`refine_dang_*`) were deleted; their history remains in Git.

**Tradeoffs.**
- Legacy record order was kept for the parity proof (B1). The final artifact
  orders arm results by table (1, 2, 3, 4), and the diff reports this as
  reordering.
- Keeping record IDs stable meant keeping the historical ID
  `flag-pd-post-treatment-selection`, although that flag now covers six
  outcomes.

## Experiment protocol, splits, controls and possible sources of leakage

- **B1 parity.** Inputs were derived mechanically: design text from the
  committed artifact, printed strings from the PDF layout text. The builder
  ran against the unchanged schema, and its output was compared with the
  committed artifact.
- **Independent transcription check.** The planning check used Xpdf layout
  text with its own parser; the committed verifier uses pypdf with another
  parser. Both agree with the inputs.
- **Mutation test.** Eight realistic errors were injected one at a time:
  - code: ignore the percentage-point rule; reverse the contrast sign;
  - data: drop a selection flag; an SD typo; a Table 3 mean typo; an old mean
    typo; a changed Table 5 star; a changed family marker;
  - the last four were made "consistently", i.e. the artifact was rebuilt so
    input and artifact agree.

  For each, the build, pytest, `--check` and the PDF verifier were recorded,
  and the original bytes were then restored and confirmed by hash.
- **Leakage risk.** `study.yaml` was produced from the old artifact, and the
  pre-Phase-B baseline pins old values. These show *no change*, not
  *correctness*. Correctness of the numbers rests on the independent PDF
  re-parse.

## Quantitative results, tables, uncertainty, failure cases and negative results

**Record counts and changes** (from the diff report):

| Section | Before | After | Added | Changed | Unchanged |
|---|---:|---:|---:|---:|---:|
| arm results | 264 | 336 | 72 (Table 3) | 0 | 264 |
| comparison families | 66 | 84 | 18 (Table 3) | 66 (letter-semantics wording) | 0 |
| contrasts | 198 | 252 | 54 (Table 3) | 198 (basis, estimand, assumptions, uncertainty text; 36 units) | 0 |
| associations | 36 | 36 | 0 | 0 | 36 |
| outcomes | 14 | 14 | 0 | 14 (selection audit, sampling rules) | 0 |
| flags | 5 | 8 | 3 | 2 | 3 |

Published means, SDs and n are unchanged for all 264 prior results, and the
effect values of all 198 prior contrasts are unchanged. Example: D3
2023–2024 OM+FF minus control PD = **−12.17 percentage points** (previously
`−12.17 %`).

**Table 5.** Treating the stated n = 72 as independent pairs, the critical
|r| is 0.232 at p < 0.05 and 0.302 at p < 0.01 (two-sided, df = 70).

| Reading of the stars | Disagreements | Records |
|---|---:|---|
| Exclusive bands (`*` = 0.01 ≤ p < 0.05) | 17 of 36 | 7 unmarked plus 10 single-star (below) |
| Inclusive (`*` = any p < 0.05) | 7 of 36 | unmarked with \|r\| ≥ 0.232: Ex.K–AP 0.42; Leaf Ca–pH 0.38; Leaf Ca–AP 0.39; Leaf Ca–Ex.K 0.38; Leaf Ca–Ex.Ca 0.25; yield–pH 0.37; yield–Leaf K 0.31 |

The ten single-star records with |r| ≥ 0.302 are:
- Ex.K–pH 0.51;
- Leaf K with pH 0.55, SOC 0.66, AP 0.51 and Ex.Ca 0.58;
- Leaf Ca–SOC 0.60;
- PD with pH −0.54, AP −0.52, Ex.K −0.54 and Ex.Ca −0.46.

All 17 classifications survive ±0.005 rounding of r. No single n between 6
and 72 makes all stars consistent (planning-stage scan; best n = 16 still
leaves 2 disagreements).

**Selection audit.**
- Flagged as `post_treatment_selection = true`: PD, peel, seed and aril
  proportions, aril b* and TSS (three fruits per replicate, 2.2–2.8 kg,
  without pest damage; Section 4.5).
- Flagged `false`: yield (all fruit weighed) and the soil and leaf outcomes,
  each with its sampling rule from Sections 4.4–4.5.
- The 108 contrasts on selected-fruit outcomes carry an explicit selection
  assumption.

**Table 3 (new).** Six seed-proportion families are printed `ns`, with no
letters. OM+FF minus control ranges across the six strata:
- peel −4.7 to −3.7 pp;
- aril +4.5 to +5.1 pp;
- seed −1.37 to −0.07 pp.

**Mutation results.**

| Injected error | Before the review fixes | After |
|---|---|---|
| Code errors; dropped selection flag; inconsistent SD | caught by pytest and `--check` | caught |
| Consistent Table 3 mean typo | **missed by pytest and `--check`**; caught only by the local PDF verifier | caught by pytest |
| Consistent family-marker change | **missed by pytest and `--check`**; caught only by the PDF verifier | caught by pytest |
| Consistent old-mean typo; Table 5 star change | caught by pytest (baseline, flag text) | caught |

**Negative results and defects found in review:**
1. Consistent transcription errors in data not covered by the old-value
   baseline (Table 3, all family markers) were invisible to the repository
   tests. Fixed with the PDF-extraction digest.
2. Duplicate or unused rows in `markers.csv` were silently overwritten or
   ignored, and duplicate Table 5 pairs were not rejected. Fixed, with tests.
3. The artifact's "byte identity" depended on Git's `core.autocrlf`: the
   working copy was CRLF (`64b681f2…`), the committed blob LF (`cf0b402f…`).
   Fixed by the canonical LF writer and `.gitattributes`.
4. Table 3 had never been compiled although its outcomes were defined.

## Verification of source-grounded facts versus derived computations

- **Source-grounded** (author result or method, with locators): all 336
  printed cells, 84 markers and 36 correlations; n = 3 per cell (all four
  table footnotes); n = 72 for Table 5 (caption); 72 soil samples =
  4 × 3 × 3 × 2 (Section 4.4); the selection rule (Section 4.5); Duncan's
  test at p < 0.05 (Section 4.6).
- **Derived (`our_derived`)**: 252 arithmetic contrasts. They recompute
  exactly in validation and in tests; a changed mean changes exactly its
  three dependent contrasts.
- **Derived checks in flags**: the Table 5 consistency classification (with
  the independence assumption stated in the flag) and the pooling caution.
- **Reported, not resolved**: the conflict between the table footnotes,
  which tie letters to the asterisk levels, and Section 4.6, which states
  Duncan at p < 0.05.
- **Not recorded as a flag (minor)**: the narrative in Section 2.3 gives the
  PD–pH correlation as "−0.54" without a star, while Table 5 prints
  "−0.54 *".

## Scientific interpretation and what is supported by the evidence

- The compiled record now states what the paper reports. Each derived
  contrast is a descriptive difference of two published means (each over
  three replicates) within one orchard and season. It is **not** a
  block-adjusted or causal effect, and it has no uncertainty, because the
  randomization unit and replicate-level data are unavailable.
- The PD and fruit-quality outcomes describe sound fruit of 2.2–2.8 kg, not
  all fruit. A PD difference of about −11 to −12 pp for OM+FF is a
  within-study, selected-fruit contrast of a **treatment package** (OM+FF on
  top of background NPK). It does not support a farm-wide prediction or an
  isolated K or Ca effect.
- Table 5 correlations pool treatments, orchards and seasons. Their printed
  significance cannot be reconciled with n = 72 independent pairs, which is
  consistent with clustered, treatment-driven variation. They support no
  intervention claim; in particular, leaf K and Ca with PD (r = −0.88 and
  −0.91) are post-treatment co-variation.

## Unsupported conclusions, threats to validity and alternative explanations

- **Table 5 stars.** Alternative explanations for the disagreements include
  tests run on fewer or aggregated observations, a different correlation
  procedure, or typesetting errors. None can be distinguished from the
  published data, so the flag records the conditional disagreement only.
- **Letters.** If the footnote reading were intended (letters keyed to the
  omnibus p level), the per-pair semantics would differ. The record keeps
  letters and markers separate and states the ambiguity.
- **Compositional outcomes.** Peel, seed and aril proportions sum to about
  100% of fruit mass, so their contrasts are not independent: a peel decrease
  forces an increase elsewhere.
- **Contrasts on `ns` families.** The 18 seed-proportion contrasts are kept
  as descriptive differences. A consumer must read them together with their
  family's `ns` marker; contrasts do not yet link to their family record.
- **TSS in percentage points.** Treating TSS (%) like the mass percentages is
  dimensionally consistent but assumes %Brix units, which the paper does not
  spell out.
- **Human review of `study.yaml`.** The design layer was carried over from
  the earlier hand-compiled artifact. Only the wording changed in this phase
  was re-reviewed against the PDF.
- **Verifier coverage.** The PDF verifier covers printed table cells, not the
  prose in `study.yaml` (sites, doses, timings), which still relies on review.

## Adversarial criticism and attempted falsification

- *"The build is independent of history."* Tested by building from a copy of
  the four inputs in a fresh directory without `.git`: identical bytes. The
  builder imports nothing that reads Git. Residual dependence: the output
  also depends on the schema code (field order in Pydantic dumps), which is
  intended and versioned.
- *"Tests detect incorrect transcription."* Initially false for consistent
  errors outside the legacy baseline (2 of 8 mutations escaped). After adding
  the extraction digest, 8 of 8 are caught. The digest is only as good as
  the pypdf re-parse it records; that re-parse agreed with an Xpdf re-parse
  in planning.
- *"Semantics stay within scope."* Contrast text was checked for removal of
  "randomized within block", and the flags were checked for overclaiming. The
  Table 5 flag explicitly does not accuse the authors of wrong tests. The
  build would fail if any unparsed SD lacked a flag.
- *"Numbers were not changed."* 564 pinned IDs and values are compared, and
  the diff shows 0 changes to arm results and associations.

## Decisive next experiments, competing alternatives and stop conditions

1. **Phase C, cross-document stress test.** Test whether this schema
   represents the Ca×Mg factorial (an explicit tree unit) and the
   observational Cai Lay survey without forcing trial semantics. The
   Musang King NPK trial needs visual transcription first.
2. **Phase D, typed query.** Use this artifact to test claim typing:
   contrasts as descriptive, associations as non-causal, selection-scoped
   outcomes, and package versus nutrient.
3. **Small follow-ups:**
   - link contrasts to their comparison family;
   - add a `compositional_group` to Table 3 outcomes;
   - record the Section 2.3 star discrepancy;
   - refresh the stale Dang remarks in `docs/CLAUDE.md`.

Stop conditions: any future input edit that changes the PDF-extraction digest
must be re-verified against the PDF before the digest is refreshed. Any
downstream use of a contrast as a causal effect or with invented uncertainty
must be rejected.

## Questions requiring external scientific review

1. Is the conditional Table 5 analysis (17 of 36 under exclusive bands, 7 of
   36 under the inclusive reading) a fair representation, and should
   downstream systems down-weight all 36 associations or only the 17?
2. Should descriptive contrasts be kept for `ns` families, or suppressed in
   claim generation?
3. Is "percentage points" appropriate for TSS differences, or should TSS be
   treated as °Brix?
4. Is attributing the letters to Duncan at α = 0.05 (Section 4.6) the more
   defensible reading than the footnotes?
5. Does representing the package (OM+FF on background NPK) and the
   selected-fruit scope through outcome fields and assumptions suffice for
   Phase D claim boundaries, or does the schema need an explicit
   intervention-package object?
