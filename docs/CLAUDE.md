# AgriWorldModel — Claude Code persistent operating contract

**Purpose:** Evidence-scoped agricultural decision research, not an already-validated biological world model. Before suggesting actions, distinguish farm observations, intervention arm results, randomized arm-mean arithmetic, Pearson association, author interpretation, guidelines, regulation and independently justified farm-level applicability.

**Research question:** Does explicit inferential type + provenance + study-scope enforcement reduce unsupported agricultural intervention claims and unnecessary information requests while preserving useful claim coverage, compared with capability-matched LLM/RAG systems?

**Governance:** User decides. Claude Code operates and codes. Claude Opus and ChatGPT independently critique meaningful research milestones. Treat expert interpretation, source support and empirical falsification above confident prose. Do not add labels like V1/V2 in new research concepts.

## Model and effort by role

1. **PLAN (every scoped coding work unit): Opus 5.5, High**. Inspect and propose objective, alternatives, exact files, invariants, tests, runtime cost and phase gate. No edits.
2. **CODE (after approved plan): Sonnet 5.5, Medium** for straightforward scripts/tests, **High** for fragile migrations, validators, source-quality issues or integration. Implement, validate using actual local environment, report failures and diffs.
3. **PHASE SCIENTIFIC REVIEW (not on every passing test): Opus 5.5, High**. Challenge conclusions, inspect actual results, generate a self-contained ChatGPT collaboration handoff and STOP before next major phase until independent feedback/user decision.

Verify actual model/version/effort using session controls; model family aliases may change. If exact version isn't available or switching cannot be verified, ask rather than silently substitute. Do not claim another model was used when it wasn't.

## Local runtime and safety

- Windows PowerShell; existing repo `.venv`; Python `>=3.12,<3.13`; `uv.lock`; Postgres/pgvector in local Docker; optional GPU, BGE-M3, reranker, LM Studio Qwen. **Verify actual configuration every session.**
- Record `git status`, branch, HEAD SHA, `sys.executable`, Python/uv/torch/CUDA, Docker/test dependencies before jobs. Don't run on a different computer or venv and call it comparable.
- No silent `uv sync`, global pip, CUDA reinstall, Python upgrade, extra venv, costly remote API smoke, simultaneous GPU model loads if VRAM tight, DB reset, data move/delete, force push, or hidden test skips.
- Do not print credentials/environment secrets or private farm identifiers in logs/ChatGPT reports.
- Never overwrite uncommitted work. **Never stage, commit or push Git changes yourself**, even with general permission; the user performs these operations manually.

## Scientific invariants

- Association != intervention effect; package != isolated nutrient effect; post-treatment leaf nutrient levels != pretreatment effect modifiers.
- Study-specific treatment arm differences are not calibrated target-farm predictions or pairwise SE/CI with only summary data.
- Preserve controls/background NPK, cultivar, region, treatment/version/dose/timing, outcome definition and fruit-selection rule.
- `OUR_DERIVED` values must recompute exactly and trace to source arm records; manuscript anomalies remain flagged, never quietly repaired.
- Study-scope transfer demands explicit support/assumptions, never invented scalar applicability scores. Unknown stays unknown.
- Clinical-style or farm-wide incidence claims are not licensed by selected-fruit PD sampling.
- No biological simulator, probabilistic VOI, latent belief state, inferred causal mediator, automatic effect modifiers or multi-agent system without separate data and review.
- Benchmarks must include strong fair baselines, held-out expert-judged cases, **useful claim coverage alongside error rate**, counterexamples and documented failures.

## Planned scientific phases and phase-gate reports

A. **Corpus identity + PDF extraction audit** — user topic taxonomy, manifest, hashes, duplicate/parent links, extraction quality. No OCR by default; inspect corrupted text visually. Gate = quantified quality/ambiguity findings on trial vs survey vs guide.

B. **Reproducible Dang compilation** — immutable manual transcription source, deterministic build, identical rebuild, comparison families, derived contrasts, provenance and anomaly flags. Gate = independent rebuild and scientific audit.

C. **Cross-document schema stress test** — Can Tho Musang King NPK trial, Cai Lay observational survey, Malaysia durian guide; adapt ontology only on true need. Gate = evidence-supported schema/generalization critique.

D. **Typed evidence query / claim boundary** — deterministic inferential separation, full stratum inclusion, package integrity, study support/limits, no unsupported transfer. Gate = adversarial claim-boundary cases.

E. **Controlled comparisons** — raw/hybrid RAG, typed text, typed tool, claim enforcement under equivalent access and costs; pre-registered and held-out cases. Gate = empirical coverage/error results and limitations.

F. **Conditional farm decision integration** — only if experiments justify: bitemporal farm snapshot, hard constraints, limited ACT/WAIT/MEASURE/ESCALATE and decision-relevant information requests.

**For every work unit**: PLAN -> CODE. At a **predeclared meaningful phase gate**, perform Opus scientific review and write **both**:
- `research/reports/<phase-slug>_analysis.md` — full phase analysis: hypothesis, plan, scientific source references/hashes, environment/code revision, implementation and invariants, exact experiment commands/results, quantitative metrics, failures/ablations/negative results, limits/confounders, adversarial analysis, falsification proposals and decisions;
- `research/collaboration/<phase-slug>_chatgpt_handoff.md` — concise, self-contained technical context + critical questions and a **ready-to-paste prompt for independent ChatGPT discussion**. Refer to the complete local analysis file; report actual paths.

**Reports are about the research, not their writers.** No authorship/bylines/ownership, "Claude wrote", "ChatGPT wrote", AI model attribution, credit sharing, generated-by boilerplate or section headings naming the reviewer model. Preserve scholarly source provenance, experiment model identifiers used as research variables, file hashes and Git SHAs when necessary for reproducibility. Do not present a model's identity as the author of the report. Separate observed evidence from inference and assumptions. **No handoff for unit-test green status alone.** The user manually shares the report with ChatGPT unless a real authorized integration exists. Pause before the next major phase; the user decides after discussion.

## Repository starting facts (always re-check)

Latest main seen by ChatGPT on 2026-10-15: `a1cf86de` (2026-10-04).
- `research/evidence/dang_2025_durian.json`: 264 arm results, 66 comparison families, 36 associations, 198 derived contrasts, 5 flags.
- `src/agriworldmodel/compiled_evidence/`: scientific schemas and validation.
- `src/agriworldmodel/retrieval/`: BGE-M3, hybrid/FTS and reranking.
- `src/agriworldmodel/decisions/evidence_packet.py`: still uses raw reranked chunks; typed evidence not integrated.
- `scripts/ingest_durian_source.py`: old hardcoded Dang source path; compare against local reorganized `data/` corpus.
- Existing `research/scripts/` mutate the Dang JSON; clean deterministic reproduction is unproven.

## Git responsibility — exclusively user-controlled

- Claude Code can **inspect** with `git status`, `git diff`, `git log`, and `git show` but must NEVER execute `git add`, `git commit`, `git push` or equivalent Git-write API actions. Do not execute merge/rebase/reset/clean/branch moves without separate approval.
- After a coherent reviewed change, provide a **copy-paste Windows PowerShell Git sequence** targeting the actual changed paths: `git add -- <paths>`, `git commit -m "<meaningful technical/scientific change>"`, `git push` (adjust for verified tracking branch). The user runs it. Do not claim a commit or push has occurred without observing updated Git state.
- Commit messages describe the **change and research consequence**, not ownership. Never propose author/model identifiers, credit statements, `Co-authored-by`, `Signed-off-by`, `Generated-by`, or similar trailers. Example: `refactor: make evidence compilation reproducible`.

## Code style and implementation explanations

- Prefer **natural, compact code** rather than robotic line breaks. Target roughly **80 total characters including indentation** before wrapping a line that genuinely needs wrapping: approximately `80 - indent_spaces` available code characters. Do not turn simple `if`, `for`, signatures, expressions or calls into stacks of tiny lines. The 80-column guideline is a **wrapping target**, not a required minimum: never pad short lines or sacrifice readability/syntax. Multiline dictionaries, data/type initializations, genuinely complex expressions and existing formatter conventions are acceptable.
- Keep control flow transparent and validation logic auditable. Put short, meaningful **intent/why** comments before nontrivial functions, important `for`/`while` loops and coherent implementation stages. Explain assumptions, invariants, failure behavior and scientific inference restrictions. Don't add a comment to every assignment or simply restate the code. Use precise naming and docstrings for complex public interfaces.

Keep plans/results in `research/`, avoid broad refactors and unrequested new dependencies. On any meaningful contradiction, **stop and replan in Opus before further coding**.
