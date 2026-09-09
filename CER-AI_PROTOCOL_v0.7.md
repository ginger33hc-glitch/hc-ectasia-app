# CER-AI Preoperative Ectasia Risk Assessment — Software Rule Specification v0.7

Original effective date: 26 August 2026. Reconciled with approved staging amendments: 8 September 2026.

This file is the code-aligned operational rule specification. Published evidence, provisional
triage, CER-AI operational policy, imaging-quality criteria, and general clinical eligibility are kept
as separate layers. No rule in one layer is silently presented as a validated rule from another.

## Case and source integrity gate

- Require OD and OS Four Maps Refractive, OD and OS Belin/Ambrosio Display, and one bilateral Show 2 Exams Topometric page. Primary page identification confirms this five-page set before targeted rereading, geometric SRAX, merge, clinical scoring, or reporting. One excimer treatment card is optional as the sixth image. If it is absent, complete surgeon-entered manifest and intended refraction for both eyes is required before assessment continues.
- Age is calculated in `patient_age_policy.py` as completed years at the Four Maps Refractive examination date from its labeled Date of Birth. Raw dates and calculation provenance are retained. Surgeon-entered age takes precedence; conflicting or age-ambiguous dates require confirmation. The image model transcribes dates without performing arithmetic.
- Report patient name uses one block: First Name / Last Name in the upper-left OD 4 Maps Refractive header (first supplied OD page). Use OS only when OD Four Maps is absent. An unreadable selected header requests surgeon entry; other-page name readings do not select or veto the report name. Patient-ID safety checks remain separate.
- Extract and compare patient ID/name, printed age, date of birth, examination date/time, laterality, filename, and
  literal Pentacam QS.
- Unresolved patient age or a conflicting Pentacam examination date prohibits PASS; identity uncertainty remains
  a visible surgeon-confirmation warning without suppressing the eye assessments.
- Surgeon-entered age is authoritative and does not conflict with printed or date-derived age. Source age evidence remains in the audit record.
- Every surgeon-entered or surgeon-confirmed field is authoritative. Image-derived and calculated values may fill blank fields only; they do not overwrite or create a conflict against a surgeon value.
- Both OD and OS are required for overall PASS; eyes remain separately assessed and are not averaged.
- An unclassified upload, an upload yielding no usable eye/treatment data, or an unresolved
  decision-critical field conflict prohibits PASS.
- Literal Pentacam QS and generic source-image quality are retained as acquisition audit data.
  Non-OK/unconfirmed QS and limited/inadequate quality do not alone suppress a report when required
  clinical measurements are readable; they generate a prominent surgeon-attention warning at the
  bottom of the browser, PDF, and Word reports. They are never silently changed to `OK`.
- Record field-level canonical source and surgeon-confirmation provenance. Locked fields have
  no alternative-source fallback. Same-source disagreement clears the field and requests
  resolution; no tolerance, first/minimum/maximum, or most-concerning selection is permitted.

## Clinical disposition contract

- Completed assessments use four clinical results: `PASS`, `PASS WITH CAUTION`, `CAUTION`, and `STOP-DEFER`.
- `CAUTION` requires explicit surgeon review but does not automatically defer surgery. NICE 5–8
  uses this category.
- `STOP-DEFER` means surgery must not proceed unless the stated stop/defer condition is resolved.
  NICE ≥9, independent hard stops, and explicit defer rules use this category.
- `ASSESSMENT INCOMPLETE` and `POST-REFRACTIVE PATHWAY REQUIRED` remain workflow states, not additional
  clinical result categories.

## Pathway gate

- `prior PRK/LASIK/SMILE = yes` exits the virgin-cornea engine immediately and returns
  `POST-REFRACTIVE PATHWAY REQUIRED`.
- Unknown prior-surgery status prohibits PASS.

## Refraction and plan separation

- LASIK ERSS MRSE uses preoperative manifest sphere and minus-cylinder magnitude:
  `MRSE = manifest sphere − manifest cylinder magnitude / 2`.
- Ablation and CER-AI treatment-range gates use intended treatment sphere/cylinder only.
- PRK Mitomycin-C guidance uses intended treatment MRSE magnitude and does not change the ectasia
  score or disposition. Use is required for all hyperopic PRK and for myopic PRK at 4.00 D or
  greater magnitude (for example, -4.00 D and -5.00 D); use is recommended below 4.00 D myopic
  magnitude (for example, -3.99 D). Mixed astigmatism requires separate surgeon review.
- Treatment-card extraction may auto-fill intended correction only from `Düzeltme Miktarı`.
- Invalid numeric ranges are not used in any formula.
- Manifest and intended corrections are normalized to minus-cylinder notation, then classified
  from their two principal meridians as myopic, hyperopic, simple astigmatism, or mixed
  astigmatism. Entering an equivalent plus-cylinder notation must not change the classification.
- A valid surgeon-entered axis is required for a complete manifest or intended refraction,
  including an explicitly entered zero cylinder. Missing values remain missing and are never
  converted to zero; plus-cylinder transposition without an axis is never cleared.

## Hyperopic and mixed-astigmatism pathway

- The report is generated even when this pathway cannot receive PASS; available tomography,
  structural calculations, missing plan data, and known hard stops remain visible.
- Actual laser-plan maximum stromal ablation is mandatory. The CER-AI linear myopic EX500 µm/D
  convention is not applied to hyperopic annular or mixed bitoric profiles.
- Hyperopic/mixed cases receive `CAUTION` because the supplied procedure-specific
  ectasia scoring evidence is predominantly myopic. No new weighted ectasia score is invented.
- Mixed astigmatism is present when the two intended principal meridians have opposite signs.
  Near-zero MRSE is not treated as low surgical load.
- The CER-AI Kmean estimate is not applied to mixed astigmatism. The report instructs the surgeon to
  review planned postoperative meridional K values/K1-K2 and the expected steepest and flattest
  corneal powers.
- The report instructs the surgeon to confirm manifest-versus-cycloplegic refraction, latent
  hyperopia, at least one year of refractive stability, actual ablation profile, optical/transition
  zones and centration, full-diameter anterior/posterior tomography, inferior peripheral
  pachymetry, and PMD/inferior-steepening morphology.
- Applicable Alcon WaveLight LASIK labeling is displayed as a surgeon-verification item, not as an
  ectasia-safety guarantee: hyperopia up to +6.00 D sphere, 5.00 D cylinder and +6.00 D MRSE;
  mixed astigmatism up to 6.00 D cylinder and age at least 21 years.
- Hyperopic/mixed PRK is explicitly identified as lacking a validated procedure-specific ectasia
  score; regression and haze remain separate clinical considerations.

## CER-AI operational hard stops

- Thinnest preoperative pachymetry `<480 µm`; exactly 480 is not stopped by this rule alone.
- CER-AI-modified LASIK pachymetry bands: `480–499 µm` = +2 points, `500–509 µm` = +1 point,
  and `>=510 µm` = +0 points.
- LASIK RSB `<300 µm`; exactly 300 is allowed by this rule.
- PRK RST `<310 µm`; exactly 310 is allowed by this rule.
- Intended sphere `<−10.00 D`; exactly −10.00 is allowed by this rule.
- Intended sphere `>+6.00 D`; exactly +6.00 is allowed by this rule.
- PRK epithelium is fixed at 50 µm for CER-AI calculations.

## Shared PTA amendment — September 8, 2026

Surgeon instruction: “for prk,too, same pta rule as lasik shall apply.”
Both procedures require PTA `<40%`; exact 40% and higher fail the evaluated plan.
PRK applies this independent STOP-DEFER gate in direct selection and automatic LASIK→PRK
assessment, retaining the original requested PRK treatment settings and the 50 µm epithelial
convention. LASIK retains its existing A→B→C candidate sequence; no flap-based Plan C is
introduced for PRK. Passing PTA alone does not clear any other clinical requirement.
The historical 35.28% cohort maximum has no separate operational caution or stop.
This is approved CER-AI policy, not a claim of a validated PRK literature threshold.

## Tissue formulas

- PRK `RST = CCT − 50 − maximum stromal ablation`.
- PRK `PTA = (50 + maximum stromal ablation) / CCT × 100`.
- LASIK `RSB = CCT − flap − maximum stromal ablation`.
- LASIK `PTA = (flap + maximum stromal ablation) / CCT × 100`.
- Actual planned maximum ablation is preferred. CER-AI EX500 estimation is limited to 12 µm/D at
  6.0 mm, 15 µm/D at 6.5 mm, and 16.33 µm/D at 7.0 mm.

## Final combination of scoring systems

The canonical final disposition counts CAUTION results from completed ERSS, NICE,
PS3 and Final BAD-D: zero or one = PASS; two = PASS WITH CAUTION; three or four = CAUTION.
Independent cautions retain CAUTION. Missing critical data blocks completion;
STOP-DEFER overrides every other result. Both caution outcomes are orange.
Bilateral aggregation preserves the worse eye, without adding caution counts across eyes.
Individual ERSS/NICE/PS3 scoring and procedural hard stops remain unchanged.

## Published/provisional instruments

- LASIK uses the published five-component ERSS: Placido topography, RSB, age, pachymetry, and
  manifest MRSE. Score 0–2 is PASS if no other concern is present, 3 is CAUTION without automatic
  defer, and ≥4 is STOP-DEFER.
- PRK uses the same canonical ERSS component thresholds and includes its disposition in
  the four-system result; its residual stroma supplies the tissue component.
- The canonical signed I-S and independent geometric SRAX feed one non-additive ERSS topography
  component. General visual morphology scoring is retired; no image-model morphology category
  may create points or an independent override. Numeric categories are not relabeled as a
  definitive diagnosis. Negative I-S retains its signed category and cannot be converted to
  inferior steepening by SRAX in ERSS or PS3; a measured SRAX remains visible but does not create
  an inferior-risk factor. SRAX >20.0° is positive when signed I-S is nonnegative; exactly 20.0° is negative.
- Final BAD-D is the sole BAD disposition authority. Df/Db/Dp/Dt/Da, PPI and ARTmax
  contextual colors do not independently add points, CAUTION or STOP-DEFER.
- PPI/ARTmax reference display bands are defined once in `clinical_core.bad`, using
  Ghiasian et al., J Curr Ophthalmol. 2022;34(2):200-207, Table 1,
  DOI 10.4103/joco.joco_249_21. Green = normal; orange = suspicious; red = abnormal.
  These are informational bands, not prospective post-refractive ectasia probabilities.
  PS3 retains its separate PPI Average >1.20 Moderate criterion.
- Check `PPImin ≤ PPIavg ≤ PPImax` and consistency of `ARTmax ≈ thinnest pachymetry / PPImax`.

## Clinical eligibility layer

- Instability or documented progression: `STOP-DEFER`, repeat relevant assessment and
  reassess after at least six months.
- Pregnancy/nursing: `STOP-DEFER`.
- Collagen/connective-tissue disease: `STOP-DEFER`.
- Eye rubbing/repetitive ocular trauma, family history of keratoconus, unexplained CDVA below
  20/20, relevant medication, dry eye, or other systemic disease: `CAUTION` with explicit
  surgeon review.
- Marked inter-eye asymmetry is evaluated by PS3 and is not duplicated as a patient-level
  clinical modifier. Anticipated enhancement is not part of the eligibility contract.
- These modifiers do not add invented ectasia-score points.
- The server readiness gate uses soft contact lens washout ≥10 full days and rigid/RGP ≥21 full
  days, as recorded in the launch contract and owned by `clinical_core.readiness`. Missing or
  insufficient washout blocks assessment. These operational criteria are not ectasia score points.

## Output semantics

- Missing/unknown decision-critical data prohibit PASS.
- `CAUTION` requires explicit surgeon review but does not automatically defer surgery.
  Any specific follow-up or reassessment interval must come from the finding that triggered
  CAUTION; it is not implied by the category itself.
- Overall status is the least favorable eye or global integrity gate.
- PASS is decision support, not a guarantee of zero ectasia risk and not autonomous surgical clearance.
- Every hyperopic/mixed report contains a case-specific `Surgeon attention` section. The final
  surgical decision and all associated responsibility and liability rest with the surgeon. The
  application is a clinical decision-support aid only.

### PRK shared ablation and ERSS evaluation — 2026-09-08

LASIK and PRK resolve requested myopic ablation through the same canonical estimator when no entered maximum ablation is supplied. Entered ablation takes precedence. PRK includes the canonical ERSS result alongside NICE, PS3 and final BAD-D in the four-system disposition. ERSS uses the same component thresholds, with PRK residual stroma (thinnest pachymetry minus 50 µm epithelium minus ablation) supplying the tissue input. A full PRK report requires complete ERSS. Do not emit an ERSS-not-applicable warning for PRK.

CER-AI-modified PS3 LASIK thinness exception: the underlying PS3 rule remains one Moderate factor = PRK and SMILE allowed / LASIK deferred; two Moderate factors or one High factor = all procedures deferred. When thinnest pachymetry is 490-500 µm inclusive and is the sole PS3 Moderate factor, LASIK may be reported as PASS WITH CAUTION only if Randleman/ERSS, NICE, and Final BAD-D are each PASS. Any CAUTION, STOP-DEFER, or incomplete result in those three systems preserves the raw PS3 LASIK defer. Independent tissue-safety and eligibility gates remain controlling. The report must show both the raw PS3 LASIK defer and the explicitly labeled CER-AI modification.

### PS3 prescription-axis source — 2026-09-08

Manifest-versus-topographic astigmatic disparity is a separate measurement/refraction validation item, not a PS3 factor. It uses `bad_flat_axis_deg`, read directly from the BAD Display upper-middle Axis box beside K1, and the normalized minus-cylinder manifest axis, using the smaller separation modulo 180 degrees. A magnitude difference `>=1.00 D` or axis difference `>=10°` requests validation but does not change PS3 counts or independently restrict LASIK, PRK, or SMILE. Missing disparity inputs remain passive and do not make PS3 incomplete. Do not transpose the prescription again, rotate a steep-axis value, or substitute another map. All steep-axis fields, their source locks, and SRAX geometry retain their existing independent roles.

### ML7 keratometry source — 2026-09-08

ML7 reads dedicated `ml7_k1_d` and `ml7_k2_d` from the labeled K1/K2 values associated with Anterior Sagittal Curvature (Front) on the 4 Maps Refractive page. The canonical ML7 input selects their maximum as steepest K and minimum as flattest K. BAD Display K1/K2, Kmax, and general-scoring K1/K2 are not substituted. Existing scoring keratometry, axis sources, and SRAX are unchanged. HWTW remains source-locked to the 4 Maps Refractive lower-left HWTW box and requires verified source or surgeon-confirmed provenance. Missing ML7 K1/K2 and missing verified HWTW are reported separately with exact source guidance; no ring is inferred when required inputs are absent.

Temporal is the default preferred hinge location. When `steepest K - flattest K >4.00 D`, hinge planning may change according to the steep meridian: a vertical steep meridian (`60°–120°`, inclusive) changes the preference to superior; a horizontal steep meridian (`0°–30°` or `150°–180°`, inclusive) retains temporal, with nasal as the secondary location. Intervening oblique or unavailable axes retain temporal and require surgeon judgment before any change. If the preferred superior hinge is anatomically impractical, the surgeon may select a temporal or nasal hinge with a `+10` blade only when recalculated RSB is `>=300 µm` and PTA is `<40%`.

### Automatic PRK evaluation after LASIK failure — 2026-09-08

A definitive LASIK STOP-DEFER triggers one PRK evaluation per failed eye. Incomplete LASIK alone does not trigger the transition. The original LASIK assessment and candidate history remain in `lasik_assessment`. PRK uses the requested correction, requested optical zone, and shared ablation resolution; the flap is None. All PRK tissue, ERSS, NICE, PS3, BAD and eligibility rules run through the same canonical core. A successful fellow-eye LASIK plan is unchanged. The workflow exposes an eye-specific warning, “LASIK failed. Now evaluating PRK.”, including when completion inputs remain missing. The evaluated PRK result is not an automatic clearance: shared stops and missing inputs remain effective. Browser presentation contains no clinical decision logic.


### SRAX surgeon confirmation — 2026-09-09

For nonnegative signed I-S, application-measured SRAX above 20° requires an explicit
surgeon YES/NO answer before the final report is issued. The shared decision owner
is `srax_policy.srax_positive`; ERSS and PS3 consume this decision.
YES confirms the existing SRAX-positive scoring; NO rejects the positive classification.
The measured degrees remain visible and the existing correction audit records the answer.
An unanswered question is incomplete, never silently NO. Exactly 20° does not trigger
this confirmation. Negative signed I-S skips the question and retains the existing
signed-I-S category and SRAX exclusion. Other clinical findings still apply.
The existing completion workflow presents one question per applicable eye and blocks
the final report until it is resolved; no report-side score correction is used.
