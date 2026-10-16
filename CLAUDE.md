# AgriWorldModel

Evidence-scoped agricultural decision research (durian first); not an
already-validated world model. The full operating contract, scientific
invariants and phase list are in [docs/CLAUDE.md](docs/CLAUDE.md) — read
it before planning or coding.

## Workflow
- Each code-bearing work unit: PLAN (Opus 5.5, High; no edits) then CODE
  (Sonnet 5.5, Medium; High for validators/migrations) after approval.
- Verify the active model/effort from session metadata; never substitute
  silently. The session cannot switch itself — ask the user.
- Phase-gate reviews (Opus 5.5, High) write
  `research/reports/<phase-slug>_analysis.md` and
  `research/collaboration/<phase-slug>_chatgpt_handoff.md`, then stop.
  No byline, model or ownership language in those files.

## Hard rules
- Never run `git add`, `commit` or `push`; the user does. Read-only git is
  fine. Propose PowerShell commands; commit messages carry no attribution
  trailers.
- No `uv sync`, global pip, new venv, CUDA/Python changes, DB reset, data
  moves/deletes, or OCR/embedding runs without explicit approval.
- Use the repo `.venv` (Python 3.12). If DB commands hang, check that
  `DATABASE_URL` uses `127.0.0.1`, not `localhost` (IPv6 stall).
- Association != intervention effect; treatment package != isolated
  nutrient; post-treatment measurements != pretreatment modifiers.
- Do not print `.env` values or commit third-party PDFs.

## Style
~80-column wrapping target, natural layout, short intent comments before
non-obvious functions and stages; tests include adversarial cases.
