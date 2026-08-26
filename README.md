# HC Ectasia App

FastAPI application for source-restricted preoperative ectasia risk assessment using the **HC Preoperative Ectasia Risk Assessment for Corneal Refractive Surgery**.

## What v0.6 implements

- Sequential original-detail extraction of each uploaded Pentacam/topography or treatment-card image.
- Pentacam numeric-source priority: explicitly labeled side/summary-table fields are used first.
  When that field is unreadable, a directly corresponding marked local-map value may be used only
  for thinnest pachymetry or anterior/posterior elevation at the marked thinnest point. Local spots
  cannot substitute for K, BAD, progression, ARTmax, topometric, volume, or HOA/coma summary values;
  categorical visual inference is reserved for morphology, bow-tie/SRAX, and map patterns.
- Installable Android PWA with a Web Share Target: one or multiple images shared from Samsung Gallery can open the HC Ectasia App and populate its image intake.
- Excimer Laser Takip Kartı reading limited to the eye-specific `Düzeltme Miktarı` row; confident minus-cylinder values can fill otherwise empty sphere/cylinder/axis fields, while manual input wins and uncertain/conflicting readings remain warnings.
- Independent OD and OS assessment; eye values are never averaged, and a missing fellow-eye assessment prohibits overall PASS.
- Source identity review reads Pentacam patient names only from the labeled `First Name` and `Last Name` demographics fields and records the source filename. An unreadable or unverified name produces a prominent surgeon-confirmation warning without suppressing the eye analyses; acquisition-date conflicts and unclassified/unusable uploads remain clinical/source blockers.
- Pentacam clearance requires a same-exam explicit `QS: OK`; a visible non-OK QS cannot be masked by another page.
- Age is read from the explicitly printed Pentacam age; a conflicting manually entered age remains a blocker. Date of birth is not collected.
- Preoperative manifest refraction is separated from intended treatment correction. LASIK ERSS MRSE uses only the former; ablation and HC treatment-range gates use only the latter.
- Prior PRK/LASIK/SMILE short-circuits virgin-cornea scoring and routes to `POST-REFRACTIVE PATHWAY REQUIRED`.
- Published five-component LASIK ERSS scoring and categories.
- PRK-EWSS v1.0 provisional morphology/pachymetry/age triage score, explicitly labeled as unvalidated.
- Morphology-first override gate for definite KC/FFKC/PMD or unequivocal ectatic morphology.
- Published ERSS Placido thresholds are enforced for SRAX/inferior steepening: SRAX requires `≥20°`; the alternative category requires `≥1.0 D` inferior-versus-opposite steepening with `I-S <1.4 D`. Minimal axis deviation is not scored as SRAX, and unsupported visual labels remain unscorable rather than being guessed.
- HC operational hard stops: preoperative thinnest pachymetry `<480 µm`, LASIK RSB `<300 µm`, PRK RST `<310 µm`, intended sphere `<−10.00 D`, and intended sphere `>+6.00 D`. Exact boundaries do not trigger those rules.
- Standard HC PRK calculation: `RST = pachymetry - 50 µm epithelium - maximum stromal ablation`.
- Zone-specific HC ablation estimates for explicitly documented Alcon EX500 plans: `12 µm/D` at 6.0 mm, `15 µm/D` at 6.5 mm, and `16.33 µm/D` at 7.0 mm; the actual treatment-plan maximum remains preferred.
- Optical-zone selection is limited to `6.0`, `6.5`, or `7.0 mm`; transition-zone selection is limited to `8.0`, `8.5`, or `9.0 mm`.
- The visible laser-platform field is fixed and read-only as `Alcon EX500` for both eyes; the optical zone remains an explicit eye-specific input.
- Planned LASIK flap thickness is selected per eye from `90`, `100`, `110`, or `120 µm`; PRK plans leave the flap selection blank.
- Refraction stability, documented progression, unexplained CDVA loss, and anticipated enhancement remain separate eye-specific values inside one compact clinical-eligibility dropdown box.
- PRK epithelial thickness is shown per eye as a fixed, read-only `50 µm` HC value and is used in the PRK RST/PTA calculations.
- Procedure-correct PTA formulas for LASIK and PRK.
- BAD-D/component display interpretation plus adjunctive ARTmax/TP/Dt/Da evidence flags.
- Positive tomography concern flags require review and cannot receive automatic PASS.
- Limited/inadequate decision-source image quality, implausible numeric values, failed PPI/ARTmax consistency checks, and unresolved cross-image value conflicts prohibit PASS.
- PRK PTA above the supplied 35.28% direct-cohort envelope requires review and cannot receive automatic PASS.
- Expanded extraction/reporting of anterior and posterior elevation, pachymetric progression,
  topometric, thinnest-point location, corneal-volume, and HOA/coma fields when visibly available.
- Required clinical modifiers and treatment-plan inputs; missing/unreadable critical data prohibit PASS.
- One multi-select clinical-eligibility control records eye rubbing/ocular trauma, family history, inter-eye asymmetry, pregnancy/nursing, collagen/connective-tissue disease, medication, dry eye, and systemic disease. These create separate defer/review dispositions without invented ectasia-score points.
- Contact-lens type and washout are documented. The supplied source-study acquisition criterion (soft ≥14 days; rigid ≥21 days) is an imaging-data gate, not an ectasia score or universal safety cutoff.
- Binding CAUTION action: STOP/DEFER, repeat relevant screening, and reassess after at least 6 months.
- Formal clinical report with patient/reviewer metadata, restrained decision colors (PASS green,
  CAUTION amber, FAIL red, NOT ASSESSED gray), print layout, and validated PDF and DOCX exports.
- Complete machine-readable extraction and decision records remain available for audit.

See [HC_PROTOCOL_v0.6.md](HC_PROTOCOL_v0.6.md) for the locked operational rules and
[PROTOCOL_COMPLIANCE.md](PROTOCOL_COMPLIANCE.md) for the source-to-code audit and evidence limitations.

## Run

```bash
pip install -r requirements.txt
python start.py
```

Railway start command: `python start.py`.

## Test

```bash
python -m unittest discover -s tests -v
```

The 92-test suite covers the exact structural and treatment-range boundaries, signed manifest/intended input, prior-surgery routing, identity warnings, date/QS gates, invalid numeric inputs, fellow-eye completeness, ERSS/PRK-EWSS categories, extraction merging, and valid PDF/DOCX generation.

Dependencies are exact-version pinned. The extraction model is restricted to the reviewed configuration; changing it requires explicit non-clinical override and revalidation.


## Authorized update and deployment workflow

For this project, do not use the cloud-browser GitHub username/password form and do not rely on a
local HTTPS `git push` credential. Use the connected GitHub application:

1. Read the current target file from `ginger33hc-glitch/hc-ectasia-app` on `main` and retain its
   current blob SHA.
2. Make and validate the change in the local project copy.
3. Replace the target file on `main` through the connected GitHub application's file-update
   capability, supplying the retained SHA and a descriptive commit message.
4. Verify the returned commit SHA, then allow the linked Railway service to deploy automatically.
5. Reload `https://hc-ectasia-app-production.up.railway.app/` and verify the live application.

Never place GitHub passwords, tokens, API keys, or other credentials in this repository.
