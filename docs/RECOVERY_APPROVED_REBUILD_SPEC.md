# CER-AI Owner-Approved Recovery Specification

Baseline: `b582fc83f04fa01200aa9f6aaf073b1672e916c1` (pre-PR #43).

This file is the recovery contract for `recovery/approved-rebuild`. Do not import PRs #43-57 wholesale. Reapply only the owner-approved behavior below.

## Randleman / ERSS topography

General visual morphology classification remains retired as an independent scoring pathway.

The signed, source-locked Pentacam I-S value is the primary numeric classifier:

- `-0.50 <= I-S <= +0.50 D`: NORMAL_SYMMETRIC, 0 points.
- `I-S < -0.50 D`: ASYMMETRIC_BOWTIE, 1 point, with no lower negative limit.
- `+0.50 < I-S <= +1.00 D`: ASYMMETRIC_BOWTIE, 1 point.
- `+1.00 < I-S < +1.40 D`: INFERIOR_STEEPENING_SRA, 3 points.
- `I-S >= +1.40 D`: ABNORMAL_ECTATIC / keratoconus-suspect, 4 points.

SRAX is a separate evidence channel:

- SRAX may be determined only from direct geometry on the Pentacam Axial/Sagittal Curvature (Front) map.
- SRAX positive criterion is strictly `>20 degrees`; exactly 20 degrees is not positive.
- A positive SRAX supplies the INFERIOR_STEEPENING_SRA 3-point topography category.
- If SRAX cannot be determined reliably, it remains UNRESOLVED / NOT_EVALUATED and requires explicit surgeon confirmation from the same Front map.
- Missing or unresolved SRAX must never default to `0 degrees`, NORMAL, NO, or any other negative state.
- KISA, Kmax, I-S, astigmatism, BAD-D, or any other surrogate must never be used to reconstruct or reverse-calculate SRAX.
- I-S and SRAX categories are not additive. Use only the highest applicable single Randleman topography category.

## PS3

Keep PS3 as an independent risk engine and report channel. It must not add points to or rewrite Randleman/ERSS, BAD-D, or NICE.

One authoritative, source-locked SRAX observation is shared by Randleman and PS3. If SRAX is unresolved, it remains unresolved for both systems until surgeon confirmation. PS3 must not independently derive SRAX.

Keep the required PS3 Pentacam fields with strict source locks to the owner-defined labeled boxes/tables, including topographic astigmatism, topographic steep axis, posterior mean K, F.Ele.Th, B.Ele.Th, PPI/Progression Index Avg, and ARTmax where required by the PS3 rule set. These fields are independent of SRAX.

Keep PS3 report interpretation: classification, exact triggering criteria, procedure disposition, criteria audit, and surgeon-review-required items.

## Randleman report readiness

For virgin LASIK, all five Randleman/ERSS components and the total must be complete before final report readiness.

Unresolved components must produce explicit surgeon completion/confirmation requests. They must not silently appear as undocumented while a final report is issued.

PDF/DOCX export must fail closed if a virgin LASIK assessment reaches export without complete required Randleman/ERSS scoring.

Unresolved topography/SRAX must remain represented in `missing_erss_inputs`; cleanup code must never remove it merely to make the case report-ready.

## Other approved retained changes from PRs #43-57

- Prior PRK/LASIK/SMILE bypasses the virgin-cornea engine.
- Contact-lens washout gate: soft lenses >=10 full days; rigid/RGP >=21 full days; insufficient or missing required washout data blocks assessment.
- Pentacam exam dates are reconciled semantically as calendar dates; genuine/unresolved discrepancies remain blocking.
- Show 2 Exams Topometric header date is excluded from exam-date reconciliation.
- Rmin source lock: Four Maps Refractive -> Cornea Front -> printed Rmin row only; no Cornea Back or calculated/map fallback.
- ML7 reporting follows final LASIK eligibility; stale intermediate ML7 PASS becomes NOT APPLICABLE when LASIK is ultimately ineligible.
- Keep public CER-AI website and routing: `/` public homepage, `/home` public alias, `/app` authenticated clinical application, `/archive-ui` authenticated.
- Keep public-site design, evaluation framework, User Guide, and authentication routing correction from PRs #49-54.

## Explicitly prohibited recovery behavior

- No inverse-KISA or other derived SRAX.
- No general morphology result competing with the signed I-S classifier.
- No default SRAX zero.
- No downstream report layer independently recalculating clinical scores or disposition.
- Do not merge or deploy the recovery branch until regression and real-case validation are complete.
