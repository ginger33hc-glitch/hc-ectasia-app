# Turkish report consistency audit — 2026-09-08

Scope: Turkish PDF and Word presentation, based on staging commit
`b77499a23af03a679153c7dfa1bb94e2527636d9`. No clinical rule or formula changes.
Production remains outside the authorized deployment scope.

## Findings and corrections

- Report headings were translated, but table cells, decision actions, eye statuses
  and warnings frequently remained in English. Both renderers now apply the shared
  translation owner to presentation text.
- Added consistent Turkish terminology for planning, MMC, ERSS, NICE, PS3, BAD,
  ML7 notes, decision drivers and missing-value markers.
- Corrected partly translated inter-eye findings, joined clinical notes and BAD
  reference ranges. Numeric values, units and comparison signs are preserved.
- Status colors continue to derive from original clinical codes before translation.
- Patient identity, original evidence, source filenames and version identifiers
  are protected from translation. Device screen names and machine identifiers
  intentionally remain literal evidence.
- Word documents now declare Turkish language metadata (`tr-TR`).

## Verification

- Full regression suite: **717 passed**, including nine new Turkish report checks.
- New checks cover PDF/Word translation, four disposition labels and colors,
  numeric/operator preservation, nested notes, protected identifiers, English
  identity behavior and BAD classification presentation.
- A synthetic bilateral sample exercises LASIK PASS, automatic LASIK-to-PRK
  assessment with PTA exactly 40% and STOP-DEFER, BAD amber/red findings, ML7
  notes, source-quality warnings and Turkish names.
- All **11 PDF pages and 9 Word-rendered pages** were visually inspected. No
  clipping, overlapping text or missing Turkish glyphs was observed. Clinical
  values and translated dispositions agree across the two formats.

## Limits and remaining findings

PDF and Word still paginate differently for this comprehensive sample. Identical
page breaks are not claimed. This is a synthetic presentation audit, not a
surgeon-confirmed real-case validation, physical-phone test or archive/reopen test.
The previously documented release-validation gaps remain open.

Deployment success and exact deployed commit must be checked separately after
the staging branch is advanced; this audit records pre-deployment evidence.
