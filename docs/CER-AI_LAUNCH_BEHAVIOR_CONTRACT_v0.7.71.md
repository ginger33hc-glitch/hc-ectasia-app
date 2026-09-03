# CER-AI Launch Behavior Contract — v0.7.71

Status: **Phase 1 behavior freeze**

Purpose: this document defines the observable production behavior that must remain unchanged during the pre-launch architectural refactor unless a clinical policy change is explicitly approved. It is a behavior contract, not a description of the current wrapper implementation.

## 1. Canonical production flow

A clinical request must behave as the following ordered pipeline:

1. Authentication / access boundary.
2. Upload admission and security checks.
3. Image extraction for each uploaded source.
4. Mandatory source-set validation.
5. Source-aware reconciliation and provenance checks.
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

If a mandatory source is absent or cannot be identified, clinical assessment must not start. The doctor must be told which source is missing. A duplicate mandatory page cannot substitute for a different missing page.

Real-world source-label variants such as `4 Maps Refractive` and accented `Ambrósio` must be recognized. The gate may also use source-locked numeric signatures to corroborate Show 2 Exams Topometric and BAD Display identity.

## 3. Source ownership and provenance

Decision-critical values must retain source provenance. Source locks include:

- K1, K1 axis, K2, K2 axis, and Kmean: **Show 2 Exams Topometric → Cornea Front** only.
- Signed I-S: explicitly labeled I-S/IS value; no map reconstruction.
- NICE posterior elevation: **B. Ele.Th labeled box on BAD Display** only.
- NICE central pachymetry: **Pupil Center (+)** only.
- Rmin: designated Cornea Front source policy only.
- Thinnest pachymetry: circle-marked Thinnest Location source.
- Final BAD-D and components: their own labeled boxes only.

Unresolved conflicts in decision-critical values must not be silently averaged or guessed.

## 4. ERSS / Randleman topography contract

Visual morphology is not an ERSS scoring authority and must not create score points or hard stops.

The two authoritative numeric topography channels are:

1. signed Topometric I-S;
2. CER-AI derived SRAX.

The highest applicable **single** topography category wins. Categories are never added together.

### Signed I-S bands

- I-S < -0.50 D → Asymmetric bow tie → 1 point. There is no lower negative boundary.
- -0.50 through +0.50 D inclusive → Normal / symmetric → 0 points.
- > +0.50 through +1.00 D → Asymmetric bow tie → 1 point.
- > +1.00 and < +1.40 D → Inferior steepening / SRA category → 3 points.
- >= +1.40 D → Abnormal category → 4 points.

### Derived SRAX

CER-AI operational derivation:

`SRAX = (KISA% × 3) / (max(1, Kmax-47.2) × max(1, |I-S|) × max(1, |topographic astigmatism|))`

For ERSS, the original Randleman threshold is retained:

- derived SRAX >=20° → Inferior steepening / SRA category → 3 points.

Derived SRAX is not represented as directly reported by Pentacam.

## 5. ERSS component policy currently frozen

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

PS3 derived SRAX retains its own PS3 threshold:

- >22° → HIGH
- <=22° → not HIGH from that item

The ERSS >=20° threshold and PS3 >22° threshold are deliberately separate rules.

PS3 morphologic items that are not reliably machine-readable remain NOT_EVALUATED and are not silently counted as normal.

## 9. Tissue and procedural safety contract

Independent hard-stop / safety rules include at least:

- thinnest preoperative cornea <480 µm → STOP-DEFER
- LASIK RSB <300 µm → STOP-DEFER
- PRK RST <310 µm → STOP-DEFER
- intended myopic sphere beyond -10.00 D → STOP-DEFER
- intended hyperopic sphere beyond +6.00 D → STOP-DEFER
- estimated postoperative Kmean outside 36–48 D → STOP-DEFER
- LASIK PTA policy remains independently enforced
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

PRK remains governed by BAD-D, NICE, PS3, tissue/procedure safety, readiness, and other explicitly retained clinical rules.

## 11. Contact-lens readiness contract

The server-authoritative readiness gate currently uses:

- soft lenses: at least 10 full days off lenses
- rigid / RGP lenses: at least 21 full days off lenses

If the criterion is not met, assessment is blocked before clinical scoring and the doctor is instructed to repeat Pentacam after adequate washout.

The 10-day soft-lens readiness rule supersedes the legacy 14-day message retained in the old base implementation.

## 12. Canonical status contract

Clinical categories are exactly:

- PASS
- CAUTION
- STOP-DEFER

Workflow/routing states are separate:

- POST-REFRACTIVE PATHWAY REQUIRED
- DATA INSUFFICIENT

Restrictiveness order:

`PASS < CAUTION < POST-REFRACTIVE PATHWAY REQUIRED < DATA INSUFFICIENT < STOP-DEFER`

No module may downgrade an independent hard stop.

## 13. Planning contract

Planning is downstream of risk assessment. Favorable planning statuses are PASS and CAUTION only. Planning must not be used to erase or reinterpret an upstream risk classification.

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
