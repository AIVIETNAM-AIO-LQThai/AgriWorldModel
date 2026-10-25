# Dang et al. (2025) compiled study: build inputs

Source: Dang LV et al., *Plants* 2025;14(8):1185, DOI 10.3390/plants14081185
(registry id `dang-2025-plants-14-1185`; PDF located by SHA-256 through
`data/MANIFEST.csv`).

`research/evidence/dang_2025_durian.json` is **generated** from these files and
must not be edited by hand:

| File | Content |
|---|---|
| `study.yaml` | Design, sites, interventions, arms, outcomes (with sampling/selection rules), hand-authored flags, and the wording of derived records (contrasts, comparison families, computed flags). |
| `cells.csv` | One printed table cell per row, verbatim (`13.9 b ± 035`). Mean, letter and SD are parsed from the printed string; an SD without a decimal point is left unresolved and must be covered by a flag. |
| `markers.csv` | The printed p-value marker (`*`, `**`, `***`, `ns`) of each comparison family. |
| `table5.csv` | Printed Pearson r with stars (`−0.54 *`, U+2212 as printed). |
| `pdf_extraction.sha256` | Not a build input. Digest of the printed strings re-parsed from the PDF with pypdf when every input matched (written by `verify_dang_transcription.py --write-digest`). Tests compare the inputs with it, so an edit to any printed string fails without the PDF being present. |

## Commands (repository root, project `.venv`)

```text
python research/scripts/build_dang_2025.py --check          # rebuild in memory, compare with the committed artifact
python research/scripts/build_dang_2025.py --out <path>     # write a fresh build
python research/scripts/verify_dang_transcription.py        # re-parse the local PDF with pypdf and compare every input
python research/scripts/verify_dang_transcription.py --write-digest   # after a verified correction: refresh the digest
python research/scripts/diff_compiled_study.py OLD NEW OUT.md
```

The build reads no Git state, clock or network, and writes LF line endings
(`.gitattributes` pins them for this directory).

## What the build does not do

It does not correct published numbers, infer the randomization unit, derive
standard errors or p-values, or reinterpret Table 5 stars. Disagreements
inside the source are recorded as flags (`flag-table5-markers-inconsistent-
with-n72`, `flag-comparison-letter-semantics-ambiguous`), never repaired.
