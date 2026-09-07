# CER-AI Stage 1 — Canonical Architecture Inventory

Status: ACTIVE CONTROL DOCUMENT

Governing rule: one source -> one normalized value -> one clinical rule -> one result -> one report representation.

This inventory is the Stage 1 map required by the Monday Master Order. A module marked DELETE NOW is already superseded by the direct canonical workflow/runtime and must not survive as a parallel clinical authority. A module marked RETAIN FOR LATER STAGE is not accepted as permanent architecture; it is kept only because its topic belongs to a later ordered stage and its replacement has not yet completed validation. Operational modules do not own clinical scoring.

## Canonical clinical path that survives

1. `assessment_workflow.py` — transport/session/surgeon-completion workflow; calls canonical runtime directly.
2. `canonical_readiness.py` + `clinical_core/readiness.py` — pre-core age/contact-lens/procedure/prior-surgery readiness only.
3. `canonical_input_adapter.py` — one treatment-role normalization/plan-resolution boundary.
4. `canonical_runtime_service.py` — one case-level clinical runtime boundary.
5. `clinical_core/erss.py` — sole ERSS/Randleman scorer.
6. `clinical_core/nice.py` — sole NICE scorer.
7. `ps3_policy.py` through `clinical_core/ps3.py` — sole PS3 policy/evaluator.
8. `clinical_core/bad.py` — sole BAD-D classification.
9. `clinical_core/safety.py` — sole canonical hard-stop/tissue-safety thresholds.
10. `clinical_core/disposition.py` — sole final PASS/CAUTION/STOP-DEFER/ASSESSMENT INCOMPLETE finalizer.
11. `clinical_core/planning.py` — canonical planning primitives; full runtime integration belongs to Stage 9.
12. `clinical_core/report_payload.py` — canonical renderer-neutral report payload; renderer cutover belongs to Stage 10.
13. `pentacam_canonical_source_lock.py` — current single source registry specification; direct extraction migration belongs to Stages 2-3.
14. `pentacam_provenance.py` — canonical provenance/conflict semantics.

## Legacy clinical implementations — DELETE NOW from production composition

These are already superseded by the canonical runtime and must not be imported/installed as parallel clinical scorers:

- `hc_age_policy.py` — duplicate age scoring/legacy runtime mutation.
- `hc_bad_final_policy.py` — import-time mutation of `core.assess_eye`; duplicate BAD/tomography decision path.
- `pachymetry_policy.py` — duplicate legacy pachymetry scoring path.
- `randleman_bad_independence.py` — legacy Randleman runtime path superseded by `clinical_core/erss.py`.
- `hc_final_decision_policy.py` — duplicate final-decision hierarchy superseded by `clinical_core/disposition.py`.
- `inter_eye_tomography_policy.py` — parallel clinical escalation layer; accepted inter-eye PS3 logic is in canonical PS3.
- `nice_policy.py` — parallel NICE runtime scorer superseded by `clinical_core/nice.py`.
- `ps3_runtime_policy.py` — parallel PS3 runtime wrapper superseded by canonical PS3/case runtime.

Their tests may remain temporarily only where they verify accepted clinical boundaries independently; tests that require installer identity/wrapper order must be retired with documented old-rule -> new-rule rationale.

## Legacy planning/report modules — RETAIN FOR LATER ORDERED STAGES, not permanent architecture

Do not modify their clinical behavior during Stage 1 except to prevent them becoming a second final clinical authority.

- `microkeratome_planning_policy.py` — Stage 9 migration target.
- `lasik_planning.py` — legacy Plan A/B/C wrapper; contains retired PTA >=40 STOP behavior and must NOT be copied. Stage 9 replacement uses `clinical_core/planning.py` plus the same canonical safety engine.
- `ps3_report_policy.py` — Stage 10 report migration target.
- `microkeratome_report_policy.py` — Stage 10 report migration target.
- `critical_score_highlight.py` — Stage 10 presentation migration target; must not score.
- `report_export_guard.py` — Stage 10/11 gate migration target; may gate export but may not calculate scores.
- `reports.py` — Stage 10 renderer migration target; final renderer must consume canonical report payload only.

## Extraction/source modules — RETAIN FOR STAGES 2-3, not accepted as final architecture

These currently preserve required source behavior but include wrapper/on-wrapper structure that must be flattened into direct extraction in the next ordered stages:

- `merge_policy_base.py`
- `extraction_guard.py`
- `erss_numeric_extraction_policy.py`
- `erss_topography_evidence_policy.py`
- `pentacam_canonical_source_enforcement.py`
- `ps3_extraction_policy.py`
- `mandatory_source_set_policy.py`
- `pentacam_targeted_reread.py`
- `rmin_front_source_policy.py` — misleading legacy name; current behavior may be corrected but module must be deleted after direct Cornea Back extraction migration.
- `geometric_srax_policy.py`
- `erss_auto_read_policy.py`
- `bad_display_source_policy.py`

Stage 2-3 rule: move accepted source behavior into direct canonical extraction, then delete wrappers rather than stacking new ones.

## Base legacy engine in `app.py` / `bootstrap.py`

`app.py` still contains legacy `assess_eye`, `hc_engine`, score combination, plan correction and other clinical code. `bootstrap.py` also installs/overwrites legacy functions. These are NOT canonical clinical authority after workflow cutover.

Stage 1 cleanup requirement:
- prove production `/analyze` reaches `assessment_workflow` -> `canonical_runtime_service`;
- remove production composition dependencies on legacy clinical scorers;
- identify any non-workflow caller of `core.assess_eye` / `core.hc_engine`;
- after callers are migrated or shown obsolete, delete the legacy clinical functions rather than leaving a dormant second engine.

The EX500 displayed-Maximal-Ablation precedence currently trapped in legacy plan correction is a valid input-resolution behavior and must be migrated to `canonical_input_adapter.py` before deleting the legacy correction function. This is plan-input normalization, not a second clinical scorer.

## Operational/non-clinical modules — KEEP

These do not own clinical scoring and may remain installed:

- `assessment_workflow.py`
- `user_access.py`
- `operational_security.py`
- `public_site.py`
- `analysis_job_service.py`
- `mobile_install_section.py`
- `case_archive.py`
- `audit_log.py`
- `case_catalog.py`
- `historical_report.py` (must consume canonical report artifacts; no rescoring)
- `research_export.py`
- `named_user_ui.py`

## Already deleted as obsolete architecture

- Phase 3 runtime seam/parity/shadow/cutover modules.
- `srax_completion_policy.py` monkey-patch.
- `randleman_report_readiness_policy.py` monkey-patch.
- superseded Phase 3 migration tests that required legacy-vs-canonical coexistence.

## Stage 1 closure criteria

Stage 1 is accepted only when:

- production composition no longer imports/installs duplicate clinical scorers;
- `assessment_workflow` directly calls `canonical_runtime_service.evaluate_case`;
- no workflow monkey-patch remains;
- no active production caller uses legacy `core.hc_engine` for clinical assessment;
- import order cannot change clinical behavior;
- the architecture inventory matches actual code;
- startup invariants, dedicated canonical runtime tests, full pytest, and independent test-file/import-order checks pass.

Only after Stage 1 is accepted do we proceed to Stage 2 canonical Pentacam extraction sources.
