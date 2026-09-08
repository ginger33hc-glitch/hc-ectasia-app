# CER-AI Stage 11 — Analyze and Completion Workflow Acceptance

Status: **IMPLEMENTED / LOCAL VALIDATION COMPLETE — 2026-09-07**

## Surviving workflow

`/analyze -> assessment_workflow.py -> canonical runtime -> structured missing-value requests -> /assessment/complete -> report token only when ready`

The browser presents workflow state and canonical report data. It does not score, apply
clinical thresholds, or reconstruct report results.

## Analyze and completion behavior

- Every non-ready state is visible, including contact-lens washout requirements.
- Analyze is re-enabled after each response, so an incomplete response cannot leave the
  action permanently disabled.
- Each readable completion request identifies eye, parameter, scoring system, canonical
  Pentacam screen, and source box where applicable.
- Requests shared by multiple systems are deduplicated and list every dependent scoring
  system.
- PS3 factor-level gaps are expanded into the exact missing canonical or surgeon-entered
  fields rather than requesting an opaque factor name.
- Surgeon-entered values continue through the single completion endpoint and retain
  surgeon-confirmed provenance.
- Prior LASIK, PRK, or SMILE selects the separate prior-surgery pathway and cannot receive
  a virgin-cornea report token.

## Readiness and hard stops

A complete report token is issued only when Randleman/ERSS, NICE, and PS3 are complete.
A definitive hard stop may be displayed immediately through the structured hard-stop
summary, but it does not substitute for completion when a full report is requested.

## Canonical browser result

The result view consumes `report_payload` from the canonical engine and presents:

- Randleman/ERSS;
- NICE;
- PS3 with exact elevated-risk findings;
- BAD-D and component values;
- procedural safety;
- canonical procedure planning and ML7 details;
- decision drivers;
- source-locked values and provenance;
- surgeon-completed values.

Legacy browser reads of parallel Randleman, morphology, elevation, planning, and raw
extraction fields were removed.

## Local evidence

- Focused Stage 11 and adjacent workflow tests: `32 passed`.
- Complete application suite: `557 passed`.
- All `63` test files passed independently in fresh pytest processes.
- Critical Ruff checks, full Python compilation, and canonical startup invariants: passed.
- Contact-lens, exact source prompt, PS3 dependency expansion, prior-surgery, immediate
  hard-stop, and Analyze-button regressions: passed.

No push, merge, deployment, or production action is authorized by this document.
