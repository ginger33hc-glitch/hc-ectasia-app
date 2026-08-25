# HC Ectasia App

FastAPI application for source-restricted preoperative ectasia risk assessment using the **HC Preoperative Ectasia Risk Assessment for Corneal Refractive Surgery**.

## What v0.4 implements

- Sequential original-detail extraction of each uploaded Pentacam/topography image.
- Independent OD and OS assessment; eye values are never averaged.
- Published five-component LASIK ERSS scoring and categories.
- PRK-EWSS v1.0 provisional morphology/pachymetry/age triage score, explicitly labeled as unvalidated.
- Morphology-first override gate for definite KC/FFKC/PMD or unequivocal ectatic morphology.
- HC operational hard stops: preoperative thinnest pachymetry `<480 µm`, LASIK RSB `<300 µm`, and PRK RST `<310 µm`.
- Standard HC PRK calculation: `RST = pachymetry - 50 µm epithelium - maximum stromal ablation`.
- Procedure-correct PTA formulas for LASIK and PRK.
- BAD-D/component display interpretation plus adjunctive ARTmax/TP/Dt/Da evidence flags.
- Required clinical modifiers and treatment-plan inputs; missing/unreadable critical data prohibit PASS.
- Binding CAUTION action: STOP/DEFER, repeat relevant screening, and reassess after at least 6 months.
- Human-readable color-coded report plus a complete machine-readable record.

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

The tests cover the exact 480/310/300 µm boundaries, ERSS/PRK-EWSS categories, missing-data prohibition, per-eye isolation, BAD display boundaries, and extraction merging.
