# HC Preoperative Ectasia Risk Assessment — Software Rule Specification v0.6

Effective date: 26 August 2026

This file is the code-aligned operational rule specification. Published evidence, provisional
triage, HC operational policy, imaging-quality criteria, and general clinical eligibility are kept
as separate layers. No rule in one layer is silently presented as a validated rule from another.

## Case and source integrity gate

- Extract and compare patient ID/name, DOB, examination date/time, laterality, filename, and
  literal Pentacam QS.
- Conflicting patient ID, DOB, or Pentacam examination date prohibits PASS.
- A mismatch between entered and source patient ID, DOB, or derived age prohibits PASS.
- Both OD and OS are required for overall PASS; eyes remain separately assessed and are not averaged.
- An unclassified upload, an upload yielding no usable eye/treatment data, a limited/inadequate
  decision-source image, or an unresolved decision-field conflict prohibits PASS.
- Pentacam clearance requires a same-exam explicit `QS: OK`; a visible non-OK QS cannot be overridden.
- Record field-level provenance as labeled table, permitted map fallback, or visual classification.

## Pathway gate

- `prior PRK/LASIK/SMILE = yes` exits the virgin-cornea engine immediately and returns
  `POST-REFRACTIVE PATHWAY REQUIRED`.
- Unknown prior-surgery status prohibits PASS.

## Refraction and plan separation

- LASIK ERSS MRSE uses preoperative manifest sphere and minus-cylinder magnitude:
  `MRSE = manifest sphere − manifest cylinder magnitude / 2`.
- Ablation and HC treatment-range gates use intended treatment sphere/cylinder only.
- Treatment-card extraction may auto-fill intended correction only from `Düzeltme Miktarı`.
- Invalid numeric ranges are not used in any formula.

## HC operational hard stops

- Thinnest preoperative pachymetry `<480 µm`; exactly 480 is not stopped by this rule alone.
- LASIK RSB `<300 µm`; exactly 300 is allowed by this rule.
- PRK RST `<310 µm`; exactly 310 is allowed by this rule.
- Intended sphere `<−10.00 D`; exactly −10.00 is allowed by this rule.
- Intended sphere `>+6.00 D`; exactly +6.00 is allowed by this rule.
- PRK epithelium is fixed at 50 µm for HC calculations.

## Tissue formulas

- PRK `RST = CCT − 50 − maximum stromal ablation`.
- PRK `PTA = (50 + maximum stromal ablation) / CCT × 100`.
- LASIK `RSB = CCT − flap − maximum stromal ablation`.
- LASIK `PTA = (flap + maximum stromal ablation) / CCT × 100`.
- Actual planned maximum ablation is preferred. HC EX500 estimation is limited to 12 µm/D at
  6.0 mm, 15 µm/D at 6.5 mm, and 16.33 µm/D at 7.0 mm.

## Published/provisional instruments

- LASIK uses the published five-component ERSS: Placido topography, RSB, age, pachymetry, and
  manifest MRSE. Score 0–2 is low, 3 is moderate/STOP-DEFER, and ≥4 is high/DO NOT PROCEED.
- PRK-EWSS v1.0 is an HC provisional triage score and is not validated. It does not produce a risk
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
