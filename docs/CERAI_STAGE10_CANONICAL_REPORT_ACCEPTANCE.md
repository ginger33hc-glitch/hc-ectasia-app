# CER-AI Stage 10 — Canonical Report Acceptance

Status: **IMPLEMENTED / LOCAL VALIDATION COMPLETE — 2026-09-07**

## Surviving path

`clinical_core result -> clinical_core/report_payload.py -> reports.py -> PDF or DOCX`

PDF and DOCX consume the same renderer-neutral eye payload. The renderer does not import
ERSS, NICE, BAD-D, PS3, safety, or planning scorers and contains no clinical threshold.

## Retired report architecture

The following import-time or install-time report modifiers were deleted:

- `report_export_guard.py`
- `ps3_report_policy.py`
- `microkeratome_report_policy.py`
- `critical_score_highlight.py`

Their report-only tests were retired because retaining them would require preserving the
deleted wrapper architecture. Equivalent accepted behavior is now covered by
`tests/test_step10_canonical_reports.py` through the single canonical report model.

## Full-report readiness

A complete report is rejected unless every applicable LASIK ERSS row and total, NICE, and
PS3 are complete. A definitive hard stop remains immediately visible as a hard-stop summary,
but no report token is issued until the missing scoring input is completed.

## Required content

Each complete report contains:

- Randleman/ERSS components, points, total, category, and disposition;
- NICE inputs, component points, total, and classification;
- PS3 factor status, exact finding, counts, and procedure disposition;
- Final BAD-D, Df/Db/Dp/Dt/Da, PPI, ARTmax information/QC, and provenance;
- procedural safety results;
- canonical procedure planning and ML7 planning where applicable;
- final decision drivers;
- canonical Pentacam values with source provenance;
- surgeon-entered corrections labeled `SURGEON_CONFIRMED`;
- software, clinical-policy, source-registry, and SRAX-policy versions.

## Local evidence

- Focused Stage 10 and adjacent acceptance set: `56 passed`.
- Complete application suite: `547 passed`.
- All `62` test files passed independently in fresh pytest processes.
- Critical Ruff checks, full Python compilation, and canonical startup invariants: passed.
- Production dependency audit: no known vulnerabilities found.
- PDF and DOCX generation from the same model: passed.
- Rendering immutability check: passed.
- Locked posterior Rmin/topometric RMin distinction and BAD-D provenance: passed.

No push, merge, deployment, or production action is authorized by this document.
