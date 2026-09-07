# CER-AI Step 1 — Test Retirement Record

This record implements Monday Master Order Step 60.

## Parallel `clean_engine` test suite

**Old rule / authority:** `clean_engine/*` was built as a separate replacement clinical engine and had its own policy, scoring, hard-stop, calculation, finalization, report-model, service, migration, and planning tests.

**New canonical rule / authority:** `clinical_core/*` + `canonical_input_adapter.py` + `canonical_runtime_service.py` + `assessment_workflow.py` are the sole surviving clinical path.

**Why the old tests are retired:** keeping tests that require `clean_engine` to exist would preserve a second clinical implementation and directly violate the governing rule: one source -> one normalized value -> one clinical rule -> one result -> one report representation. Equivalent accepted boundaries are protected by the canonical clinical-core, runtime, workflow, provenance, source-lock, planning-primitive, and report-payload tests.

The following `clean_engine`-specific test files are therefore retired rather than skipped:

- `test_clean_policy_equivalence.py`
- `test_clean_decision_surgery.py`
- `test_clean_reconciliation.py`
- `test_clean_engine_pipeline.py`
- `test_clean_status_equivalence.py`
- `test_clean_ablation_equivalence.py`
- `test_clean_prk_characterization.py`
- `test_clean_prk_equivalence.py`
- `test_clean_hard_stops.py`
- `test_clean_validation.py`
- `test_clean_scoring.py`
- `test_clean_calculation.py`
- `test_clean_finalization.py`
- `test_clean_architecture.py`
- `test_clean_public_api.py`
- `test_clean_end_to_end_equivalence.py`
- `test_clean_input_adapter.py`
- `test_clean_report_model.py`
- `test_clean_service.py`
- `test_clean_migration_seam.py`
- `test_clean_production_isolation.py`

## Legacy microkeratome runtime wrapper

**Old rule / authority:** `microkeratome_planning_policy.py` wrapped `core.hc_engine` after clinical assessment and `test_microkeratome_runtime_policy.py` required that wrapper to be installed.

**New canonical rule / authority:** clinical assessment never runs through an `hc_engine` wrapper. Pure microkeratome calculations remain in `planning/microkeratome.py`; canonical procedure-planning integration is deferred to the ordered Monday planning stage (Step 9).

**Why the old test is retired:** requiring the wrapper to be installed would recreate a second downstream clinical path and violate Step 1. The pure planning calculations are preserved for their later canonical integration.

## Legacy ERSS runtime-wrapper and visual-morphology tests

**Old rule / authority:** `erss_auto_read_policy.py`, `erss_topography_evidence_policy.py`, `erss_topography_guard.py`, and `erss_visual_morphology_policy.py` modified `core.hc_engine`, `core.assess_eye`, `core.scoring_morphology`, or readiness behavior and allowed a visual morphology pathway to participate in Randleman/ERSS classification.

**New canonical rule / authority:** `clinical_core.rules.erss_topography_category` and `clinical_core.erss` own the Randleman topography rule. Signed I-S is canonical numeric evidence; SRAX is used only from the approved front-map geometry/surgeon-confirmed source according to the Monday matrix. General visual morphology is not an automated Randleman scoring pathway.

**Why the old tests are retired:** tests that import or require those deleted wrappers would preserve the superseded runtime chain. Canonical I-S/SRAX boundaries, missing-data behavior, and non-additive topography scoring are now locked by the clinical-core and canonical-runtime test suites.

Retired files in this group:

- `test_erss_auto_read_policy.py`
- `test_erss_topography_evidence_policy.py`
- `test_morphology_retirement_lock.py`

## Legacy PS3 runtime wrapper

**Old rule / authority:** `ps3_runtime_policy.py` wrapped `core.hc_engine` to attach PS3 findings and escalate status after the legacy assessment.

**New canonical rule / authority:** `ps3_policy.py` is the pure PS3 evaluator and `clinical_core.ps3` exposes it to `canonical_runtime_service`; final disposition is owned by `clinical_core.disposition`.

**Why the old test is retired:** `test_ps3_runtime_policy.py` requires a deleted `hc_engine` wrapper and would preserve a second status-assignment path. PS3 thresholds, completeness, inter-eye logic, and procedure disposition remain covered by canonical PS3/core/runtime tests.

## Duplicate NICE runtime/scorer

**Old rule / authority:** `nice_scoring.py` duplicated NICE thresholds and `nice_policy.py` wrapped `core.hc_engine` to calculate NICE and mutate final status.

**New canonical rule / authority:** `clinical_core.nice.score_nice` is the sole four-input NICE scorer and `clinical_core.nice.nice_disposition` provides the NICE-specific finding consumed by the single canonical final disposition path.

**Why the old test is retired:** `test_nice_workflow.py` imports the duplicate scorer/wrapper and legacy HC-engine fixtures. Keeping that test would require retaining two NICE implementations and a second status mutation path. NICE boundary, incompleteness, disposition, pipeline, and report-payload behavior remain covered by canonical clinical-core/runtime tests.

## Monolithic legacy HC-engine regression suite

**Old rule / authority:** `tests/legacy_hc_engine_tests.py` and its collector `tests/test_hc_engine.py` execute `app.assess_eye` and `app.hc_engine`, including obsolete PRK-EWSS, tomography escalation, LASIK fallback, report-generation, and legacy readiness assumptions.

**New canonical rule / authority:** clinical assessment is executed only by `assessment_workflow -> canonical_runtime_service -> clinical_core`. Randleman/ERSS, NICE, BAD, PS3, tissue safety, final disposition, canonical input resolution, workflow readiness, and report-payload behavior each have dedicated canonical tests.

**Why the old tests are retired:** the remaining failures in this suite are not regressions in the canonical runtime; they assert behavior of the superseded engine itself (for example old LASIK planning-sequence fields and legacy readiness fixtures). Repairing those expectations would preserve `app.assess_eye/app.hc_engine` as a second clinical authority. The suite is therefore retired as a unit rather than patched piecemeal.

Retired files:

- `tests/test_hc_engine.py`
- `tests/legacy_hc_engine_tests.py`

No test is being retired because it is inconvenient. A test is retired only where its implementation has been explicitly superseded by the accepted canonical architecture.
