# CER-AI Monday Clean Architecture Audit

Status: **SUPERSEDED HISTORICAL BASELINE — branch `monday-clean-architecture`**

This document records the pre-refactor problem and deletion plan. It is not the current runtime
description. See `CERAI_MASTER_ORDER_66_ITEM_EVIDENCE_MATRIX.md` for the current 66-item audit.

## Governing rule

One source -> one normalized value -> one clinical rule -> one result -> one report representation.

If a rule is wrong, correct it at its canonical implementation and delete the superseded implementation. Do not add wrappers, monkey-patches, import-order overrides, report-side corrections, or a second scorer.

## Current production problem

Production currently starts through `canonical_engine.py`, which imports `runtime_composition.py`. `runtime_composition.py` installs many policy modules by mutating functions on the legacy `app.py` core. `canonical_engine.runtime_invariants()` then checks wrapper identity/order and `_installed` flags. This is exactly the architecture being retired.

## Existing candidate cores

### `clean_engine/`

- Pure/side-effect-free modules exist.
- However, the current API still uses a `morphology` category for Randleman topography and represents an earlier migration stage.
- It does not match the accepted Monday source/rule matrix as closely as `clinical_core/`.
- It must not become a second production clinical core.

### `clinical_core/`

- Side-effect-free pure clinical modules.
- Explicit I-S and SRAX inputs.
- Explicit NICE and PS3 modules.
- Explicit procedural safety and final disposition pipeline.
- Already has Phase 3 parity/cutover scaffolding.
- This is the preferred canonical clinical-core candidate, subject to Monday matrix corrections and regression validation.

## First confirmed rule correction

`clinical_core.rules.erss_topography_category()` previously treated SRAX `>=20.0` degrees as positive. Monday matrix requires:

- 19.9 = negative
- 20.0 = negative
- 20.1 = positive

The canonical candidate has been corrected directly to `>20.0` with a regression boundary test. No wrapper was added.

## Confirmed source conflict requiring deletion

The repository contains `rmin_front_source_policy.py`, while the accepted Monday matrix locks:

- Rmin -> Show 2 Exams -> Cornea Back
- posterior Km -> Show 2 Exams -> Cornea Back

The legacy Cornea Front Rmin path must therefore be removed during extraction cutover rather than overridden by another policy layer.

## Canonical target ownership

The final architecture should have these owners only:

1. **Pentacam source registry / extraction**
   - one registry of field -> screen -> panel/box -> unit/sign/provenance
   - no cross-screen fallback for locked fields
   - no reverse calculation for locked fields

2. **Normalization / reconciliation**
   - eye, exam date, provenance, surgeon-confirmed correction
   - no OD/OS cross-fill
   - no cross-date merge
   - same-eye/same-exam/same-source disagreement only -> CONFLICT

3. **`clinical_core`**
   - ERSS/Randleman
   - NICE
   - BAD final-D classification
   - PS3
   - hard stops / tissue safety
   - planning
   - one final disposition aggregator

4. **Workflow service**
   - dependency-aware missing-data prompts
   - one prompt per unresolved canonical field
   - no clinical scoring

5. **Report/archive**
   - render/store canonical assessment payload only
   - no clinical recalculation

## Deletion/cutover order

Do not mass-delete wrappers before their behavior has been moved into the canonical owner. Proceed in this order:

1. Freeze branch and map active production calls.
2. Correct and complete `clinical_core` against the Monday Acceptance Matrix.
3. Create one canonical Pentacam source registry and migrate extraction callers to it.
4. Move provenance/conflict/reconciliation into one normalized-input boundary.
5. Validate `clinical_core` against boundary and end-to-end regression cases.
6. Wire production assessment to the normalized input -> `clinical_core` path.
7. Make report generation consume the canonical result payload only.
8. Remove clinical wrapper installs from `runtime_composition.py`.
9. Remove wrapper-order and `_installed` clinical invariants from `canonical_engine.py`.
10. Delete superseded clinical policy wrapper files after confirming no callers remain.
11. Retire `clean_engine/` if all remaining functionality is represented in `clinical_core` or non-clinical owner modules.
12. Run full regression suite and production smoke test before merge/deploy.

## Wrapper families to retire after canonical migration

Clinical/extraction wrapper families currently visible include, among others:

- `hc_age_policy.py`
- `hc_bad_final_policy.py`
- `pachymetry_policy.py`
- `randleman_bad_independence.py`
- `hc_final_decision_policy.py`
- `erss_numeric_extraction_policy.py`
- `erss_topography_evidence_policy.py`
- `erss_auto_read_policy.py`
- `nice_policy.py`
- `ps3_runtime_policy.py`
- `ps3_extraction_policy.py`
- `mandatory_source_set_policy.py`
- `pentacam_canonical_source_enforcement.py`
- `pentacam_targeted_reread.py` where functionality duplicates the final canonical registry/reader
- `rmin_front_source_policy.py`
- `geometric_srax_policy.py` once SRAX geometry has a direct canonical extraction owner
- report policy wrappers that recalculate or alter clinical output

Deletion is conditional on caller migration and regression parity; none should remain as dormant alternate clinical truth.

## Immediate next stage

Audit and correct the canonical source registry, then complete ERSS/Randleman boundaries and SRAX dependency behavior in `clinical_core` before moving to NICE, BAD, PS3, hard stops, planning, disposition, reporting, and archive.
