# Corpus identity and PDF extraction quality: scientific and implementation analysis

Phase A of the AgriWorldModel evidence programme. Scope: the 14 local PDFs
(12 bibliographic works) under `data/`, their identity records, and how
faithfully their text can be extracted by the project's toolchain. This phase
makes no claim about the scientific content of any source.

## Research question, hypothesis and prespecified success/failure criteria

**Question.** Before any document is used as evidence, can we (a) establish a
stable, verifiable identity for every file and bibliographic work, and
(b) measure, by document type and by parser, how often extracted text
misrepresents the rendered page?

**Working hypothesis.** "The parser returned text" is a poor proxy for
fidelity: some files that pass naive non-empty checks carry corrupted or
misplaced text, and failure modes differ by parser and document type.

**Prespecified criteria** (from the A1–A3 plans):

- Identity: every PDF has exactly one manifest row whose SHA-256 matches the
  bytes on disk; every row links to one registered work; identifiers and
  licences carry a page or record locator; unknown stays blank. *Failure:*
  any unmatched hash, orphan row/work, or identifier without a locator.
- Preflight (A1): the known garbled file (Musang King NPK) is flagged; the
  encrypted manual is reported; the three Phytophthora extracts are linked;
  the Dang, Ca×Mg and Vietnamese-handbook files are not flagged. Output is
  byte-identical across reruns.
- Page-level audit (A3): open failures, render failures, low-text pages and
  visually supported fidelity problems are reported **separately**, per
  document type and per parser, never as one pooled rate.

## Study/corpus scope, documents and provenance (source identifiers/hashes)

| Type (folder) | Files | Works | Pages | Files (registry `source_id`) |
|---|---:|---:|---:|---|
| Intervention trials (`techniques_research`) | 3 | 3 | 34 | `dang-2025-plants-14-1185`, `tswj-2026-1153166`, `khcn-nnmt-2025-07-musang-king-npk` |
| Observational survey (`observationals`) | 1 | 1 | 13 | `jad-24-3-cai-lay-durian-soil` |
| Cultivation / technical guides (`nursing_guides`) | 7 | 7 | 733 | two Malaysian packages, Vietnamese handbook, FAO Lao, Indonesian GAP curriculum, Philippine *Kape*, Philippine citrus |
| Disease monograph extracts (`diseases`) | 3 | 1 | 235 | `aciar-monograph-114-2004` (three parts) |
| **Total** | **14** | **12** | **1,015** | |

All 14 SHA-256 values are in `data/MANIFEST.csv` and, per work, in
`data/SOURCES.csv`. Selected anchors:
Dang `5e8a648d…eb0e` (DOI 10.3390/plants14081185);
Musang King NPK `ae52151b…f1dc` (DOI 10.71254/nn5cqx48);
Ca×Mg `e056d748…c449` (DOI 10.1155/tswj/1153166);
Cai Lay `42d8813e…899a` (DOI 10.52997/jad.2.03.2025);
Indonesian curriculum `d78db5b4…59ce` (ISBN 978-602-9292-40-4).
Two exact duplicates in the original download were dropped before this phase
(`data/DUPLICATES.csv`). The PDFs are third-party documents and are not
tracked in Git (`.gitignore: data/**/*.pdf`); only metadata and derived
metrics are committed.

Registry coverage after curation: 4 DOIs, 6 ISBNs, 7 licence or rights
statements with locators, 5 official URLs, 0 fields left in
`unverified_fields`. Remaining open bibliographic questions are listed under
*Unsupported conclusions* below.

## Tested environment, code revision, dependencies and exact commands

- Windows 11; repository `.venv` with Python 3.12.10; uv 0.12.5;
  `uv sync --locked --offline --dry-run` reported no changes.
- Parsers: **pypdf 6.19.0** (project dependency, used by ingestion);
  **Xpdf `pdftotext` 4.06** from Git for Windows, used only as a read-only
  diagnostic and not a project dependency; `cryptography` is **not**
  installed, so pypdf cannot open AES-encrypted files.
- External evidence: a hash-matched spot-check run in a separate Python
  environment with **PyMuPDF** and **pypdf with a crypto backend**; parser
  versions were not recorded in that evidence.
- Revisions: A1 `9e2065d`; A2 and registry curation `6c37802`; A3 changes
  are in the working tree at the time of writing (see the commit commands
  accompanying this report).
- Database: Postgres 17 + pgvector 0.8.6 in Docker, Alembic head
  `680aa39700b6`. With the configured host `localhost`, connections resolve to
  `::1` and stall indefinitely; DB-backed tests were run with the host forced
  to `127.0.0.1` for that process only.

Commands (PowerShell, repository root):

```text
.venv\Scripts\python.exe research\scripts\audit_corpus.py --root . --out research\corpus\extraction_preflight.json
.venv\Scripts\python.exe research\scripts\page_extraction_metrics.py --root . --out research\corpus\page_extraction_metrics.json
.venv\Scripts\python.exe research\scripts\check_db_source_identity.py
.venv\Scripts\python.exe scripts\ingest_durian_source.py        # dry run
.venv\Scripts\python.exe -m pytest -q                            # needs DATABASE_URL host 127.0.0.1
pdftotext -enc UTF-8 -f <p> -l <p> <file.pdf> <out.txt>          # diagnostic only
```

Each script was run twice; outputs were byte-identical
(`extraction_preflight.json` `50351935…`, `page_extraction_metrics.json`
`72ce19a2…`). Test suite: **176 passed, 0 skipped** (DB host `127.0.0.1`).

## Implementation architecture, algorithms, invariants and design tradeoffs

- `src/agriworldmodel/corpus/manifest.py` — file identity: one manifest row
  per PDF, SHA-256 match, naming convention, folder versus topic, duplicate
  log consistency.
- `src/agriworldmodel/corpus/sources.py` — work identity: `SOURCES.csv`
  schema (journal in `container_title`, publisher in `issuing_body`,
  role-tagged `other_bodies`, verbatim `edition_statement`), locator rules,
  file→work links, `resolve_pdf_by_sha256` (ingestion no longer depends on
  paths), and a read-only reconciliation of database source rows by hash.
- `src/agriworldmodel/corpus/pdf_preflight.py` — document-level triage:
  open/encryption failure, near-empty pages (<40 chars), low text density,
  a legacy-Vietnamese-encoding signature, and shared front matter between
  files.
- `src/agriworldmodel/corpus/page_metrics.py` — page-level metrics: a
  deterministic sample (pages 1, n//2+1, n), low-text pages (<100 chars) by
  document type, and unreadable documents counted apart from page rates.
- Evidence files: `research/corpus/visual_sample_judgments.csv` (42 sampled
  pages: render status, page kind, fidelity finding, affected parser,
  evidence source) and `research/corpus/external_spotcheck_preflight.csv`
  (external metrics with a provenance header; not pooled with local ones).

Invariants: PDF bytes are never modified (aggregate hash unchanged
throughout); outputs carry no timestamps; flags are triage hints and never
drop a file; external and local measurements stay in separate files.

Tradeoffs: CSV over a nested provenance format keeps the registry editable by
hand at the cost of one locator per field group rather than per field. Using
pypdf only in committed code keeps runs reproducible from `uv.lock`; Xpdf and
PyMuPDF evidence is therefore documented but not regenerated by the scripts.

## Experiment protocol, splits, controls and possible sources of leakage

- **Identity:** hashes recomputed locally and compared with the manifest and
  the external evidence (three-way).
- **Page sample:** first, middle and last page of every file (42 pages). The
  rule is deterministic and identical locally and externally. It is not
  random and over-represents covers and back matter.
- **Visual evidence:** contact-sheet renders of the 42 pages from the
  external, hash-matched spot-check. Thumbnails support render and layout
  judgments, not character-level comparison.
- **Fidelity labels:** taken from (i) visual comparison reported with the
  external evidence, (ii) local cross-parser comparison (pypdf against Xpdf),
  or (iii) the local detector, marked `signal_only`. Detector hits are never
  counted as confirmed.
- **Leakage / circularity risks:**
  1. The detector's second signal (digits/punctuation inside words) and its
     0.02 threshold were set after the first signal missed the one known
     positive, so the detector is fitted to a single case.
  2. The A1 acceptance list of expected flags was written from prior
     knowledge of the corpus. Agreement with it shows consistency, not
     detection power.
  3. "No issue reported" on a page means only that no problem was observed in
     a thumbnail or reported. It is not verification.

## Quantitative results, tables, uncertainty, failure cases and negative results

**Identity.** 14/14 hashes match across disk, manifest and external evidence;
0 manifest or registry issues. The single database source row resolves by
hash to `dang-2025-plants-14-1185`, flagged `stale_filename` and
`no_source_id`. The ingestion dry run resolves the renamed file and reproduces
the 34 stored chunks without loading a model.

**Separate rates** (pypdf, project environment, unless stated):

| Measure | Trials | Survey | Guides | Monograph | Note |
|---|---|---|---|---|---|
| Files that fail to open | 0/3 | 0/1 | **1/7** | 0/3 | Indonesian curriculum, AES encryption without a crypto backend. Xpdf and PyMuPDF open it (370 pages). |
| Sampled pages that fail to render (external) | 0/9 | 0/3 | 0/21 | 0/9 | Renderer: PyMuPDF |
| Low-text pages (<100 chars) | 0/34 | 0/13 | **12/363** (3.3%) | 0/235 | Readable guides only. External PyMuPDF: 9/363 on the same six, 24/370 on the Indonesian file. |
| Files with a confirmed fidelity defect in the project parser | **1/3** | 0/1 | **1/6 readable** | 0/3 | Defects listed below |

**Fidelity defects, by parser:**

| File | pypdf (project) | Xpdf (local) | PyMuPDF (external) | Evidence |
|---|---|---|---|---|
| Musang King NPK trial | corrupt (legacy font encoding) | corrupt | corrupt | visual comparison; detector fractions 0.176 / 0.150 / 0.043 on sampled pages |
| *Kape* guide | page attribution error: identical text on p. 1 and p. 20 | correct | correct (4 chars on cover) | local cross-parser comparison |
| Indonesian curriculum | cannot open (locally) / doubled letters (external pypdf) | readable | readable | external report; not reproducible locally |
| Ca×Mg trial | consistent (4,316 chars on p. 6) | consistent (4,437) | oversized output (21,415; p. 10: 17,702 vs 7,694) | external numbers plus local cross-check; p. 10 evidence is weak |
| ACIAR disease-management extract | — | — | — | rotated table on p. 84: a layout risk for numeric extraction, not a text defect |

**Detector performance (document level, 13 readable files).** The detector
flagged 1 file (Musang King NPK, token fraction 0.131); the next-highest
score was 0.0022. With one positive and twelve negatives this establishes
neither sensitivity nor specificity. Page-level fractions are unstable on
short pages: *Kape* p. 11 scores 0.154 over 13 tokens with no corruption
visible.

**Negative results.**
- The A1 detector **cannot see** the second corruption mode found (doubled
  letters in the Indonesian file under some pypdf builds) nor page
  misattribution (*Kape*). Both pass every A1 metric.
- The first detector version **missed** the known positive: title-symbol
  tokens were 0.004 of tokens against a 0.02 threshold.
- The first front-matter fingerprint (300 characters) **failed** to link the
  three Phytophthora extracts. A 100-character slice links them.

**Uncertainty.** All counts are exact for the files and pages examined. No
interval is given for page-level fidelity, because the page sample is
neither random nor large (42 of 1,015 pages, about 4%) and labels come from
heterogeneous evidence.

## Verification of source-grounded facts versus derived computations

- **Source-grounded** (page or record locator in `SOURCES.csv`): titles,
  publishers, ISBNs, DOIs, edition statements, licences. Of these, 4 DOIs and
  dates come from Crossref records, 1 URL is confirmed by byte-identical
  download (DA citrus PDF), and the rest come from page text read with pypdf
  or Xpdf, or from hash-matched renders.
- **Derived** (computed here): hashes, page counts, character counts,
  low-text rates, detector fractions, cross-parser agreement.
- **Not verified:** the content of the external review beyond its numbers.
  Its claims were accepted only where they could be checked locally or seen
  in the renders.
- **Curation error rate, as a process finding.** The first registry draft
  left 6 of 12 works with unverified fields and missed recoverable DOIs and
  ISBNs. An independent review identified 6 avoidable omissions. All 6 were
  confirmed; 2 of them were corrected in turn (the journal naming for the
  Vietnamese NPK article, and the publisher entity for the TSWJ article).
  Root causes: giving up after one parser failed, and not consulting
  registration records.

## Scientific interpretation and what is supported by the evidence

Supported:

1. Naive extraction checks are insufficient. A trial whose numeric tables
   are central to Phase C (the Musang King NPK trial) passes every page-has-
   text check yet is unreadable as text in all three parsers tried.
2. Failure modes are parser-specific and cannot be ranked by output length:
   PyMuPDF over-produces on one table-heavy page where pypdf and Xpdf agree;
   pypdf misplaces text on one guide; pypdf cannot open one file in this
   environment.
3. Document identity is now stable under renames (hash-keyed), and parts of
   one work are not counted as independent sources.

Not supported by this phase: anything about the scientific claims of the
documents, the correctness of extracted numbers on pages not inspected, or
the general reliability of any parser.

## Unsupported conclusions, threats to validity and alternative explanations

- **External validity.** The 14 files are a convenience corpus (one crop
  family dominant; Vietnamese, Malay, Indonesian, Filipino and English). The
  failure rates do not transfer to a larger corpus.
- **Sampling bias.** First and last pages are 28 of 42 sampled pages; tables
  and results pages, where numeric fidelity matters most, are
  under-represented. Targeted table pages were proposed but not sampled.
- **Alternative explanation for *Kape*.** The duplicated text may come from a
  shared content stream or an off-page layer drawn on both pages, rather than
  from a pypdf bug. The root cause is not established; the consequence (wrong
  page locator) holds either way.
- **Indonesian file.** The doubled-letter result depends on the pypdf build
  and crypto backend used externally. Locally the file does not open at all
  in pypdf.
- **Visual evidence.** The renders came from the external environment.
  Their hash match establishes which bytes were rendered, not how faithfully
  that renderer draws them.
- **Open bibliographic questions.** How the Malaysia 2012 and 2024 packages
  relate (both "Edisi Kedua", different ISBNs, 62 vs 108 pages). The
  Vietnamese NPK journal's registered title versus its printed header. Whether
  the three Phytophthora files match ACIAR's hosted parts. *Kape*'s year and
  official URL.

## Adversarial criticism and attempted falsification

- *"The detector works."* Not shown: it was tuned after failing on its only
  positive and has not been tested on a new positive. A falsification test
  would apply it, unchanged, to newly added Vietnamese PDFs with known
  encoding status.
- *"Low text equals failure."* Not established either way. All 12 low-text
  pages are in guides. Five are front or back covers (citrus p. 1; Malaysia
  2012 pp. 1 and 62; Malaysia 2024 p. 1; Vietnamese handbook p. 1). Seven are
  interior pages (Lao pp. 4, 6, 70; *Kape* pp. 11–12; Vietnamese handbook
  pp. 7, 37). Of those seven, only *Kape* p. 11 was seen in a render, where
  it is a diagram. The other six interior pages need a visual check before
  they are called benign.
- *"Hash-matched external evidence can be pooled with local metrics."*
  Rejected: the parsers and versions differ, and pypdf counts differ by a few
  characters between environments. The files are kept separate.
- *"Registry values are correct because tests pass."* Rejected: the tests
  check structure and pin values. Correctness rests on locators and review;
  one review round already found avoidable omissions.

## Decisive next experiments, competing alternatives and stop conditions

Competing next steps (the choice is external to this report):

1. **Phase B: reproducible Dang build.** The final artifact already rebuilds
   byte-identically (`64b681f2…`, two runs) from the design JSON at
   `31a3b67`, but transcription is spread over scripts and history.
   Unflagged semantic issues found in the initial audit:
   - Table 5 significance markers disagree with the stated n = 72 in 17 of
     36 cells, and no single n between 6 and 72 reconciles them.
   - The contrast label `randomized_within_block` overstates a design whose
     randomization unit is not reported.
   - PD differences are stored as `%` rather than percentage points.
   - Post-treatment fruit selection is flagged for PD only.

   Dang text extracts cleanly, so Phase A findings do not block B.
2. **A4: ingestion quality gating** (small). Make ingestion consult the
   registry and quality flags: quarantine the NPK text, choose a parser per
   file with an audit trail, fix page locators for *Kape*. This is needed
   before any RAG baseline is built, so the baseline is not handicapped by
   corrupted text the typed system avoids through manual transcription.
3. **Phase C prerequisite.** The Musang King NPK trial cannot be compiled
   from text. It needs visual transcription or another accessible source,
   and the two Musang King trials share a site and first author, so they are
   not independent.

Stop conditions to carry forward: if any later comparison would give the
typed system manually transcribed text while baselines get raw garbled
extraction, stop and equalize inputs. If a new Vietnamese file is added
without a re-run of the preflight and visual sample, do not ingest it.

## Questions requiring external scientific review

1. Is a deterministic first/middle/last sample adequate for Phase A, or
   should targeted table and results pages be required before any trial is
   compiled?
2. For fair Phase E baselines, should raw-PDF RAG receive the same
   human-verified text used for typed records, or the raw extraction?
3. Should corrupted-but-renderable sources such as the NPK trial be
   transcribed manually (cost, error) or excluded until an accessible text
   source exists?
4. Is Phase B (anchor reproducibility and semantics) the right next phase,
   ahead of A4 gating or C cross-document stress testing?
5. How should the Table 5 inconsistency be represented: a source anomaly
   flag only, or a reason to downgrade all 36 associations?
