# Corpus identity and PDF extraction quality: independent scientific discussion

Full analysis: `research/reports/corpus-identity-pdf-quality_analysis.md`
(repository `AIVIETNAM-AIO-LQThai/AgriWorldModel`; Phase A work at commits
`9e2065d` and `6c37802`, plus the A3 changes committed together with this
handoff).

## Question and phase deliverable

AgriWorldModel tests whether explicit inferential type, provenance and study
scope can reduce unsupported agricultural intervention claims compared with
capability-matched LLM/RAG agents, while preserving useful coverage. It
centres on durian nutrient interventions and physiological disorders in
Vietnam.

Phase A asked a prerequisite question: before any document is used as
evidence, can every file and bibliographic work be identified verifiably, and
how often does extracted text misrepresent the rendered page, measured by
document type and by parser?

Deliverables:
- a hash-keyed file manifest and a bibliographic registry with page or
  record locators;
- a deterministic extraction preflight;
- page-level metrics;
- a 42-page visual judgment record;
- a hash-matched external spot-check kept separate from local measurements.

## Experimental setting and source/data scope

- **Corpus:** 14 local PDFs, 12 works, 1,015 pages.
  - 3 intervention trials: Dang et al. 2025 *Plants* (Ri6 durian, organic
    manure and foliar fertilizer); a 2026 Ca(NO3)2 × MgSO4 factorial on
    Musang King; a 2025 Vietnamese NPK-ratio trial on Musang King.
  - 1 observational farmer survey with soil sampling (Cai Lay, 60 farmers,
    20 soil samples).
  - 7 cultivation/technical guides (Malaysia ×2, Vietnam, FAO Lao PDR,
    Indonesia, Philippines ×2).
  - 3 extracts of one ACIAR monograph on *Phytophthora*.
- **Languages:** English, Vietnamese, Malay, Indonesian, Filipino.
- **Environment:** Windows, Python 3.12.10. Project parser **pypdf 6.19.0**
  without a crypto backend. **Xpdf pdftotext 4.06** as a read-only
  diagnostic. External evidence from **PyMuPDF** plus pypdf with crypto, run
  in a separate environment; parser versions there were not recorded.

## Methods and exact implementation references

- Identity: `src/agriworldmodel/corpus/manifest.py` and
  `src/agriworldmodel/corpus/sources.py`, with `data/MANIFEST.csv` and
  `data/SOURCES.csv`. Ingestion resolves PDFs by SHA-256, not by path.
- Preflight: `src/agriworldmodel/corpus/pdf_preflight.py` →
  `research/corpus/extraction_preflight.json`.
- Page metrics: `src/agriworldmodel/corpus/page_metrics.py` →
  `research/corpus/page_extraction_metrics.json`. The sample is pages
  1, n//2+1 and n; low text means fewer than 100 extracted characters.
- Visual judgments: `research/corpus/visual_sample_judgments.csv`.
  External metrics: `research/corpus/external_spotcheck_preflight.csv`.
- Determinism: every script was run twice with byte-identical output.
  176 tests pass (DB host set to 127.0.0.1).

## Key results (including failures), statistics and evidence paths

- **Identity:** 14/14 SHA-256 agree across disk, manifest and external
  evidence. After curation the registry holds 4 DOIs, 6 ISBNs and 7 licence
  or rights statements, all with locators, and 0 fields left unverified.
- **Open failures (pypdf, project environment):** 1/14. The Indonesian
  curriculum is AES-encrypted and no crypto backend is installed. Xpdf and
  PyMuPDF open it (370 pages).
- **Render failures (external, sampled):** 0/42.
- **Low-text pages (pypdf):** trials 0/34, survey 0/13, monograph 0/235,
  readable guides 12/363 (3.3%). Five of the twelve are covers; seven
  interior pages are mostly not visually checked.
- **Confirmed fidelity defects in the project parser:** trials 1/3, survey
  0/1, readable guides 1/6, monograph 0/3.
  - **Musang King NPK trial:** text is garbled by a legacy Vietnamese font
    encoding in pypdf, Xpdf and PyMuPDF alike, although the page renders
    legibly and passes every non-empty-text check.
  - ***Kape* guide:** pypdf returns identical text for page 1 and page 20, so
    the back-cover imprint is attributed to the front cover. Xpdf separates
    the two.
- **Parser-specific anomalies:** PyMuPDF returns 21,415 characters on a
  Ca×Mg table page where pypdf (4,316) and Xpdf (4,437) agree. External pypdf
  with crypto doubles letters on the Indonesian cover; this cannot be
  reproduced locally.
- **Detector:** the legacy-encoding detector flags exactly the NPK file
  (0.131 versus at most 0.0022 elsewhere). Its second signal and threshold
  were set after it missed that very file, so it is fitted to one positive.
  It cannot detect doubled letters or page misattribution.
- **Process failure:** the first registry draft left 6 of 12 works partly
  unverified and missed recoverable DOIs and ISBNs. An independent review
  found 6 avoidable omissions; all were confirmed, and 2 were corrected in
  turn.
- **Carried over from the initial audit** (relevant to choosing the next
  phase):
  - The compiled Dang evidence artifact rebuilds byte-identically from
    history (two runs).
  - Its source Table 5 prints significance markers that disagree with the
    stated n = 72 in 17 of 36 correlations; no single n between 6 and 72
    reconciles them.
  - Three semantic issues remain: an overstated "randomized within block"
    contrast label, PD differences stored in % rather than percentage
    points, and post-treatment fruit selection flagged for PD only.

## Conclusions supported versus unresolved / competing explanations

**Supported:**
- Non-empty extraction is a poor proxy for fidelity: a central trial passes
  every naive check and is unreadable as text.
- Failure modes depend on the parser; output length does not rank parsers.
- File and work identity is now stable under renaming, and monograph parts
  are not double-counted.

**Unresolved:**
- The cause of the *Kape* duplication: a parser bug, or content shared or
  hidden in the PDF.
- Whether the six unseen interior low-text pages are benign.
- How the Malaysia 2012 and 2024 packages relate.
- The Vietnamese journal's registered title versus its printed header.
- Fidelity on table and results pages, which the sampling rule
  under-represents (28 of 42 sampled pages are first or last pages).

**Not addressed:** any scientific claim inside the documents.

## Critical decisions for the next phase

1. **Next phase:** B (make the Dang anchor build canonical and fix its
   semantics), a small A4 (make ingestion respect quality flags and per-file
   parser choice before any RAG baseline exists), or C (cross-document schema
   stress test, which requires visual transcription of the NPK trial).
2. **Baseline fairness in later experiments:** should raw-PDF RAG baselines
   receive the same human-verified text as typed records, or raw extraction?
3. **Garbled NPK trial:** transcribe it manually, find an accessible text
   source, or exclude it until one exists.
4. **Table 5 inconsistency:** a flag only, or a downgrade of all 36
   associations?

## Prompt for independent discussion

Review this phase report as an independent scientific collaborator. Scrutinize
study design, code assumptions, inferential type and applicability boundaries,
baseline fairness, reproducibility, quantitative results and failure cases.
Disagree where warranted. Propose competing interpretations, falsification
experiments and the most defensible next phase. Distinguish evidence from
assumption; do not treat passing tests as proof of a scientific claim.
