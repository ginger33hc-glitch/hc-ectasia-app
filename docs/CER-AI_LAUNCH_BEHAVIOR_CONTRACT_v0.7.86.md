# CER-AI Launch Behavior Contract — v0.7.86

Status: **Reconciled with the approved September 8, 2026 staging checkpoint**

Purpose: this document describes the approved canonical candidate based on staging commit `0d36e06981b48d1147eb2123c2b46a0df077f70a`, with the subsequent September 8 shared-PTA amendment. It does not claim this candidate is deployed to production. The 66-item evidence matrix records acceptance; later approved amendments in the protocol and test-retirement record supersede the original Phase 1 freeze. Clinical changes require explicit approval and direct changes to the owning implementation.

## 1. Canonical production flow

A clinical request must behave as the following ordered pipeline:

1. Authentication / access boundary.
2. Upload admission and security checks.
3. Image extraction for each uploaded source.
4. Mandatory source-set validation.
5. Canonical source validation, conflict detection, and provenance checks.
6. Patient/eye identity reconciliation.
7. Readiness and completion workflow for genuinely missing decision-critical inputs.
8. Independent per-eye clinical pathways:
   - Randleman / ERSS
   - Final BAD-D
   - CER-AI-adapted NICE
   - PS3
   - tissue and procedure safety
9. Canonical disposition aggregation.
10. Procedure planning only when disposition permits it.
11. Report generation.
12. Archive / audit persistence when enabled.

No refactor may reorder these stages in a way that changes clinical outputs, bypasses a source gate, or allows planning/report finalization before unresolved decision-critical data are handled.

## 2. Mandatory image-set contract

CER-AI accepts **5 mandatory Pentacam images** plus **1 optional excimer treatment card**, for a maximum of 6 images.

Mandatory:

- OD Four Maps Refractive
- OS Four Maps Refractive
- OD Belin/Ambrosio Display
- OS Belin/Ambrosio Display
- one bilateral Show 2 Exams Topometric image

Optional:

- Excimer laser treatment card

The primary image read identifies each uploaded page. The application must then show the status of all five mandatory sources and whether the optional treatment card is present. This confirmation occurs before targeted numeric rereading, geometric SRAX derivation, multi-image merging, clinical scoring, or report generation.

If a mandatory source is absent or cannot be identified, clinical assessment must not start. The doctor must be told which source is missing. A duplicate mandatory page cannot substitute for a different missing page. If the optional treatment card is absent, complete surgeon-entered manifest and intended refraction for OD and OS is required at this same pre-assessment gate. A surgeon-entered cylinder axis is required for each complete refraction, including an explicit zero cylinder; blank cylinder or axis values are never converted to zero.

Any value explicitly entered or confirmed by the surgeon is authoritative for that field. An image-derived or calculated value may fill only a blank field; it must not overwrite the surgeon value or create a conflict against it. This includes surgeon-entered age: printed or date-derived Pentacam age remains audit evidence only when the surgeon supplies age.

Real-world source-label variants such as `4 Maps Refractive` and accented `Ambrósio` must be recognized. The gate may also use source-locked numeric signatures to corroborate Show 2 Exams Topometric and BAD Display identity.

## 3. Source ownership and provenance

Decision-critical values must retain source provenance. Source locks include:

- K1, K1 axis, K2, K2 axis, and Kmean: **Show 2 Exams Topometric → Cornea Front** only.
- Signed I-S: explicitly labeled I-S/IS value; no map reconstruction.
- NICE posterior elevation: **B. Ele.Th labeled box on BAD Display** only.
- NICE central pachymetry: **Pupil Center (+)** only.
- Posterior Rmin: **Show 2 Exams Topometric → Cornea Back** only; the center 8-mm topometric RMin is a separate field.
- PS3 prescription comparison: `bad_flat_axis_deg` from the **BAD upper-middle Axis box beside K1** only.
- ML7 keratometry: reuse the existing canonical `K1_D` / `K2_D`; never create or request a second ML7-specific pair, and never substitute Kmax.
- Thinnest pachymetry: circle-marked Thinnest Location source.
- Final BAD-D and components: their own labeled boxes only.

Locked-field disagreement remains unresolved. Do not reconcile by tolerance, first value, minimum, maximum, or most-concerning value. Wrong-source values are rejected. `pentacam_canonical_source_lock.py` owns the registry.

## 4. ERSS / Randleman topography contract

Visual morphology is not an ERSS scoring authority and must not create score points or hard stops.

The two authoritative numeric topography channels are:

1. signed Topometric I-S;
2. independent geometric SRAX from the anterior Axial/Sagittal Curvature map.

The highest applicable **single** topography category wins. Categories are never added together.

### Signed I-S bands

- I-S < -0.50 D → Asymmetric bow tie → 1 point. There is no lower negative boundary.
- -0.50 through +0.50 D inclusive → Normal / symmetric → 0 points.
- > +0.50 through +1.00 D → Asymmetric bow tie → 1 point.
- > +1.00 and < +1.40 D → Inferior steepening / SRA category → 3 points.
- >= +1.40 D → Abnormal category → 4 points.

### Geometric SRAX

`geometric_srax_policy.measure_srax` is the single image-geometry implementation. Reverse-KISA calculation and model-estimated geometry are retired. SRAX >20.0° is positive; exactly 20.0° is negative. Uncertain geometry requests surgeon confirmation rather than inventing degrees.

ERSS uses this evidence within its single topography component only when signed I-S is from 0.00 through +1.00 D and does not already establish a higher category. A negative I-S represents superior rather than inferior asymmetry and cannot be relabeled as inferior steepening by SRAX; its signed I-S category is final and SRAX is not required for ERSS completion. PS3 retains a measured SRAX value as visible evidence, but when signed I-S is negative it records the SRAX factor as normal and cannot defer a procedure on that basis. A page with no SRAX observation must not erase a valid measured observation; a true conflict remains unresolved when SRAX is applicable.

## 5. Approved ERSS component policy

### Age — CER-AI modification

- 18 years → 3 points
- 19–20 years → 2 points
- >=21 years → 0 points

### Thinnest pachymetry — CER-AI modification

- <480 µm → hard stop; no clearance score
- 480–499 µm → 2 points
- 500–509 µm → 1 point
- >=510 µm → 0 points

### Overall ERSS disposition

- total 0–2 → no ERSS-specific escalation
- total 3 → CAUTION
- total >=4 → STOP-DEFER

ERSS remains independent of BAD-D, NICE, and PS3.

PRK uses the same canonical ERSS thresholds, with PRK residual stroma supplying the tissue component. Full PRK reports require complete ERSS; do not label it not applicable.

## 6. Final BAD-D contract

Final BAD-D is interpreted independently:

- <=1.60 → NORMAL
- >1.60 and <2.60 → SUSPICIOUS; contextual, not an automatic defer by itself
- >=2.60 → ABNORMAL → STOP-DEFER hard stop

Individual Df/Db/Dp/Dt/Da values do not replace Final BAD-D as the final BAD classification.

This hard stop applies regardless of whether the planned procedure is LASIK or PRK.

## 7. NICE contract

NICE is an independent CER-AI-adapted pathway using:

- K2
- central pachymetry from Pupil Center (+)
- B. Ele.Th from BAD Display
- signed I-S

Component score ranges are 1–3; total is 4–12.

Disposition:

- total 4 → no NICE-specific escalation
- total 5–8 → CAUTION
- total >=9 → STOP-DEFER
- missing required NICE input → DATA INSUFFICIENT until resolved

NICE never overrides a more restrictive independent pathway.

## 8. PS3 contract

PS3 remains mathematically and interpretively independent from ERSS, BAD-D, and NICE.

Disposition rule:

- no HIGH and no MODERATE findings → PRK/SMILE/LASIK allowed by PS3
- exactly 1 MODERATE finding → PRK/SMILE allowed by PS3; LASIK deferred by PS3
- >=2 MODERATE findings or >=1 HIGH finding → PRK/SMILE/LASIK deferred by PS3

PS3 uses the shared geometric SRAX: >20.0° → HIGH; exactly 20.0° is not HIGH. Missing SRAX remains incomplete, even when other findings already defer surgery.

Manifest/topographic astigmatism discrepancy activates only when either absolute manifest cylinder or topographic astigmatism is >3.00 D. When both are <=3.00 D this factor adds no risk; missing magnitudes are not assumed low. Active comparisons retain >1.00 D magnitude or >10° axis discrepancy thresholds. The axis source is the directly read BAD flat meridian, compared with normalized minus-cylinder manifest axis modulo 180°; no steep-axis substitution or extra transposition is permitted.

PS3 morphologic items that are not reliably machine-readable remain NOT_EVALUATED and are not silently counted as normal.

## 9. Tissue and procedural safety contract

Independent hard-stop / safety rules include at least:

- thinnest preoperative cornea <480 µm → STOP-DEFER
- LASIK RSB <300 µm → STOP-DEFER
- PRK RST <310 µm → STOP-DEFER
- intended myopic sphere beyond -10.00 D → STOP-DEFER
- intended hyperopic sphere beyond +6.00 D → STOP-DEFER
- estimated postoperative Kmean outside 36–48 D → STOP-DEFER
- LASIK PTA >=40.0% fails the evaluated candidate; evaluate A→B→C and retain the first candidate satisfying every applicable requirement
- PRK PTA >=40.0% → STOP-DEFER for both direct PRK and automatic LASIK→PRK; no separate 35.28% flag
- PRK epithelium convention = 50 µm

PRK selection must not retain an active LASIK flap plan.

## 10. PRK pathway contract

The provisional PRK-EWSS pathway is retired from decision authority.

It must not:

- generate a PRK score used for disposition;
- create CAUTION;
- create STOP-DEFER;
- cancel or override any independent hard stop;
- appear as a fifth ectasia-risk scoring system in the final clinical architecture.

PRK is governed by canonical ERSS, BAD-D, NICE, PS3, tissue/procedure safety, readiness, and clinical eligibility. Requested myopic ablation uses the shared estimator when no entered maximum ablation is supplied; entered ablation takes precedence. PRK residual stroma is thinnest pachymetry minus 50 µm epithelium minus maximum stromal ablation.

A definitive LASIK STOP-DEFER triggers one PRK evaluation for that eye through the same canonical core. Preserve the LASIK assessment and candidate history. Incomplete LASIK alone does not trigger PRK; shared stops and missing inputs remain effective. A successful fellow-eye LASIK result is retained.

## 11. Contact-lens readiness contract

The server-authoritative readiness gate currently uses:

- soft lenses: at least 10 full days off lenses
- rigid / RGP lenses: at least 21 full days off lenses

If the criterion is not met, assessment is blocked before clinical scoring and the doctor is instructed to repeat Pentacam after adequate washout.

The 10-day soft-lens readiness rule supersedes the legacy 14-day message retained in the old base implementation.

## 12. Canonical status contract

Clinical categories are exactly:

- PASS
- PASS WITH CAUTION
- CAUTION
- STOP-DEFER

Workflow/routing states are separate:

- POST-REFRACTIVE PATHWAY REQUIRED
- ASSESSMENT INCOMPLETE (`DATA_INSUFFICIENT` is a compatibility name for the same state)

Restrictiveness order:

Clinical ordering: `PASS < PASS WITH CAUTION < CAUTION < STOP-DEFER`. Incompleteness blocks favorable completion; prior refractive surgery routes out of the virgin-cornea engine rather than being treated as another clinical score.

For each eye, count CAUTION results from the completed ERSS, NICE, PS3 and Final BAD-D systems:
zero or one yields PASS; two yields PASS WITH CAUTION; three or four yields CAUTION. Count systems, not individual findings. Independent
CAUTION findings retain CAUTION. Incomplete inputs block favorable final status;
STOP-DEFER dominates incomplete and caution results. The bilateral result preserves
the more restrictive eye result; two PASS WITH CAUTION eyes do not become CAUTION.
Both caution categories use orange. Component scoring rules remain unchanged.

No module may downgrade an independent hard stop.

## 13. Planning contract

Planning is downstream of risk assessment. Favorable planning statuses are PASS, PASS WITH CAUTION and CAUTION. Planning must not be used to erase or reinterpret an upstream risk classification.

LASIK/PRK tissue calculations, postoperative K constraints, optical/transition-zone rules, flap selection, MMC guidance, and microkeratome planning remain separate from ectasia-risk scoring.

## 14. Reporting and archive contract

The final report must preserve independent pathway interpretability. ERSS, Final BAD-D, NICE, PS3, and tissue/procedural findings must remain distinguishable rather than being collapsed into one opaque composite score.

Report/export operations must use the server-authoritative completed assessment state. Client-supplied report payloads must not be trusted as replacement clinical evidence.

When archive is enabled, source images and generated case/report data remain part of the case record according to the archive policy.

## 15. Refactor acceptance rule

During Phase 2 and Phase 3, a proposed architectural change is acceptable only when:

1. the canonical startup invariants pass;
2. the complete existing regression suite passes;
3. the Phase 1 launch-contract golden tests pass;
4. no new decision-critical code path bypasses provenance or readiness gates;
5. any intentional clinical behavior change is separately documented and explicitly approved.

Implementation details such as wrapper identity are **not** part of this long-term contract. Observable clinical behavior, source ownership, disposition, and safety boundaries are.


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
