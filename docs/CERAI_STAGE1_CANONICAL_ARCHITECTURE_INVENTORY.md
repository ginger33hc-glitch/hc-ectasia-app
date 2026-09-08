# CER-AI Stage 1 — Canonical Architecture Inventory

Status: **CLOSED / ACCEPTED — 2026-09-07**

Governing rule: one source -> one normalized value -> one clinical rule -> one result -> one report representation.

Stage 1 is complete. Production clinical assessment no longer uses the legacy `app.py` clinical engine or runtime clinical wrappers. The accepted production path is direct and canonical:

`assessment_workflow.py -> canonical_runtime_service.py -> clinical_core/*`

## Canonical clinical path

1. `assessment_workflow.py` — transport/session/readiness/surgeon-completion workflow only; calls the canonical runtime directly.
2. `canonical_readiness.py` + `clinical_core/readiness.py` — pre-core readiness only.
3. `canonical_input_adapter.py` — one treatment/refraction normalization boundary.
4. `canonical_runtime_service.py` — one case-level clinical runtime boundary.
5. `clinical_core/erss.py` — sole ERSS/Randleman scorer.
6. `clinical_core/nice.py` — sole NICE scorer.
7. `ps3_policy.py` through `clinical_core/ps3.py` — sole PS3 evaluator.
8. `clinical_core/bad.py` — sole BAD-D classifier.
9. `clinical_core/safety.py` — sole hard-stop/tissue-safety owner.
10. `clinical_core/disposition.py` — sole final disposition owner.
11. `clinical_core/planning.py` — canonical planning primitives; direct runtime integration was completed in Stage 9.
12. `clinical_core/report_payload.py` — canonical renderer-neutral payload consumed directly by the Stage 10 PDF/DOCX renderers.
13. `pentacam_canonical_source_lock.py` — sole canonical Pentacam source specification; Stage 2-3 extraction flattening is complete.
14. `pentacam_provenance.py` — canonical provenance/conflict semantics.

## Physically retired clinical architecture

The following parallel clinical paths were deleted rather than bypassed:

- `clean_engine/*`
- `hc_age_policy.py`
- `hc_bad_final_policy.py`
- `pachymetry_policy.py`
- `randleman_bad_independence.py`
- `hc_final_decision_policy.py`
- `inter_eye_tomography_policy.py`
- `nice_policy.py`
- `nice_scoring.py`
- `ps3_runtime_policy.py`
- `erss_auto_read_policy.py`
- `erss_topography_evidence_policy.py`
- `erss_topography_guard.py`
- `erss_visual_morphology_policy.py`
- `microkeratome_planning_policy.py`
- `lasik_planning.py`
- the monolithic legacy HC-engine test suite
- Phase-3 shadow/cutover/parity wrappers
- workflow monkey-patches including `srax_completion_policy.py` and `randleman_report_readiness_policy.py`

## Legacy clinical engine removed from `app.py`

The following dormant second-engine functions were physically deleted from `app.py`:

- `assess_eye`
- `hc_engine`
- `apply_extracted_corrections`

The obsolete `nice_policy.attach_readings` pass was also removed. `/analyze` now merges extraction output and passes it directly into `assessment_workflow.begin`, which calls `canonical_runtime_service.evaluate_case`.

A permanent regression lock in `tests/test_phase4_cleanup_contract.py` fails if these legacy functions or the NICE attach-readings path reappear.

## Extraction/source migration outcome

The following list is the original Stage-1 inventory. Stage 2 subsequently moved the accepted
behavior into direct extraction/merge ownership and physically deleted the superseded wrappers.
The current acceptance state is recorded in `CERAI_MASTER_ORDER_66_ITEM_EVIDENCE_MATRIX.md`.

## Extraction/source modules originally retained for Stage 2-3 migration

These modules remain temporarily because they currently own extraction/source behavior. They are **not accepted as final architecture** and must be flattened into one direct canonical extraction path before Stage 2-3 close:

- `merge_policy_base.py`
- `extraction_guard.py`
- `erss_numeric_extraction_policy.py`
- `pentacam_canonical_source_enforcement.py`
- `ps3_extraction_policy.py`
- `mandatory_source_set_policy.py`
- `pentacam_targeted_reread.py`
- `rmin_front_source_policy.py`
- `geometric_srax_policy.py`
- `bad_display_source_policy.py`

Stage 2-3 rule: migrate accepted behavior into the canonical extraction/merge/source registry, update callers, then delete the superseded wrapper. Do not add another wrapper.

## Reporting/planning Stage 10 update

Stage 10 has now retired the temporary report modifiers listed below. They are
kept here only as an architecture-history record:

- `ps3_report_policy.py`
- `microkeratome_report_policy.py`
- `critical_score_highlight.py`
- `report_export_guard.py`

The surviving modules are:

- `reports.py` — the sole presentation renderer; consumes only the canonical report payload.
- `planning/microkeratome.py` — the canonical ML7 planning implementation completed in Stage 9.

## Operational modules retained

These are non-clinical or persistence/access concerns and may remain installed:

- `user_access.py`
- `operational_security.py`
- `public_site.py`
- `analysis_job_service.py`
- `case_archive.py`
- `audit_log.py`
- `case_catalog.py`
- `historical_report.py`
- `research_export.py`
- `named_user_ui.py`

Stage 13 retired `mobile_install_section.py`. Its presentation-only behavior now belongs
directly to the authoritative public renderer in `public_site.py`; the former module replaced
that renderer at import-composition time and was therefore an unnecessary wrapper.

## Stage 1 validation record

Accepted branch head: `fa83208cb5a53fcda460513c8345f9aefa8b14bc`

Canonical Runtime Safety run `34138765265` completed successfully. All gates passed:

- dependency audit
- critical static checks
- decision-critical module compilation
- canonical startup invariants
- Phase 1 launch behavior contract
- Phase 2 canonical clinical core/readiness/source/provenance contract
- Phase 3 direct canonical input/runtime/workflow boundary
- Phase 4 cleanup contract
- archive/Railway/security/public-site regression group
- behavior/equivalence/clinical regression group
- complete application pytest suite
- every test file independently, proving no test/import-order dependency

Therefore Stage 1 is closed. PR #75 remains draft and unmerged. No deployment is authorized by Stage 1 closure.

## Next ordered stage

Proceed to **Stage 2 — canonical Pentacam source/extraction audit and flattening**.

Stage 2 objective:

`SOURCE IMAGE -> ONE CANONICAL EXTRACTION -> ONE CANONICAL VALUE + PROVENANCE`

The first Stage-2 action is an inventory of the remaining extraction wrappers, their mutations of `SCHEMA`, `PROMPT`, `extract_one_image`, `merge_extractions`, or field provenance, and the exact canonical destination for each accepted behavior.
