# Universal toric IOL calculation: research status

The prototype in `research/toric_vergence.py` is **not available in the clinical
application**. It reproduces the continuous optical result of the published
Castrop example 1, but does not select an implant, predict a validated clinical
outcome, or replace the manufacturer calculator. Do not route patients to it.

## First lens and surgeon input contract (research only)

`research/panoptix_toric_contract.py` records the surgeon's choice of Clareon
PanOptix Toric and the standard IOLMaster 500 anterior K1/K2 and both axes.
The incision is on the measured steep **K2 axis**, and the surgeon's stipulated
SIA is **0.25 D**. The K2 axis is normalized modulo 180 degrees; implausible
or inconsistent readings are rejected rather than silently repaired. These
settings express a planning assumption, not a validated prediction.

| Model | Cylinder at IOL plane (D) |
| --- | ---: |
| CNWTT2 | 1.00 |
| CNWTT3 | 1.50 |
| CNWTT4 | 2.25 |
| CNWTT5 | 3.00 |
| CNWTT6 | 3.75 |

The digit after `CNWTT` is a model step, **not its diopter value**. CNWTT1
was requested but could not be established in the manufacturer's product
listings or the Australian device listing, so it is deliberately absent. The
manufacturer's Japanese launch specification lists T3–T6, while an Australian
listing and other regional Alcon pages list T2–T6. Availability in Türkiye
and specific inventory still need confirmation. These are IOL-plane powers;
corneal-plane effect changes with eye geometry and cannot be substituted by a
single fixed conversion. The surgeon clarified that the Pentacam Cataract
Pre-OP image in this workflow contains posterior corneal astigmatism data.
Pair IOLMaster 500 anterior K1/K2 and axes with the same eye's Pentacam
posterior data; do not silently replace a readable direct measurement with a
population estimate. Verify the exact printed label, sign convention, optical
zone, and posterior axis (or posterior meridional radii) on the actual image.
A scalar posterior magnitude without an axis is insufficient for vector
calculation. TCRP total-corneal astigmatism is not itself a separate posterior
measurement. The Castrop model constants still need to be established.

### Castrop Table 1: source mapping for this workflow

Use the measured-data branch of the published formula only when its actual
inputs are available. The Pentacam posterior *astigmatism* number by itself
cannot be inserted as the formula's posterior *radii*.

| Formula input | Proposed source | Requirement |
| --- | --- | --- |
| AL | IOLMaster 500 upper biometry | Confirm eye and printed/edited status. |
| Anterior RCA1, RCA2 and axis ACA1 | IOLMaster 500 K1/K2 and axes | Confirm the device keratometric index before converting D to physical mm. |
| Posterior RCP1, RCP2 and axis ACP1 | Same-eye Pentacam posterior-surface readout | Verify both meridional radii and their axis; posterior cylinder magnitude alone is insufficient. |
| CCT | Pentacam Pachy Vertex | Check unit and same eye. |
| External ACD | Pentacam ACD (Ext.), or ACD (Int.) + Pachy Vertex/1000 | Confirm which value is printed; do not add CCT twice. |
| Crystalline lens thickness LT | Explicitly printed biometry | Current extractor allows null; absence blocks this formula. |
| Target sphere, cylinder and axis | Surgeon target | Document the spherocylindrical target, including zero cylinder. |
| SIA magnitude and axis | Surgeon: 0.25 D at measured K2 axis | Surgeon-defined assumption. |
| C, H, R | Provenance-checked model-specific optimized constants | A-constant 119.1 does not substitute for these three values. |
| Lens cylinder steps | Verified CNWTT2–6 catalog | Select a discrete product only after continuous calculation is validated. |

The paper permits a fallback using assumed posterior radii and a statistical
CPA when tomography is unavailable. For this workflow, direct Pentacam data
have been reported, so this fallback is not the selected branch. If the
standard uploaded screen shows only posterior astigmatism magnitude, obtain a
posterior curvature readout that explicitly contains both radii and the axis;
do not infer them from the magnitude or from TCRP.

## Why toric calculation differs from spherical IOL power

A toric result needs a cylinder magnitude and implantation axis in addition to
spherical equivalent power. Anterior K and its axis, posterior corneal
astigmatism, incision-induced astigmatism as a double-angle vector, effective
lens position, and the available cylinder steps of the actual implanted model
all matter. ESCRS recommends methods accounting for posterior cornea and ELP.

The published Castrop toric formula is a possible manufacturer-neutral optical
core. It uses a thick cornea, thin IOL, three *model-specific* constants C/H/R,
and full spherocylindrical vergence. Its article presents numerical examples,
not a prospective validation of the new method. Our research implementation
matches its tomography example within rounding. This establishes one
calculation identity; it does not establish surgical accuracy.

## Current application gaps

1. The existing catalog lists spherical model IDs such as `CNWTT0`, `DEN00V`,
   and `DRN00V`. Their toric counterparts have distinct model IDs and discrete
   cylinder powers. A manufacturer calculator link on a spherical model is
   not a toric model catalog.
2. Catalog A-constants cannot be substituted for the Castrop C, H and R
   constants. Neither the toric model's allowed sphere/cylinder combinations
   nor current availability in the clinic are established.
3. Existing Pentacam `ACD (Int.)` excludes corneal thickness. The Castrop paper
   requires **external ACD** from the anterior corneal vertex. For this model,
   external ACD = internal ACD + CCT/1000, using a confirmed same-eye CCT.
4. The existing IOLMaster anterior K1/K2 and axes are authoritative for the
   current clinical toric trigger. Converting keratometric D to *physical*
   anterior radii requires the device keratometric index. The surgeon reports
   posterior astigmatism on the Pentacam Cataract Pre-OP images, but current
   `iol_module/extraction.py` does not transcribe its magnitude or axis. The
   actual posterior field and its convention need source verification; a
   cylinder magnitude alone does not provide two physical posterior radii.
5. The surgeon supplied SIA 0.25 D and incision on K2; these may be used as
   explicit planning assumptions and should be checked against postoperative
   vector data before a lens recommendation is enabled.
6. Prior refractive surgery, irregular astigmatism, absent or discrepant
   biometry, and unavailable lens constants need explicit unsupported routes.

## Requirements before a surgeon-facing calculator

- Confirm the *actual toric model IDs* stocked or offered in Türkiye, and
  manufacturer documentation for each sphere range and cylinder step.
- Source current model-specific optimized constants and their provenance.
- Source-lock the actual Pentacam posterior magnitude **and axis**, or both
  posterior meridional radii and orientation, with measurement conventions.
  Do not confuse TCRP total astigmatism with posterior astigmatism.
- Record surgeon-specific incision location and SIA, including their axis
  convention. Validate left/right and 0/180-degree boundaries.
- Compare the independent implementation against published examples and a
  de-identified paired dataset of manufacturer/ESCRS outputs, across both eyes,
  with-the-rule/against-the-rule/oblique axes, short/normal/long AL, shallow/deep
  ACD, all supported toric cylinder steps, and missing-data cases. Record
  differences and adjudicate them before any clinical activation.
- Validate postoperative refractive prediction and lens selection on an
  independent consecutive clinical dataset before claiming clinical accuracy.
- Integrate exactly one clinical toric planning function only after those
  gates; retire the manufacturer-only route then. Preserve a manufacturer
  comparison link and show provenance, uncertainty, and residual cylinder.

## Primary sources

- ESCRS cataract guideline: https://www.escrs.org/escrs-recommendations-for-cataract-surgery
- Castrop toric derivation and examples: https://doi.org/10.1007/s00417-021-05287-w
- J&J toric calculator FAQ (anterior K only): https://tecnistoriccalc.com/pdfs/DHF1641B-3301-EN.pdf
- J&J toric model availability: https://www.jnjvisionpro.com/en-us/products/tecnis-odyssey/
- Alcon toric model information: https://www.myalcon.com/professional/cataract-surgery/iols/clareon-toric/
- Alcon Clareon PanOptix model and cylinder specifications: https://www.alcon.co.jp/media-release/20220413-clareon-panoptix
- Australian Clareon PanOptix Toric device listing (T2–T6): https://www.legislation.gov.au/F2024L01355/asmade/2024-10-24/text/original/pdf/2

ESCRS already supports toric formula comparison and a biometry handoff, but its
published toric route and model coverage must be checked in a live calculation
before treating it as an embedded calculator. No undocumented manufacturer
web-form parameters should be used as a clinical data-transfer interface.
