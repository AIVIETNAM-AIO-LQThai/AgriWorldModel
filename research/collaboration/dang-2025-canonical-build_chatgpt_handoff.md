# Canonical, source-faithful compilation of the Dang 2025 durian study: independent scientific discussion

Full analysis: `research/reports/dang-2025-canonical-build_analysis.md`.
Record-level diff: `research/reports/dang-2025-canonical-build_diff.md`.
Repository `AIVIETNAM-AIO-LQThai/AgriWorldModel`, base `ddfdd294`, plus the
Phase B change set committed with this handoff.

## Question and phase deliverable

The project tests whether explicit inferential type, provenance and study
scope reduce unsupported agricultural intervention claims compared with
capability-matched LLM/RAG systems.

Phase B made the anchor study's compiled record reproducible from
version-controlled transcriptions, and made it semantically faithful to the
source. The study is Dang et al., *Plants* 2025;14(8):1185, DOI
10.3390/plants14081185: Ri6 durian in three Mekong Delta orchards over two
seasons, RCBD per orchard, 3 replicates × 12 trees, with arms control, OM, FF
and OM+FF on top of background NPK in all arms.

## Experimental setting and source/data scope

- **Compiled tables:**
  - Table 1: soil, 120 printed cells;
  - Table 2: leaf K and Ca, 48;
  - Table 3: peel, seed and aril proportions, 72 (newly compiled);
  - Table 4: yield, aril b*, TSS and PD, 96;
  - Table 5: 36 Pearson r, caption "n = 72".
- **Inputs:** every number enters as the verbatim printed string
  (e.g. `13.9 b ± 035`, where the ambiguous SD is kept null and flagged).
  Design, outcome rules, flags and the wording of derived records live in
  one YAML file.
- **Environment:** Windows, Python 3.12.10, pypdf 6.19.0; no new
  dependencies.

## Methods and exact implementation references

- **Builder:** `src/agriworldmodel/compiled_evidence/dang_2025_build.py`,
  run as `research/scripts/build_dang_2025.py --check | --out`. No Git,
  clock or network; canonical JSON with LF line endings.
- **Verifier:** `research/scripts/verify_dang_transcription.py` re-parses
  Tables 1–5 from the PDF with separate code and compares strings. It
  writes `pdf_extraction.sha256`, which tests use without the PDF.
- **Schema `compiled-study-2`:**
  - the contrast basis is `published_arm_mean_difference`;
  - an absolute difference of `%` outcomes must be in "percentage points";
  - `ns` families may have no letters.
- **Tests:** `tests/test_dang_build.py` covers determinism, a build without
  Git, preserved IDs and values, semantics, and tamper cases. A separate
  harness injected eight errors (mutation testing).

## Key results (including failures), statistics and evidence paths

- **Parity.** Before any semantic change, the builder reproduced the old
  artifact byte-for-byte (LF SHA-256 `cf0b402f…`). The final artifact
  `1ae0b50d…` is identical across two builds and from a copy without `.git`.
- **Transcription.** 336 cells, 84 family markers and 36 correlations match
  an independent pypdf re-parse of the PDF (0 mismatches). An earlier Xpdf
  re-parse matched all 264 legacy cells and 66 markers.
- **Counts.**
  - Arm results 264 → 336, families 66 → 84, contrasts 198 → 252: the
    additions are Table 3.
  - Associations stay at 36; flags go from 5 to 8.
  - 0 published values, SDs or n changed; 0 prior effect values changed.
- **Contrast semantics.**
  - Each contrast is now "difference of two published arm means, each over
    three replicates, in one orchard and season; not a block-adjusted or
    causal estimate; no SE/CI/p; randomization unit not reported".
  - 90 contrasts are in percentage points. Example: D3 2023–2024 OM+FF minus
    control PD = −12.17 pp.
- **Selection audit.**
  - Selected-fruit outcomes (3 fruits per replicate, 2.2–2.8 kg, no pest
    damage): PD, peel, seed and aril proportions, b* and TSS (6 outcomes).
  - Not selected: yield, soil and leaf.
- **Table 5.** Critical |r| at n = 72 is 0.232 (p < 0.05) and 0.302
  (p < 0.01).
  - **17 of 36** printed annotations disagree when stars are read as
    exclusive bands: 7 unmarked correlations with |r| ≥ 0.232, plus 10
    single-starred with |r| ≥ 0.302. Only the 7 disagree under an inclusive
    reading of "*".
  - All 17 survive ±0.005 rounding, and no single n between 6 and 72
    reconciles the stars.
  - r, stars and n are preserved; the flag states the independence
    assumption and does not claim the authors' tests were wrong.
  - A second flag marks Table 5 as pooled, non-independent and
    post-treatment, so its correlations are not intervention evidence.
- **Footnote conflict.** Table footnotes tie letters to the asterisk levels,
  while Section 4.6 states Duncan at p < 0.05. This is recorded as a flag,
  not resolved.
- **Failures found in review:**
  - 2 of 8 injected "consistent" errors (a Table 3 mean, a family marker,
    each changed in both the input and the rebuilt artifact) escaped pytest
    and `--check`; only the local PDF verifier caught them. The committed
    extraction digest fixed this: 8 of 8 are now caught by pytest.
  - Duplicate or unused marker rows were silently accepted (fixed).
  - Artifact "byte identity" depended on Git's CRLF conversion (fixed with
    LF output and `.gitattributes`).
- **Tests:** 213 passed, 0 skipped (DB host 127.0.0.1).

## Conclusions supported versus unresolved / competing explanations

**Supported:**
- The compiled record is reproducible from versioned inputs and faithful to
  the printed tables.
- Its derived records now claim only descriptive arm-mean differences within
  a selected-fruit scope, for a treatment package.

**Unresolved:**
- What produced the Table 5 stars: fewer or aggregated observations, a
  different test, or typesetting.
- The intended letter semantics.
- Whether TSS should be in pp or °Brix.
- How to treat descriptive contrasts on `ns` families.
- The compositional dependence of peel, seed and aril contrasts.
- The prose design layer (sites, doses, timings), which the verifier does
  not cover.

## Critical decisions for the next phase

1. **Phase C:** cross-document schema stress test (Ca×Mg factorial, Cai Lay
   survey, Malaysian guide; the NPK trial needs visual transcription), or go
   straight to Phase D claim-boundary queries on this artifact?
2. Should claim generation suppress contrasts from `ns` families and
   down-weight all Table 5 associations?
3. Does the schema need an explicit intervention-package object, rather
   than per-arm intervention lists plus assumptions?

## Prompt for independent discussion

Review this phase report as an independent scientific collaborator. Scrutinize
study design, code assumptions, inferential type and applicability boundaries,
baseline fairness, reproducibility, quantitative results and failure cases.
Disagree where warranted. Propose competing interpretations, falsification
experiments and the most defensible next phase. Distinguish evidence from
assumption; do not treat passing tests as proof of a scientific claim.
