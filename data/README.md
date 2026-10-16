# Renamed agricultural data corpus

## Naming convention

`<region>__<crop-or-cultivar>__<specific-subject>__<document-role>__<year>.pdf`

- Lowercase file names.
- Hyphens separate words inside one field.
- Double underscores separate semantic fields.
- Author names are intentionally omitted.
- Region reflects the study/source geography, not the author.
- The folder indicates the **primary knowledge theme**.
- `MANIFEST.csv` stores secondary themes and epistemic/document role.

## Primary topics

- `nursing_guides/` — cultivation, GAP, propagation, irrigation, harvest, post-harvest and operational manuals.
- `techniques_research/` — experimental studies of agricultural interventions/techniques.
- `diseases/` — disease/pathogen biology, diagnosis and management references.
- `observationals/` — surveys, orchard measurements, field observations and later image collections.
- `market/` — reserved for price, production, trade and market reports.
- `plant_attributes/` — reserved for varieties, genetics, breeding, phenology, adaptability and trait studies.
- `policies_laws/` — reserved for regulations, registrations, standards, export rules and other legal sources.

## Important ambiguity warnings

1. `arabica-phi.pdf` is **not Arabica-only**. It covers Arabica, Robusta, Excelsa and Liberica. No publication year is printed; PDF metadata indicates 2017, but the renamed file uses `undated`.
2. `arabica-postharvest-phi.pdf` is **Indonesian**, not Philippine material. It is Edition II (September 2019); the underlying copyright started in 2017.
3. `CITRUS-PRODUCTION-Philippines.pdf` is specifically a **vegetative propagation** technoguide rather than a full citrus production manual.
4. The three Phytophthora PDFs are extracts/sections from the **same parent ACIAR Monograph 114 (2004)**. Treat them as one bibliographic source with multiple sections, not as three independent studies.
5. The 2024 Malaysia durian package opens with `Jabatan Pertanian 2023`, while the publication page states `Cetakan Kedua 2024, Edisi Kedua`. The renamed file uses 2024.
6. The Musang King NPK trial has problematic embedded-font text extraction. It is readable visually, but automatic text extraction/RAG may be garbled and should be checked.
7. Two exact duplicate file pairs were found and only one canonical copy of each is retained. See `DUPLICATES.csv`.

## Duplicate policy

Exact duplicates were not copied twice into this cleaned corpus. The original-to-canonical mapping is recorded in `DUPLICATES.csv`.
