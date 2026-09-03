# CER-AI Phase 2 Boundary Contract

## Purpose

Phase 2 separates deterministic clinical decision logic from transport, extraction, workflow, presentation, and persistence concerns. This document freezes that boundary before Phase 3 runtime cutover.

The new `clinical_core` is allowed to receive already-normalized, source-validated clinical values and return deterministic clinical outputs. It must remain side-effect free.

## Explicit production order

1. Authentication / access control
2. Upload-count and mandatory source-set validation
3. Image extraction
4. Source provenance and reconciliation
5. Assessment readiness / contact-lens washout
6. Surgeon completion of unresolved required inputs
7. Clinical eligibility gate
8. Normalized per-eye clinical input
9. Pure clinical core
   - ERSS
   - Final BAD-D
   - NICE
   - PS3
   - procedural tissue / refractive safety
   - final disposition aggregation
10. LASIK / procedure planning
11. Report generation
12. Archive / audit / research persistence

## Responsibilities that MUST remain outside `clinical_core`

### Mandatory source-set validation

The clinical core must never decide whether the five mandatory Pentacam source images were uploaded. The production source gate remains responsible for:

- OD Four Maps Refractive
- OS Four Maps Refractive
- OD Belin/Ambrosio Display
- OS Belin/Ambrosio Display
- one Show 2 Exams Topometric page
- one optional excimer treatment card as the sixth image only

Missing or unidentifiable mandatory source images block assessment before clinical scoring.

### Extraction and provenance

OCR/vision extraction, field-source restrictions, provenance, conflict detection, surgeon-confirmed corrections, and source reconciliation remain outside the clinical core. The core consumes normalized values only.

### Readiness and contact-lens washout

Readiness is a workflow gate, not a risk score. The frozen launch policy is:

- no contact lenses: no washout block
- soft lenses: at least 10 full days
- rigid/RGP lenses: at least 21 full days

Insufficient washout blocks assessment before any clinical score is computed.

### Clinical eligibility

General clinical eligibility, stability, pregnancy/nursing, systemic/ocular contraindications, prior corneal refractive surgery routing, and surgeon-entered procedural prerequisites remain outside the numeric ectasia-risk core. They may restrict or block the final workflow but must not be converted into ERSS, BAD-D, NICE, or PS3 points.

### Planning

The clinical core may expose pure planning primitives, but the production planning workflow remains downstream of the final clinical disposition. A favorable fallback plan must never erase an upstream hard stop or an earlier failed plan.

### Reporting and archive

The clinical core must not generate PDFs/DOCX, mutate report templates, create archive records, write audit logs, or persist Pentacam images. Report and archive layers consume finalized clinical outputs downstream.

## Phase 3 cutover rule

Phase 3 may replace wrapper-on-wrapper clinical composition with the explicit linear orchestrator only when:

1. Phase 1 launch-contract tests remain green.
2. Phase 2 pure-core equivalence tests remain green.
3. Shadow parity remains green.
4. External-boundary tests remain green.
5. Full application regression and import-order independence remain green.

No clinical threshold may be changed as part of the Phase 3 cutover. Any threshold change must be a separate, explicitly reviewed clinical-policy change.
