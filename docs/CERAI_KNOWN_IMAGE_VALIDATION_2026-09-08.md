# CER-AI known-image validation — 2026-09-08

## Historical evidence scope

The transcription and simulation below are retained as historical evidence for this supplied image set. They are not a complete acceptance of the later staging release. The original absence of a local model credential does not describe Railway staging, where model extraction was subsequently observed.

The later PS3 axis amendment uses the BAD upper-middle flat Axis beside K1; it does not redefine the independent Show 2 `K1_axis_deg` field. ML7 now reuses the existing canonical K1/K2 rather than maintaining a duplicate pair. Missing Show 2 K1 axis in this historical table must not be used to claim that the PS3 BAD flat axis is absent. See the updated master matrix and production review for current validation gaps.

## Subsequent accepted PS3 amendment

The historical simulation below predates policy `CER-AI-2026-09-08-PS3-GT3`.
The surgeon subsequently required astigmatism comparison only when either manifest
cylinder magnitude or topographic astigmatism is >3.00 D. Both values <=3.00 D
produce no risk factor. Thus the historical OD Moderate/PS3 LASIK-defer conclusion
below is superseded: OD 0.50/0.40 D does not activate this factor. This correction is
covered through the canonical runtime and report-payload regression; it is not a
new complete clinical assessment or a deployment claim. PS3 also now always evaluates
the shared SRAX input, including when another factor already requires deferral.

## Scope and release status

The supplied bilateral Pentacam set was manually checked against the visible canonical boxes.
Patient identifiers are intentionally excluded from this repository record. The images remain
outside the repository.

This is **partial item-63 evidence**, not a production extraction pass. The current workspace has
no configured extraction-model credential, so `app.extract_one_image` could not be executed.
No claim is made that OCR/model runtime output equals the visible values until that run occurs.

## Direct visible canonical values

| Canonical target | OD | OS | Canonical visible region |
|---|---:|---:|---|
| K1 | 42.2 D | 42.0 D | Show 2 Exams, Cornea Front |
| K1 axis | UNREADABLE | UNREADABLE | No direct numeric K1-axis field is visible; perpendicular derivation is prohibited |
| K2 | 42.6 D | 42.5 D | Show 2 Exams, Cornea Front |
| K2 / displayed steep axis | 84.5° | 107.0° | Show 2 Exams, Cornea Front |
| Km | 42.4 D | 42.2 D | Show 2 Exams, Cornea Front |
| Astigmatism | 0.4 D | 0.5 D | Show 2 Exams, Cornea Front |
| Posterior Rmin | 6.15 mm | 6.28 mm | Show 2 Exams, Cornea Back |
| ISV | 15 | 18 | Show 2 Exams, center 8-mm indices |
| IVA | 0.09 | 0.15 | Show 2 Exams, center 8-mm indices |
| KI | 1.04 | 1.05 | Show 2 Exams, center 8-mm indices |
| CKI | 1.01 | 1.01 | Show 2 Exams, center 8-mm indices |
| IHA | 0.4 | 4.5 | Show 2 Exams, center 8-mm indices |
| IHD | 0.012 | 0.018 | Show 2 Exams, center 8-mm indices |
| Topometric RMin | 7.84 | 7.84 | Show 2 Exams, center 8-mm indices |
| TKC | `-` | `poss.` | Show 2 Exams, center 8-mm indices |
| KISA | 6.533 | 13.229 | Show 2 Exams, center 8-mm indices |
| Signed I-S | +0.61 D | +1.03 D | Show 2 Exams, center 8-mm indices |
| Pupil Center pachymetry | 530 µm | 532 µm | 4 Maps Refractive, lower-left numeric box |
| Thinnest pachymetry | 529 µm | 529 µm | 4 Maps Refractive, lower-left numeric box |
| Kmax Front | 43.1 D | 43.0 D | 4 Maps Refractive, lower-left numeric box |
| HWTW | 12.1 mm | 12.1 mm | 4 Maps Refractive, lower-left numeric box |
| F.Ele.Th | 3 µm | 4 µm | BAD, central numeric box |
| B.Ele.Th | 6 µm | 7 µm | BAD, central numeric box |
| PPI Min | 0.67 | 0.65 | BAD, Progression Index section |
| PPI Avg | 0.98 | 0.96 | BAD, Progression Index section |
| PPI Max | 1.38 | 1.21 | BAD, Progression Index section |
| ARTmax | 382 | 437 | BAD, Progression Index section |
| Df | 1.17 | 2.43 | BAD, bottom strip |
| Db | 0.69 | 1.65 | BAD, bottom strip |
| Dp | 0.51 | 0.38 | BAD, bottom strip |
| Dt | 0.25 | 0.25 | BAD, bottom strip |
| Da | 0.96 | 0.47 | BAD, bottom strip |
| Final BAD-D | 0.99 | 1.51 | BAD, bottom strip |

The BAD central-box K axes were not used to populate the source-locked Show 2 axis fields. The
Elevation Back color maps were not used for B.Ele.Th. Posterior Rmin and topometric RMin remain
separate.

## Direct geometric SRAX runtime

`geometric_srax_policy.measure_srax` (`srax-geom-v2`) ran on the two supplied 4 Maps Refractive
images. It used only the anterior Axial/Sagittal Curvature map geometry.

| Eye | Superior steep hemimeridian | Inferior steep hemimeridian | SRAX | Result |
|---|---:|---:|---:|---|
| OD | 65.9° | 247.9° | 2.0° | NO — not skewed |
| OS | 75.4° | 256.4° | 1.1° | NO — not skewed |

The decision rule is strict: `>20.0°` is positive; exactly `20.0°` is negative.

## Canonical runtime simulation from verified transcription

The directly verified values were passed to the canonical runtime with the supplied age and
treatment refractions. To isolate engine behavior, the simulation marked the otherwise-unsupplied
eligibility questions as negative; therefore these are **not surgeon-confirmed clinical results**.
Myopic ablation was the canonical estimate because no actual maximum ablation value was supplied.

| Result | OD | OS |
|---|---:|---:|
| Manifest = intended | −1.25 −0.50 ×120 | −1.50 DS |
| Estimated maximum ablation | 22.5 µm | 22.5 µm |
| LASIK RSB | 406.5 µm | 406.5 µm |
| LASIK PTA | 23.16% | 23.16% |
| ERSS | 1 | 3 |
| NICE | 4 | 5 |
| PS3 complete | Yes | Yes |
| PS3 Moderate / High | 0 / 0 | 0 / 0 |
| Canonical runtime status | PASS | CAUTION |
| Plan | Plan A | Plan A |

OD manifest/topographic astigmatic-axis disparity is retained as a separate measurement-validation
warning; it is not a PS3 factor and does not independently restrict LASIK. OS spherical manifest
refraction has no meaningful axis, so no axis comparison is made.

For both eyes, PTA is below 40%; the binding `PTA >=40%` failure rule is not activated. Plan A/B/C
fallback therefore is not triggered by tissue percentage in this case.

## Remaining acceptance work

1. Run the actual extraction runtime on these images with its configured model credential and
   compare every returned field with the table above.
2. Obtain surgeon answers for prior refractive surgery, stability/progression, CDVA, and all
   clinical modifiers before treating the simulation as a complete assessment.
3. Generate and inspect the real PDF, archive the case, reopen it, and verify attribution.
4. Keep the image set out of git unless it has been formally de-identified and approved as a test
   fixture.
