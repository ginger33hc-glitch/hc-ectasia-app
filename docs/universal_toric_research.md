# Universal toric IOL calculation: research status

## Current embedded test workflow (2026-09-25)

When IOLMaster K2−K1 is at least 1.00 D and astigmatism is regular, the
surgeon chooses a toric lens family. Cooke K6 calculates the spherical
equivalent first. With the same-eye Pentacam 4 Maps Refractive Cornea Back
K1/K2, axes and Rh/Rv and the Cataract Pre-Op Pachy Vertex, the embedded
prototype computes ranked cylinder models, plus-cylinder marker axes, and
predicted residuals. The incision and SIA axis follow steep K2 at 0.25 D.
The manufacturer's official calculator is a separate optional comparison.
Missing, incompatible or unverified data prevent a model and axis result.

Results are available in authenticated doctor and OWNER sessions and are
prominently marked **TEST ONLY**. The combined K6 / Holladay 1 /
posterior-cornea optical method is our prototype, not an identical manufacturer
implementation, and has no paired clinical validation. Its first-ranked
model and axis are not implant recommendations. ENOVA lacks a verified
cylinder-step catalog and returns no toric model. Catalog entries name lens
families; their historical IDs denote clinic-supplied examples, not mandatory
cylinder steps. Stock and sphere/cylinder combination availability remain
unverified. Crystalline lens thickness is never estimated.

The older research notes below are retained for provenance. Descriptions of
a spherical-only live route are superseded by this **test-only** workflow.

## Manufacturer methodology confirmed on 2026-09-25

Johnson & Johnson's current TECNIS Toric Calculator FAQ (Rev. 08, April 2026)
explicitly identifies **Holladay 1** for eye-specific cylinder calculations and
accepts the spherical-equivalent IOL power calculated using the surgeon's
preferred method. Its supplied posterior-corneal correction is a proprietary
clinical-data algorithm, not a disclosed numerical formula, and it insists on
anterior rather than total-corneal K inputs. The published Holladay 1 ELP
uses AL, mean K, and a surgeon factor without crystalline LT; Alcon publishes
the SF conversion `SF = 0.5663 × optical A − 65.6008`. This provides an
LT-free, published optical-position method anchored to the clinic's A list.
The `holladay1_elp_mm` function in `iol_module/toric_formula.py` implements
that step, separately from the existing K6 spherical calculation. It does
**not** make the combined K6/Holladay toric optical model clinically validated.

Alcon's current online toric calculator advertises Barrett Toric and Holladay
Total SIA Toric. Barrett's internal calculation and the Alcon implementations
were not disclosed in the public sources inspected; do not label our code as
an identical implementation. Alcon FDA P190018B confirms CNW0T3–9 powers,
the plus-cylinder marker-axis convention and corneal-plane correction in an
*average* eye, not a universal fixed ratio for every patient.

Sources: https://www.tecnistoriccalc.com/pdfs/DHF1641B-3301-EN.pdf ;
https://www.tecnistoriccalc.com/pdfs/DHF1641B-3300-EN.pdf ;
https://link.springer.com/chapter/10.1007/978-3-031-50666-6_44 ;
https://us.alconscience.com/sites/g/files/rbvwei1736/files/pdf/1906A277-US-ORA-19-E-1275-Lens-Constants-White-Paper.pdf ;
https://www.myalcon-toriccalc.com/ ;
https://www.accessdata.fda.gov/cdrh_docs/pdf19/P190018B.pdf .

### Embedded K6-anchored optical prototype and validation boundary

`iol_module/toric_formula.py` now calculates Holladay 1 ELP without LT,
converts anterior IOLMaster K1/K2 to physical front-surface radii using
`nK=1.3375`, adds the measured signed Pentacam Cornea Back powers, applies
0.25 D SIA on the IOLMaster steep axis, and transforms the corneal vergence
to the IOL plane. The **K6 selected spherical-equivalent power and its Rx**
anchor the scalar retinal vergence; each published Alcon or TECNIS Eyhance
IOL-cylinder step is rotated to minimize the predicted spectacle-plane
residual. This is our own **hybrid optical prototype**, not the proprietary
J&J/Alcon algorithm nor a validated unified clinical formula. It has no
patient-facing model or axis output yet.

Tests include Castrop's published Table 2 numerical example, 30-degree
rotation invariance, posterior same-eye checks and an FDA Clareon Table 3
*average-eye* optical plausibility check: a synthetic 24 mm AL, 43 D symmetric
K and 20 D spherical IOL yields about 1.00 D corneal-plane effect for a
1.50 D cylinder; FDA's representative-eye table gives 0.98 D. This
approximately 0.02 D agreement **does not verify an individual toric
recommendation**. The manufacturer's public sites require accepting a legal
license before running paired synthetic inputs, and approval to accept that
agreement was not obtained. No real patient data were sent to these sites.

Clinical gating still needs paired eye-specific manufacturer outputs and/or
retrospective verified cases including K1/K2 axes, measured posterior
cornea, AL, selected SE and IOL model/axis, plus a checked cylinder-axis
convention. Until then, the K6 result in the live route is spherical only.

Eyhance DIU100/150/225/300/375/450/525 powers are documented by the
Johnson & Johnson EMEA product catalogue:
https://catalog.emeaassets.com/productsen/?page_id=1329 .

## 2026-09-25 workflow decision: no routine lens thickness

The surgeon checked with the Pentacam manufacturer: crystalline lens thickness
is only rarely measurable in the clinic's workflow. Therefore LT must **not**
be a required input in the intended three-image workflow (4 Maps Refractive,
Cataract Pre-OP, IOLMaster 500). The Castrop prototype remains a published
optics reference only; its ELP equation requires measured LT and its C/H/R
constants are not optimized for CNWTT2–6 in IOL Con. Do not fill LT with a
population value or transfer C/H/R from another lens.

The next candidate is a documented **LT-free spherical power/ELP method**
(the existing Cooke K6 v2024.01 route using the manufacturer's optical
A-constant for the selected lens),
combined with a separately verified thick-cornea toric vector step using the
same-eye Pentacam posterior measurements and the surgeon's SIA. This is an
architecture for comparison, **not** a validated combined clinical formula:
its ELP-to-cylinder vergence, anterior K index, posterior axis/sign, available
CNWTT steps and resulting sphere and axis must be checked against paired
manufacturer calculations and postoperative outcomes. If an independently
specified and validated LT-free toric formula better fits these inputs, use it
instead. Retain the current manufacturer comparison route meanwhile.

The clinic's photographed optical A-constant list names TECNIS Eyhance Toric
DIU525 (119.3), CLAREON Toric CNW0T8 (119.1), CLAREON PanOptix Toric CNWTT3
(119.1), and ENOVA Advance Toric (118.0; exact model code not listed). These
four entries are in the application catalog. The live K6 power service now
runs for regular toric cases and labels its output **spherical only**; it
does not compute toric cylinder, residual cylinder or implantation axis.
Manufacturer toric calculator comparison remains required. The clinic list
does not itself define the entire stock range or manufacturer cylinder steps.

The Castrop calculation core now lives in `iol_module/toric_formula.py`, but is
**not routed into patient-facing clinical results**. It reproduces the continuous optical result of the published
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
| Posterior RCP1, RCP2 and axis ACP1 | Existing same-eye Pentacam 4 Maps Refractive, left-side Cornea Back Rh/Rv, K1/K2 and axis | Rh/Rv are horizontal/vertical radii, not generally the principal radii in an oblique eye; verify the K conversion and axis before deriving RCP1/RCP2. |
| CCT | Pentacam Pachy Vertex | Check unit and same eye. |
| External ACD | Pentacam ACD (Ext.), or ACD (Int.) + Pachy Vertex/1000 | Confirm which value is printed; do not add CCT twice. |
| Crystalline lens thickness LT | Separately measured and documented source | ZEISS lists no LT measurement for IOLMaster 500; absence blocks this form of Castrop. Check whether the available Pentacam report actually prints `Lens Th.` with a value. |
| Target sphere, cylinder and axis | Surgeon target | Document the spherocylindrical target, including zero cylinder. |
| SIA magnitude and axis | Surgeon: 0.25 D at measured K2 axis | Surgeon-defined assumption. |
| C, H, R | Provenance-checked model-specific optimized constants | A-constant 119.1 does not substitute for these three values. |
| Lens cylinder steps | Verified CNWTT2–6 catalog | Select a discrete product only after continuous calculation is validated. |

The paper permits a fallback using assumed posterior radii and a statistical
CPA when tomography is unavailable. This workflow already uploads an OD and
OS Pentacam 4 Maps Refractive image for the refractive surgery module; the
left-side `Cornea Back` table prints posterior Rh, Rv, K1, K2 and axis. Source-lock
those fields separately for toric research on the existing images, without
changing the canonical refractive module or requesting another screen. The
current refractive extractor transcribes only posterior Km and Rmin from Show
2 Exams; these do not supply the pair of cardinal posterior radii. The new
research input contract stores the directly printed radii and signed K values
with axis but does not yet substitute the horizontal/vertical Rh/Rv for the
flat/steep Castrop radii. In an oblique cornea those are different directions.
ZEISS's IOLMaster 500 specification explicitly lists lens thickness as absent;
the formula also needs a verified LT source or a separately validated variant.

The surgeon's uploaded 4 Maps Refractive example confirms a `Cornea Back`
numeric group containing Rh/Rv, K1/K2, Astig and Axis, while its `Lens Th.`
box is blank. No patient identifiers or example measurements are retained in
this research note. In this example the missing LT is a real calculation
blocker, even though posterior surface information is present. IOL Con lists
no optimized Castrop C/H/R for **Clareon PanOptix Toric CNWTT2–6** as of this
review; nearby constants for other Alcon lenses must not be copied over.

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
   posterior astigmatism on the Pentacam Cataract Pre-OP images, and the
   existing refractive module's 4 Maps Refractive OD/OS images have a Cornea
   Back numeric panel. Neither current extractor transcribes its posterior
   K1/K2/axis trio. Do not substitute the already-extracted posterior Km/Rmin
   or the Cataract Pre-OP TCRP for the Castrop posterior radii.
5. The surgeon supplied SIA 0.25 D and incision on K2; these may be used as
   explicit planning assumptions and should be checked against postoperative
   vector data before a lens recommendation is enabled.
6. Prior refractive surgery, irregular astigmatism, absent or discrepant
   biometry, and unavailable lens constants need explicit unsupported routes.

## Requirements before a surgeon-facing calculator

- Confirm the *actual toric model IDs* stocked or offered in Türkiye, and
  manufacturer documentation for each sphere range and cylinder step.
- Source current model-specific optimized constants and their provenance.
- Source-lock posterior Rh, Rv, K1, K2 and axis from the **existing** 4 Maps
  Refractive Cornea Back numeric panel, checking the eye and convention for
  conversion into principal-meridian physical radii. Rh and Rv must not be
  relabeled as the oblique principal radii. Do not confuse TCRP total
  astigmatism with posterior astigmatism.
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
- ZEISS IOLMaster 500 capability table (no lens thickness): https://www.zeiss.com/meditec/en/products/optical-biometers.html
- IOL Con CNWTT2–6 constants status: https://www.iolcon.org/printLenses.php

ESCRS already supports toric formula comparison and a biometry handoff, but its
published toric route and model coverage must be checked in a live calculation
before treating it as an embedded calculator. No undocumented manufacturer
web-form parameters should be used as a clinical data-transfer interface.
