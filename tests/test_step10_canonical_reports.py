"""Stage 10 acceptance: one canonical payload, two presentation-only renderers."""
from copy import deepcopy
from io import BytesIO
import inspect

from docx import Document
import pytest

from canonical_runtime_service import evaluate_case
import reports


def _eye(name, **overrides):
    values = {
        "eye": name, "K1_D": 42.0, "K1_axis_deg": 180.0,
        "K2_D": 44.0, "K2_axis_deg": 90.0, "Kmean_D": 43.0,
        "central_pachy_um": 550.0, "pachy_thinnest_um": 545.0,
        "Kmax_D": 45.0, "corneal_diameter_mm": 11.8,
        "Rmin_mm": 5.9, "topometric_RMin": 6.8,
        "BAD_D": 1.0, "Df": -0.2, "Db": 0.4, "Dp": 0.3, "Dt": 0.2, "Da": 0.5,
        "ARTmax_um": 380.0, "PPI_min": 0.7, "PPI_avg": 1.0, "PPI_max": 1.2,
        "I_S": 0.0, "ISV": 20, "IVA": 0.12, "KI": 1.02, "CKI": 1.0,
        "IHA": 2.0, "IHD": 0.01, "TKC": "-", "KISA": 5.0,
        "topographic_astig_D": 1.0, "bad_flat_axis_deg": 90.0, "topographic_steep_axis_deg": 90.0,
        "posterior_Kmean_D": -6.0 if name == "OD" else -6.05,
        "F_Ele_Th_um": 5.0, "B_Ele_Th_um": 10.0,
        "srax": "NO", "srax_deg": 10.0,
        "table_verified_numeric_fields": ["corneal_diameter_mm"],
        "field_provenance": {
            "BAD_D": [{"source": "BAD_D_STRIP", "file": f"{name}-bad.png"}],
            "Rmin_mm": [{"source": "SHOW_2_CORNEA_BACK", "file": "show2.png"}],
            "topometric_RMin": [{"source": "SHOW_2_INDICES", "file": "show2.png"}],
        },
    }
    values.update(overrides)
    return values


def _plan():
    return {
        "prior": "no", "procedure": "LASIK", "flap_um": 100.0, "ablation_um": 50.0,
        "manifest_entered_sphere_D": -2.0, "manifest_cylinder_signed_D": -1.0,
        "manifest_axis_deg": 90.0, "intended_entered_sphere_D": -2.0,
        "intended_cylinder_signed_D": -1.0, "intended_axis_deg": 90.0,
        "stable": "yes", "progression": "no", "cdva_below_20_20": "no",
    }


def _payload(**od_overrides):
    decision = evaluate_case(
        {"eyes": [_eye("OD", **od_overrides), _eye("OS")]}, 35,
        {"OD": _plan(), "OS": _plan()},
        {"eye_rubbing": "no", "family_history": "no",
         "pregnancy_nursing": "no", "collagen_tissue_disease": "no", "drug_usage": "no",
         "dry_eye": "no", "systemic_disease": "no"},
        software_version="stage10-test",
    )
    return {
        "locale": "en",
        "patient": {"name": "Canonical Patient", "id": "P-10", "age": 35,
                    "report_date": "2026-09-07", "reviewer": "Dr. Test"},
        "decision": decision,
    }


def _section(model, eye, title):
    selected = next(item for item in model["eyes"] if item["eye"] == eye)
    return next(rows for heading, rows in selected["sections"] if heading == title)


def test_model_contains_every_canonical_clinical_report_section_without_recalculation():
    payload = _payload()
    model = reports.canonical_report_model(payload)
    assert [eye["eye"] for eye in model["eyes"]] == ["OD", "OS"]
    headings = [heading for heading, _ in model["eyes"][0]["sections"]]
    assert headings == [
        "Randleman / ERSS", "NICE", "PS3", "Belin/Ambrósio BAD-D",
        "Procedural safety", "Procedure planning", "Decision basis",
        "Canonical Pentacam values and provenance", "Version provenance",
    ]
    assert ["Total", "0"] in _section(model, "OD", "Randleman / ERSS")
    assert any(row[0] == "Final BAD-D" and row[1] == "1" for row in _section(model, "OD", "Belin/Ambrósio BAD-D"))
    assert any(row[0] == "selected_plan" and row[1] == "Plan A" for row in _section(model, "OD", "Procedure planning"))


def test_locked_source_values_and_provenance_remain_distinct_in_report():
    rows = _section(reports.canonical_report_model(_payload()), "OD", "Canonical Pentacam values and provenance")
    posterior = next(row for row in rows if row[0] == "Posterior Rmin")
    topometric = next(row for row in rows if row[0] == "Topometric RMin")
    assert posterior == ["Posterior Rmin", "5.9", "SHOW_2_CORNEA_BACK / show2.png"]
    assert topometric == ["Topometric RMin", "6.8", "SHOW_2_INDICES / show2.png"]
    assert next(row for row in rows if row[0] == "Final BAD-D")[2] == "BAD_D_STRIP / OD-bad.png"


def test_pachymetric_reference_colors_preserve_bad_and_ps3_authority():
    payload = _payload(PPI_min=0.80, PPI_avg=1.18, PPI_max=1.53, ARTmax_um=356)
    model = reports.canonical_report_model(payload)
    rows = _section(model, "OD", "Belin/Ambrósio BAD-D")
    by_name = {row[0]: row for row in rows}
    assert by_name["PPI Min"][2].startswith("SUSPICIOUS / 0.80-0.86")
    assert by_name["PPI Avg"][2].startswith("ABNORMAL / > 1.17")
    assert reports._cell_palette(by_name["PPI Min"], 1)[0] == reports.AMBER
    for name in ("PPI Avg", "PPI Max", "ARTmax"):
        assert reports._cell_palette(by_name[name], 1)[0] == reports.RED
    assert by_name["Final BAD-D"][2] == "NORMAL / PASS"
    ps3 = _section(model, "OD", "PS3")
    assert next(row for row in ps3 if row[0] == "ppi_average")[1] == "NORMAL"
    assert "Ghiasian" not in str(model)


def test_ps3_report_uses_canonical_findings_and_exposes_exact_trigger():
    rows = _section(reports.canonical_report_model(_payload(PPI_avg=1.3)), "OD", "PS3")
    ppi = next(row for row in rows if row[0] == "ppi_average")
    assert ppi[1] == "MODERATE"
    assert "PPI Average 1.3 > 1.20" in ppi[2]
    assert any(row[0] == "Procedure disposition" and row[1] == "PASS" for row in rows)
    assert any(row[0] == "Procedure disposition" and "lasik: DEFER" in row[2] for row in rows)


def test_pdf_and_docx_use_same_model_and_do_not_mutate_canonical_snapshot():
    payload = _payload()
    before = deepcopy(payload)
    pdf = reports.build_pdf(payload)
    docx = reports.build_docx(payload)
    assert pdf.startswith(b"%PDF")
    document = Document(BytesIO(docx))
    text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "OD — PASS" in text
    assert "Randleman / ERSS" in text
    assert payload == before


def test_full_report_rejects_incomplete_ps3_even_when_an_immediate_stop_exists():
    payload = _payload(I_S=1.40, srax="UNCERTAIN", srax_deg=None)
    assert payload["decision"]["eyes"][0]["status"] == "STOP-DEFER"
    with pytest.raises(reports.ReportContractError, match="PS3 is incomplete"):
        reports.canonical_report_model(payload)


def test_full_report_rejects_unavailable_final_bad_d():
    payload = _payload(BAD_D=None)
    with pytest.raises(reports.ReportContractError, match="Final BAD-D is incomplete"):
        reports.canonical_report_model(payload)


def test_report_module_has_no_scorer_import_threshold_or_runtime_patch():
    source = inspect.getsource(reports)
    assert "clinical_core.erss" not in source
    assert "clinical_core.nice" not in source
    assert "clinical_core.bad" not in source
    assert "ps3_policy" not in source
    assert "SimpleDocTemplate.build =" not in source
    assert "reports._" not in source
