# Universal toric IOL calculation: research status

The prototype in `research/toric_vergence.py` is **not available in the clinical
application**. It reproduces the continuous optical result of the published
Castrop example 1, but does not select an implant, predict a validated clinical
outcome, or replace the manufacturer calculator. Do not route patients to it.

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
   anterior radii requires the device keratometric index. Posterior curvature
   and axis require a separately source-locked Pentacam measurement; neither
   should be fabricated from the current stage-1 optical fields.
5. Surgeon-specific SIA should come from postoperative vector data; an
   unverified default must not silently produce a lens recommendation.
6. Prior refractive surgery, irregular astigmatism, absent or discrepant
   biometry, and unavailable lens constants need explicit unsupported routes.

## Requirements before a surgeon-facing calculator

- Confirm the *actual toric model IDs* stocked or offered in Türkiye, and
  manufacturer documentation for each sphere range and cylinder step.
- Source current model-specific optimized constants and their provenance.
- Add source-locked corneal front and back curvature/axis extraction or a
  validated posterior cornea estimation pathway, with measurement conventions.
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

ESCRS already supports toric formula comparison and a biometry handoff, but its
published toric route and model coverage must be checked in a live calculation
before treating it as an embedded calculator. No undocumented manufacturer
web-form parameters should be used as a clinical data-transfer interface.
