# HC Ectasia App

FastAPI application for source-restricted preoperative ectasia risk assessment using the **HC Preoperative Ectasia Risk Assessment for Corneal Refractive Surgery**.

## What v0.5 implements

- Sequential original-detail extraction of each uploaded Pentacam/topography or treatment-card image.
- Excimer Laser Takip Kartı reading limited to the eye-specific `Düzeltme Miktarı` row; confident minus-cylinder values can fill otherwise empty sphere/cylinder/axis fields, while manual input wins and uncertain/conflicting readings remain warnings.
- Independent OD and OS assessment; eye values are never averaged.
- Published five-component LASIK ERSS scoring and categories.
- PRK-EWSS v1.0 provisional morphology/pachymetry/age triage score, explicitly labeled as unvalidated.
- Morphology-first override gate for definite KC/FFKC/PMD or unequivocal ectatic morphology.
- HC operational hard stops: preoperative thinnest pachymetry `<480 µm`, LASIK RSB `<300 µm`, and PRK RST `<310 µm`.
- Standard HC PRK calculation: `RST = pachymetry - 50 µm epithelium - maximum stromal ablation`.
- Zone-specific HC ablation estimates for explicitly documented Alcon EX500 plans: `12 µm/D` at 6.0 mm and `15 µm/D` at 6.5 mm; the actual treatment-plan maximum remains preferred.
- Optical-zone selection is limited to `6.0`, `6.5`, or `7.0 mm`; transition-zone selection is limited to `8.0`, `8.5`, or `9.0 mm`. No HC linear ablation coefficient is assigned to 7.0 mm, so an actual maximum ablation depth is required for that option.
- The visible laser-platform field is fixed and read-only as `Alcon EX500` for both eyes; the optical zone remains an explicit eye-specific input.
- Planned LASIK flap thickness is selected per eye from `90`, `100`, `110`, or `120 µm`; PRK plans leave the flap selection blank.
- PRK epithelial thickness is shown per eye as a fixed, read-only `50 µm` HC value and is used in the PRK RST/PTA calculations.
- Procedure-correct PTA formulas for LASIK and PRK.
- BAD-D/component display interpretation plus adjunctive ARTmax/TP/Dt/Da evidence flags.
- Positive tomography concern flags require review and cannot receive automatic PASS.
- Limited/inadequate image quality and unresolved cross-image value conflicts prohibit PASS.
- PRK PTA above the supplied 35.28% direct-cohort envelope requires review and cannot receive automatic PASS.
- Expanded extraction/reporting of anterior and posterior elevation, pachymetric progression,
  topometric, thinnest-point location, corneal-volume, and HOA/coma fields when visibly available.
- Required clinical modifiers and treatment-plan inputs; missing/unreadable critical data prohibit PASS.
- One multi-select patient-modifier control records eye rubbing/ocular trauma, keratoconus family history, inter-eye asymmetry, pregnancy/nursing, collagen/connective-tissue disease, and relevant medication/drug usage; no new score weights are inferred for the added items.
- Binding CAUTION action: STOP/DEFER, repeat relevant screening, and reassess after at least 6 months.
- Formal clinical report with patient/reviewer metadata, restrained decision colors (PASS green,
  CAUTION amber, FAIL red, NOT ASSESSED gray), print layout, and validated PDF and DOCX exports.
- Complete machine-readable extraction and decision records remain available for audit.

See [PROTOCOL_COMPLIANCE.md](PROTOCOL_COMPLIANCE.md) for the source-to-code audit and evidence limitations.

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

The tests cover the exact 480/310/300 µm boundaries, ERSS/PRK-EWSS categories, missing-data prohibition, per-eye isolation, BAD display boundaries, extraction merging, and valid PDF/DOCX report generation.
