# Source registry curation: corrections, evidence and open items

Scope: `data/SOURCES.csv` (12 bibliographic works covering the 14 local PDFs
listed in `data/MANIFEST.csv`). Values are recorded only where a page of the
document or an official publication record supports them; blank means
unknown. Registry rules are described in `data/README.md`.

## Method

- Local PDFs were read with `pypdf` 6.19.0 (project environment) and, for the
  AES-encrypted file and imprint pages, with Xpdf `pdftotext` 4.06 (read-only,
  no dependency change).
- Registrations were checked in Crossref (DOIs of the four journal articles)
  and, where reachable, the journal landing page. The Vietnamese journal
  landing page returned HTTP 403, so its Crossref record is the evidence.
- The official Department of Agriculture citrus PDF was compared with the
  local copy by SHA-256 (identical: `b22455487af6dfa10ebba40ae54be1c2700df4f371ed6e82125c26cc7fe1d40e`).

## Corrections applied

| source_id | Field | Previous | Now | Evidence |
|---|---|---|---|---|
| khcn-nnmt-2025-07-musang-king-npk | title | descriptive label | official Vietnamese title | Crossref 10.71254/nn5cqx48 |
| | doi / url | blank | 10.71254/nn5cqx48 | Crossref (published 2025-07-30, issue 14, pp. 49-59) |
| | container_title / issuing_body | blank | registered journal and publisher strings | Crossref |
| | study_design_status | curator_assessed | reported_by_source | registered abstract: randomized complete block, 6 treatments, 5 replicates, one tree per unit |
| jad-24-3-cai-lay-durian-soil | doi / url | blank | 10.52997/jad.2.03.2025 | Crossref; JAD article page (vol. 24(3), pp. 12-24, published 2025-06-26) |
| | year | marked unverified | 2025 verified | same records |
| | issuing_body | university with journal in parentheses | Nong Lam University; journal moved to `container_title` | Crossref |
| doa-my-durian-package-2024 | isbn | blank | 978-983-047-329-1 | PDF p. 4 |
| | edition_statement | none | Cetakan Kedua 2024; Edisi Kedua | PDF p. 4 |
| | other_bodies | none | ministry; manuscript preparer | PDF p. 4 |
| vn-durian-climate-smart-handbook-2021 | issuing_body | host ministry and implementer | Nhà xuất bản Nông nghiệp (publisher); host and implementer moved to `other_bodies` | PDF p. 84 (registration 3830-2021, 22 Nov 2021; deposit Q4 2021) and p. 2 |
| | year | marked unverified | 2021 verified | PDF p. 84 |
| id-moa-arabica-gap-postharvest-2019 | all fields | unverified, from the manifest only | title, issuer, co-publishers, ISBN 978-602-9292-40-4, edition Edisi II September 2019 (copyright July 2017) | PDF p. 1 and p. 4 read with `pdftotext` |
| ph-da-car-citrus-propagation-2019 | issuing_body / jurisdiction / year | blank / unverified | DA RFO-CAR; Philippines; 2019 verified; project and printer in `other_bodies` | PDF p. 16 |
| dang-2025-plants-14-1185 | issuing_body | "MDPI (Plants)" | MDPI AG; journal in `container_title`; licence CC BY 4.0 | Crossref; PDF p. 1 |
| tswj-2026-1153166 | issuing_body | journal name | Wiley; journal in `container_title` | Crossref |
| ph-da-rfo12-coffee-guide-undated | study_region | Philippines - Region 12 | Philippines | the guide is national in framing; Region 12 is only the contact office |
| | other_bodies | none | reproducing section and contact office | back cover (PDF p. 20) |
| aciar-monograph-114-2004 | isbn | print only | print and online | colophon, biology part p. 2 |
| jad-24-3-cai-lay-durian-soil, aciar-monograph-114-2004 | edition_statement | — | volume/issue/pages and page extent kept out of this field (moved to `concerns`) | field definition |
| ph-da-car-citrus-propagation-2019 | identifier_locator | — | blank: the record has no DOI or ISBN; URL provenance is in `concerns` | field definition |
| fao-lao-arabica-coffee-manual-2005 | license | "copyright notice" | the stated reproduction terms | PDF p. 2 |

Schema adjustment: three columns were added to `SOURCES.csv` (`container_title`,
`other_bodies`, `edition_statement`) because publisher, journal and
sponsor/implementer roles cannot be held honestly in one field. `source_id`
values and manifest links are unchanged.

## Findings not adopted as proposed

- Publisher of the 2026 *Scientific World Journal* article is recorded as
  "Wiley", as registered in Crossref. The longer legal-entity name was not
  found in any source consulted and was not entered.
- The Vietnamese journal's container title is taken from Crossref
  (*Tạp chí Điện tử về Nông nghiệp và Môi trường*). The PDF running header
  shows a shorter print title (*Nông nghiệp và Môi trường*, Kỳ 2, Tháng
  7/2025). The relationship between the two is
  unresolved and recorded under `concerns`.
- Crossref lists a single author for the Vietnamese NPK article; the PDF
  byline lists three. Both facts are retained; neither is treated as the
  correct author list.

## Remaining uncertainty

- `doa-my-durian-package-2012`: title unverified (cover extracts only as
  "Pakej Teknologi 2012").
- Malaysia 2012 vs 2024 packages: both state *Edisi Kedua*, the ISBNs and page
  counts differ, content overlap has not been compared.
- ACIAR monograph: whether the three local PDFs correspond to ACIAR's hosted
  `mn114-part1/2/3.pdf` files has not been checked. Online ISBN is also listed
  in library catalogues but was read from the colophon only.
- Kape: no official hosting page found; year not established.
- Licences are blank where no article-level licence is stated (the Vietnamese
  NPK article, Cai Lay, the Vietnamese handbook, citrus, Kape).
- The Vietnamese NPK PDF remains unreadable as text (legacy font encoding in
  the file itself); its tables need visual reading before any compilation.
- The Indonesian manual cannot be opened by `pypdf` in the project
  environment (AES encryption without the `cryptography` package); the
  corpus preflight correctly reports `encrypted_unreadable`.
