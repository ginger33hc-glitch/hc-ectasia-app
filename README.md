# CER-AI

FastAPI application for source-restricted preoperative ectasia risk assessment using the **CER-AI Preoperative Ectasia Risk Assessment for Corneal Refractive Surgery**.

## What v0.7.52 implements

- Randleman topography is read only from a qualifying anterior curvature map. A dedicated
  `HIGH`-confidence complete-map classification may supply the mutually exclusive morphology
  category without requiring an I-S value. `MODERATE`, `LOW`, or unreadable classifications
  remain unscorable until surgeon confirmation.
- Labeled/confirmed I-S remains a separate numeric threshold input and a NICE component; it is
  not a universal prerequisite for a clearly classifiable Randleman anterior pattern.
- Topography categories remain mutually exclusive and use the existing single point mapper: abnormal
  +4, inferior steepening/SRA +3, asymmetric bow-tie +1, and normal/symmetric +0.

- Mobile-safe signed refraction parsing now recognizes common Unicode plus/minus characters.
- Invalid or partial manifest/intended manual entries block analysis with a field-specific warning instead of silently becoming missing data.

- Sequential original-detail extraction of each uploaded Pentacam/topography or treatment-card image.
- Pentacam numeric-source priority: explicitly labeled side/summary-table fields are used first.
  When that field is unreadable, a directly corresponding marked local-map value may be used only
  for thinnest pachymetry or anterior/posterior elevation at the marked thinnest point. Local spots
  cannot substitute for K, BAD, progression, ARTmax, topometric, volume, or HOA/coma summary values;
  categorical visual inference is reserved for morphology, bow-tie/SRAX, and map patterns.
- Installable Android PWA with a Web Share Target: one or multiple images shared from Samsung Gallery can open CER-AI and populate its image intake.
- Excimer Laser Takip Kartı reading limited to the eye-specific `Düzeltme Miktarı` row; confident minus-cylinder values can fill otherwise empty sphere/cylinder/axis fields, while manual input wins and uncertain/conflicting readings remain warnings.
- Independent OD and OS assessment; eye values are never averaged, and a missing fellow-eye assessment prohibits overall PASS.
- Source identity review reads Pentacam patient names only from the labeled `First Name` and `Last Name` demographics fields and records the source filename. An unreadable or unverified name produces a prominent surgeon-confirmation warning without suppressing the eye analyses; acquisition-date conflicts and unclassified/unusable uploads remain clinical/source blockers.
- Pentacam clearance requires a same-exam explicit `QS: OK`; a visible non-OK QS cannot be masked by another page.
- Age is read from the explicitly printed Pentacam age; a conflicting manually entered age remains a blocker. Date of birth is not collected.
- Preoperative manifest refraction is separated from intended treatment correction. LASIK ERSS MRSE uses only the former; ablation and CER-AI treatment-range gates use only the latter.
- Prior PRK/LASIK/SMILE short-circuits virgin-cornea scoring and routes to `POST-REFRACTIVE PATHWAY REQUIRED`.
- Published five-component LASIK ERSS scoring and categories.
- PRK-EWSS v1.0 provisional morphology/pachymetry/age triage score, explicitly labeled as unvalidated.
- Morphology-first override gate for definite KC/FFKC/PMD or unequivocal ectatic morphology.
- Published ERSS Placido thresholds are enforced when numeric evidence is available: SRAX `≥20°`; the alternative category requires `≥1.0 D` inferior-versus-opposite steepening with `I-S <1.4 D`. A clearly visible `HIGH`-confidence SRA/inferior-steepening map pattern may also supply the category without inventing an angle; lower-confidence visual labels remain unscorable.
- CER-AI operational hard stops: preoperative thinnest pachymetry `<480 µm`, LASIK RSB `<300 µm`, PRK RST `<310 µm`, intended sphere `<−10.00 D`, and intended sphere `>+6.00 D`. Exact boundaries do not trigger those rules.
- CER-AI-modified LASIK pachymetry scoring: `480–499 µm` = +2, `500–509 µm` = +1, and `>=510 µm` = +0.
- Standard CER-AI PRK calculation: `RST = pachymetry - 50 µm epithelium - maximum stromal ablation`.
- Zone-specific CER-AI ablation estimates for explicitly documented Alcon EX500 plans: `12 µm/D` at 6.0 mm, `15 µm/D` at 6.5 mm, and `16.33 µm/D` at 7.0 mm; the actual treatment-plan maximum remains preferred.
- Optical-zone selection is limited to `6.0`, `6.5`, or `7.0 mm`; transition-zone selection is limited to `8.0`, `8.5`, or `9.0 mm`.
- The visible laser-platform field is fixed and read-only as `Alcon EX500` for both eyes; the optical zone remains an explicit eye-specific input.
- Planned LASIK flap thickness is selected per eye from `90`, `100`, `110`, or `120 µm`; PRK plans leave the flap selection blank.
- Refraction stability, documented progression, unexplained CDVA loss, and anticipated enhancement remain separate eye-specific values inside one compact clinical-eligibility dropdown box.
- PRK epithelial thickness is shown per eye as a fixed, read-only `50 µm` CER-AI value and is used in the PRK RST/PTA calculations.
- Procedure-correct PTA formulas for LASIK and PRK.
- BAD-D/component display interpretation plus adjunctive ARTmax/TP/Dt/Da evidence flags.
- Positive tomography concern flags require review and cannot receive automatic PASS.
- Limited/inadequate decision-source image quality, implausible numeric values, failed PPI/ARTmax consistency checks, and unresolved cross-image value conflicts prohibit PASS. Same-provenance numeric differences `<=1%` retain the parameter-specific safety-limiting value: lower for pachymetry, ARTmax, and Rmin; higher for the remaining supported numeric fields.
- PRK PTA above the supplied 35.28% direct-cohort envelope requires review and cannot receive automatic PASS.
- Expanded extraction/reporting of anterior and posterior elevation, pachymetric progression,
  topometric, thinnest-point location, corneal-volume, and HOA/coma fields when visibly available.
- Required clinical modifiers and treatment-plan inputs; missing/unreadable critical data prohibit PASS.
- One multi-select clinical-eligibility control records eye rubbing/ocular trauma, family history, inter-eye asymmetry, pregnancy/nursing, collagen/connective-tissue disease, medication, dry eye, and systemic disease. These create separate defer/review dispositions without invented ectasia-score points.
- Contact-lens type and washout are documented. The supplied source-study acquisition criterion (soft ≥14 days; rigid ≥21 days) is an imaging-data gate, not an ectasia score or universal safety cutoff.
- Binding CAUTION action: STOP/DEFER, repeat relevant screening, and reassess after at least 6 months.
- Formal clinical report with patient/reviewer metadata, restrained decision colors (PASS green,
  CAUTION amber, FAIL red, NOT ASSESSED gray), print layout, and validated PDF and DOCX exports.
- The patient name is repeated in large bold uppercase immediately above the overall disposition
  box in the browser, print, PDF, and DOCX reports.
- Complete machine-readable extraction and decision records remain available for audit.
- A status-independent post-assessment ML7 planning module runs only after favorable LASIK results
  (`PASS` or `PASS WITH CAUTION`). It extracts labeled K1/K2 axes and corneal diameter/W2W when
  available, applies the active Turkish ML7 vacuum-ring/blade reference, and applies the CER-AI
  `steep K − flat K >4.00 D` hinge rule. The perpendicular-to-steep-axis hinge is primary; a
  `+10` temporal/nasal alternative is shown only as an anatomy-dependent contingency when projected
  RSB remains `>=300 µm` and projected PTA remains `<40%`. The module cannot change the ectasia status.

See [CER-AI_PROTOCOL_v0.7.md](CER-AI_PROTOCOL_v0.7.md) for the locked operational rules and
[PROTOCOL_COMPLIANCE.md](PROTOCOL_COMPLIANCE.md) for the source-to-code audit and evidence limitations.

## Run

```bash
pip install -r requirements.txt
python start.py
```

Railway start command: `python start.py`.

## Test

```bash
python -m pytest -q
```

The test suite covers exact structural and treatment-range boundaries, signed manifest/intended input and axis requirements, phone-safe sign-only entry, fixed OD-before-OS reporting, prior-surgery routing, identity warnings, date/QS gates, invalid numeric inputs, fellow-eye completeness, ERSS/PRK-EWSS categories, extraction merging, runtime isolation, and valid PDF/DOCX generation.

Dependencies are exact-version pinned. The extraction model is restricted to the reviewed configuration; changing it requires explicit non-clinical override and revalidation.


## Authorized update and deployment workflow

For this project, do not use the cloud-browser GitHub username/password form and do not rely on a
local HTTPS `git push` credential. Use the connected GitHub application:

1. Read the current target file from `ginger33hc-glitch/hc-ectasia-app` on `main` and retain its
   current blob SHA.
2. Make and validate the change in the local project copy.
3. Replace the target file on `main` through the connected GitHub application's file-update
   capability, supplying the retained SHA and a descriptive commit message.
4. Verify the returned commit SHA, then allow the linked Railway service to deploy automatically.
5. Reload `https://hc-ectasia-app-production.up.railway.app/` and verify the live application.

Never place GitHub passwords, tokens, API keys, or other credentials in this repository.

## v0.7.51 — CER-AI-adapted NICE and report readiness

Final BAD-D policy is now boundary-locked to the Pentacam abnormal display threshold:
`<=1.60` normal, `>1.60 to <2.60` suspicious, and `>=2.60` abnormal. Final
BAD-D `>=2.60` is an inclusive CER-AI operational hard stop and produces
`DO NOT PROCEED`. Individual Df/Db/Dp/Dt/Da components remain contextual and
do not independently determine clearance.

`canonical_engine.py` remains the single production composition root. Independent
`nice_scoring.py` and `nice_policy.py` add a restrictive-only final NICE disposition;
ERSS/BAD calculations and the isolated `clean_engine` are unchanged. NICE points are
never added to ERSS. LASIK and PRK use total 4: no NICE escalation, 5–8: CAUTION /
STOP-DEFER, >=9: HARD STOP. A stronger existing stop always wins.

The report labels this as **CER-AI-adapted NICE**, documents all four components and
provenance, and cites DOI 10.2147/OPTH.S464217. The approved posterior bands are
<=15.5 / >15.5 and <18 / >=18 µm, scoring 1/2/3 points (not zero). The automatic
reader uses the highest printed positive value inside the visible dashed pupil
on a standard 8-mm BFS Float posterior elevation map. It never substitutes a
colour estimate, a whole-map maximum, BFTE, BAD difference or thinnest-point
elevation. Central pachymetry is the labeled Pachy Vertex N. reading, not thinnest.
The pupil-maximum method and 15.5 boundary are disclosed CER-AI adaptations, not a
claim that the original study independently validated this implementation.

`assessment_workflow.py` gates reports using all canonical decision-critical missing
inputs plus missing NICE components. `/analyze` returns NEEDS_INPUT (without a
clinical decision) and eye-specific completion requests until ready. The browser
retains manual entries; `/assessment/complete` resumes without another model call.
Explicit surgeon corrections retain an audit trail and rerun input validation.
Unreadable source identity/quality may require a clearer source, not a guessed value.

PDF/Word exports require server-issued assessment and current ready-report tokens;
client-supplied clinical decisions cannot bypass completeness. Tokens reference
bounded in-memory sessions (64; one-hour idle expiry); server restart or eviction
requires a new upload. Do not increase worker count without shared session storage.
Form edits hide the previous report. No clinical model accuracy claim is inferred
from unit tests; unreadable image values require surgeon confirmation.

Deployment: publish all changed files in one GitHub tree/commit before moving main,
so a partial multi-file update cannot deploy. Pre-release rollback base:
`f9f45b8` (restore through a reviewed revert commit, never force-reset main).
