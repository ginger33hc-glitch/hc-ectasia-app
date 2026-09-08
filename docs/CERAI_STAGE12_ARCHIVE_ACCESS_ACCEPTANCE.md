# CER-AI Stage 12 — Archive and Access Acceptance

Status: **IMPLEMENTED / LOCAL VALIDATION COMPLETE — 2026-09-07**

## Surviving persistence path

`assessment_workflow -> CaseArchiveRuntime -> encrypted sources + canonical snapshot + immutable original reports + encrypted catalog + audit event`

`case_archive.py` is the sole write coordinator. It does not replace upload, workflow,
export, PDF, or DOCX functions. `case_catalog.py` owns searchable encrypted catalog data and
authorized archive routes, but no longer wraps `assessment_workflow.begin` or
`assessment_workflow.complete`.

## Retired architecture

The following runtime replacements were removed:

- archive replacement of `operational_security.read_uploads`;
- archive replacement of `assessment_workflow.begin`, `complete`, and `export_payload`;
- catalog-on-archive replacement of `assessment_workflow.begin` and `complete`;
- archive replacement of canonical PDF and DOCX builders.

Sources already reach the canonical workflow directly, so a pending-upload `ContextVar` and
installer-order-dependent archive handoff are no longer necessary.

## Complete archive cycle

- A random case identifier is created after a valid workflow session begins.
- Original source files and intake metadata are encrypted and integrity protected.
- Each ready canonical snapshot receives a deterministic revision identifier.
- English and Turkish original PDF/DOCX artifacts are generated once and stored immutably.
- Patient name, patient ID, date, decision, reviewer, and creator attribution are stored only
  inside the encrypted catalog payload.
- The authenticated archive UI can search and reopen the saved canonical assessment.
- Original PDFs open inline from integrity-checked archived bytes.
- DOCX artifacts remain downloads.
- Regeneration reads the archived canonical snapshot and uses the current canonical report
  renderer without overwriting the original artifact.
- A changed ready assessment creates a distinct revision; an identical ready response remains
  idempotent.

## Identity and access

- With named-user access enabled, report reviewer/surgeon attribution is bound server-side to
  the authenticated identity; a browser-supplied reviewer name cannot replace it.
- The authenticated reviewer field is visible and read-only in the clinical UI.
- DOCTOR can search, reopen, download, and regenerate only cases attributed to that stable user
  id.
- OWNER can access all current and legacy/unassigned cases.
- Archive search, case open, report access, regeneration, and source access remain audited.
- Background analysis-job creation and polling are protected and bound to the doctor who
  created the job.

User-management and archive code do not alter clinical extraction, scoring, thresholds,
disposition, planning, or report calculations.

## Historical failure regression

The former state where a case was listed but its report could not be opened is covered by a
route-level cycle:

`search -> reopen case -> open exact original PDF -> regenerate from saved snapshot -> reopen unchanged original`

Missing or unauthorized artifacts return explicit HTTP errors; the browser no longer presents
PDF opening as a generic attachment-only action.

## Local evidence

- Focused archive, access, security, migration, and research set: `136 passed`.
- Complete application suite: `564 passed`.
- All `64` test files passed independently in fresh pytest processes.
- Critical Ruff checks, Python compilation, canonical startup invariants, and production
  dependency audit: passed.
- Wrapper-retirement, archive cycle, immutable original, regeneration, attribution, DOCTOR
  isolation, OWNER access, and background-job ownership regressions: passed.

No push, merge, deployment, or production action is authorized by this document.
