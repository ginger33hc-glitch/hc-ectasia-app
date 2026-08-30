# CER-AI Preoperative Ectasia Risk Assessment — Software Rule Specification v0.7

Effective date: 26 August 2026

This file is the code-aligned operational rule specification. Published evidence, provisional
triage, CER-AI operational policy, imaging-quality criteria, and general clinical eligibility are kept
as separate layers. No rule in one layer is silently presented as a validated rule from another.

## Case and source integrity gate

- Extract and compare patient ID/name, printed age, examination date/time, laterality, filename, and
  literal Pentacam QS.
- Conflicting patient age or Pentacam examination date prohibits PASS; identity uncertainty remains
  a visible surgeon-confirmation warning without suppressing the eye analyses.
- A mismatch between entered and source patient ID or derived age prohibits PASS.
- Both OD and OS are required for overall PASS; eyes remain separately assessed and are not averaged.
- An unclassified upload, an upload yielding no usable eye/treatment data, a limited/inadequate
  decision-source image, or an unresolved decision-field conflict prohibits PASS.
- Pentacam clearance requires a same-exam explicit `QS: OK`; a visible non-OK QS cannot be overridden.
- Record field-level provenance as labeled table, permitted map fallback, or visual classification.
- Same-field readings from one accepted provenance class reconcile only when their full relative
  spread is `<=1%`. Retain the lower value for pachymetry, ARTmax, and Rmin; retain the higher value
  for BAD-D, Kmax, elevation, PPI, and other supported ectasia indices. Larger differences remain
  unresolved conflicts.

## Pathway gate

- `prior PRK/LASIK/SMILE = yes` exits the virgin-cornea engine immediately and returns
  `POST-REFRACTIVE PATHWAY REQUIRED`.
- Unknown prior-surgery status prohibits PASS.

## Refraction and plan separation

- LASIK ERSS MRSE uses preoperative manifest sphere and minus-cylinder magnitude:
  `MRSE = manifest sphere − manifest cylinder magnitude / 2`.
- Ablation and CER-AI treatment-range gates use intended treatment sphere/cylinder only.
- Treatment-card extraction may auto-fill intended correction only from `Düzeltme Miktarı`.
- Invalid numeric ranges are not used in any formula.
- Manifest and intended corrections are normalized to minus-cylinder notation, then classified
  from their two principal meridians as myopic, hyperopic, simple astigmatism, or mixed
  astigmatism. Entering an equivalent plus-cylinder notation must not change the classification.
- A valid axis is required whenever the manifest or intended cylinder is non-zero. Missing or
  invalid axis data prohibit PASS; plus-cylinder transposition without an axis is never cleared.

## Hyperopic and mixed-astigmatism pathway

- The report is generated even when this pathway cannot receive PASS; available tomography,
  structural calculations, missing plan data, and known hard stops remain visible.
- Actual laser-plan maximum stromal ablation is mandatory. The CER-AI linear myopic EX500 µm/D
  convention is not applied to hyperopic annular or mixed bitoric profiles.
- Hyperopic/mixed cases receive `REVIEW — NOT CLEARED` because the supplied procedure-specific
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

## Tissue formulas

- PRK `RST = CCT − 50 − maximum stromal ablation`.
- PRK `PTA = (50 + maximum stromal ablation) / CCT × 100`.
- LASIK `RSB = CCT − flap − maximum stromal ablation`.
- LASIK `PTA = (flap + maximum stromal ablation) / CCT × 100`.
- Actual planned maximum ablation is preferred. CER-AI EX500 estimation is limited to 12 µm/D at
  6.0 mm, 15 µm/D at 6.5 mm, and 16.33 µm/D at 7.0 mm.

## Published/provisional instruments

- LASIK uses the published five-component ERSS: Placido topography, RSB, age, pachymetry, and
  manifest MRSE. Score 0–2 is low, 3 is moderate/STOP-DEFER, and ≥4 is high/DO NOT PROCEED.
- PRK-EWSS v1.0 is an CER-AI provisional triage score and is not validated. It does not produce a risk
  probability.
- A single numeric Placido criterion may support the published ERSS topography category but is not
  relabeled as definite keratoconus. A definite visible KC/FFKC/PMD/ectatic morphology remains a
  separate override.
- BAD components/final D and supplied ARTmax/TP/Dt/Da thresholds are adjunctive review signals, not
  prospective post-refractive ectasia probabilities.
- Check `PPImin ≤ PPIavg ≤ PPImax` and consistency of `ARTmax ≈ thinnest pachymetry / PPImax`.

## Clinical eligibility layer

- Instability or documented progression: `CAUTION — STOP/DEFER`, repeat relevant assessment and
  reassess after at least six months.
- Pregnancy/nursing: `CAUTION — STOP/DEFER`.
- Unexplained CDVA below 20/20, inter-eye asymmetry, collagen/connective-tissue disease, relevant
  medication, dry eye, or other systemic disease: `REVIEW — NOT CLEARED` until resolved.
- These modifiers do not add invented ectasia-score points.
- Soft contact lens ≥14 days and rigid/RGP ≥21 days are supplied source-study imaging criteria, not
  universal ectasia cutoffs. Insufficient documentation prohibits automatic PASS.

## Output semantics

- Missing/unknown decision-critical data prohibit PASS.
- `CAUTION` always means STOP/DEFER and reassessment after at least six months.
- Overall status is the least favorable eye or global integrity gate.
- PASS is decision support, not a guarantee of zero ectasia risk and not autonomous surgical clearance.
- Every hyperopic/mixed report contains a case-specific `Surgeon attention` section. The final
  surgical decision and all associated responsibility and liability rest with the surgeon. The
  application is a clinical decision-support aid only.
