# CER-AI Step 1 — Test Retirement Record

This record implements Monday Master Order Step 60.

## Shared LASIK/PRK PTA amendment (2026-09-08)

**Previous behavior:** LASIK alone used the canonical 40% gate; PRK did not expose PTA in the
canonical safety projection. Older documentation separately described a 35.28% review flag.

**Approved rule:** surgeon instruction “for prk,too, same pta rule as lasik shall apply.”
Both procedures use one `pta_percent` calculation and `pta_hard_stop` gate in
`clinical_core/safety.py`. PRK uses fixed 50 µm epithelium. Exact 40% and higher fail the plan
in direct PRK and automatic LASIK→PRK. No separate 35.28% operational flag remains.
LASIK-specific helper names were replaced directly, without compatibility wrappers; ML7 uses
the same canonical formula/gate. Existing LASIK planning expectations remain unchanged.
The Step 8 RST=310 fixture at CCT=545/ablation=185 previously expected overall PASS despite
PTA=43.12%. It now expects the independent PTA stop while retaining the allowed RST boundary.
A CCT=500/ablation=140 fixture verifies RST=310 with PTA=38% still passes.

**Evidence:** boundary tests cover 39.99/40/40.01, PRK between 35.28 and 40, retained original
plan during transition, report/runtime equality, independent RST failure and missing ablation.

## Stage 10 full-report completion clarification (2026-09-07)

**Old rule / test:** `test_irrevocable_stop_does_not_request_non_decision_critical_srax`
allowed a full report token when a definitive stop was already present even though PS3 still
required SRAX.

**New canonical rule:** a definitive hard stop may be displayed immediately, but a complete
CER-AI report still requires complete ERSS/Randleman, NICE, and PS3. Missing inputs are never
treated as zero or normal and no full report token is issued while one of those systems is
incomplete.

**Why the old expectation was retired:** the revised CER-AI Monday Master Order explicitly
superseded the earlier decision-critical-only exception. Immediate STOP-DEFER eligibility and
authorization to generate a complete report are now separate states.

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

## LASIK PTA 40% plan-failure clarification (2026-09-07)

**Old rule / tests:** the earlier canonical-core tests treated LASIK PTA as calculated
information that did not independently stop a plan. The runtime could therefore retain a
LASIK Plan A whose PTA was 40% or higher.

**New canonical rule:** PTA below 40.0% is permitted. PTA at exactly 40.0% or above fails the
evaluated LASIK candidate. Planning evaluates Plan A, then Plan B, then Plan C; the first plan
with PTA below 40.0% and all other safety requirements satisfied is selected. If all three
plans fail, the result is STOP-DEFER.

**Why the old expectations were retired:** the surgeon supplied this binding clarification on
2026-09-07, explicitly superseding the earlier informational-only behavior. Boundary and
runtime fallback coverage now lives in the canonical safety, pipeline, and planning tests.

## Legacy unread-region snapshot fallback (2026-09-07)

**Old rule / test:** `pentacam_source_regions.region_hints` could obtain an unread source box from
the obsolete `targeted_unreadable_regions` snapshot field when the canonical
`unreadable_source_regions` field was absent.

**New canonical rule:** unread-region lookup uses one field, `unreadable_source_regions`. An old
parallel snapshot must not silently populate the canonical path.

**Why the old expectation was retired:** the master order prohibits compatibility/fallback paths
that can provide a second representation of a canonical concept. The former preservation test now
locks rejection of that legacy side channel.

## PS3 activation and shared SRAX clarification (2026-09-08)

Old rule: any nonzero astigmatism activated the magnitude/axis discrepancy factor.
New accepted rule: activate only when either absolute manifest cylinder magnitude or
topographic astigmatism exceeds 3.00 D. Both values at or below 3.00 D contribute no
risk factor, regardless of axis or magnitude discrepancy; absent magnitudes remain
incomplete, never assumed low. Active comparisons retain the existing >1.00 D or
>10-degree discrepancy thresholds and zero-cylinder axis handling.

The surgeon explicitly accepted "either value" as the activation criterion. Old
low-cylinder Moderate expectations were superseded, while active-comparison tests
now use magnitudes above 3 D. New tests cover each side, equality, signed magnitudes,
missing inputs, and the OD 0.50/0.40 D example through runtime/report projection.

Old rule: one High or two Moderate findings caused SRAX to be skipped as NOT_REQUIRED.
New accepted rule: PS3 always consumes the shared source SRAX used by ERSS. Existing
High/Moderate findings can immediately defer a procedure but cannot mark missing
SRAX complete. The skip test was replaced with missing-SRAX completion and retention
of already-calculated SRAX tests. No second geometric calculation was introduced.


## 2026-09-08: Four-system final combination (surgeon confirmed)

Replaced the three-system aggregation directly in clinical_core.disposition.
ERSS, NICE, PS3 and Final BAD-D now contribute one result each: zero or one
CAUTION with the remaining systems PASS yields PASS; two yields PASS WITH CAUTION;
three or four yields CAUTION. STOP-DEFER and incompleteness take precedence.
Independent non-system caution gates and individual scoring results are retained.
The pipeline and shadow-equivalence tests expecting CAUTION from exactly two
scoring cautions now expect PASS WITH CAUTION. Component CAUTION assertions remain.
All 16 PASS/CAUTION combinations are covered, as are duplicate findings, bilateral
propagation, BAD-only caution, component informational flags and hard-stop precedence.

2026-09-08: PS3 axis input changed from the Cornea Front steep axis to the directly read BAD Axis (flat meridian) for this comparison only, by surgeon instruction. Direct PS3 synthetic fixtures now identify their axis as BAD flat axis; source and runtime tests preserve the independent steep-axis field and prohibit its use as a fallback. No score threshold changed.

2026-09-08: Failed LASIK now automatically evaluates PRK through the same canonical core. LASIK-only assertions inspect the preserved `lasik_assessment`; final eye assertions refer to the evaluated PRK result. The one-Moderate PS3 LASIK defer remains enforced, while its allowed PRK alternative may pass. No scoring or safety threshold was changed.
