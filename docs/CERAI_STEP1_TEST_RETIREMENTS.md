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

No test is being retired because it is inconvenient. It is retired because the entire implementation it tests is explicitly superseded and must be deleted to satisfy Step 1.
