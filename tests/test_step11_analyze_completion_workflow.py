"""Stage 11 acceptance for Analyze and surgeon-completion workflow."""
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

import assessment_workflow as workflow


ROOT = Path(__file__).resolve().parents[1]


def test_patient_name_resolution_preserves_source_and_manual_entry():
    extracted = {"document_contexts": [
        {"document_type": "PENTACAM_TOPOGRAPHY", "patient_first_name": "AYŞE",
         "patient_last_name": "KOŞTUR"},
        {"document_type": "PENTACAM_TOPOGRAPHY", "patient_first_name": "AYŞE",
         "patient_last_name": "KOŞTUR"},
    ]}
    patient, request = workflow._resolve_patient_metadata({"name": None}, extracted, 37)
    assert patient["name"] == "AYŞE KOŞTUR" and patient["age"] == 37
    assert request is None
    extracted["document_contexts"][1]["patient_last_name"] = "OTHER"
    patient, request = workflow._resolve_patient_metadata({}, extracted, 37)
    assert not patient.get("name")
    assert request["kind"] == "form" and request["form_id"] == "patient_name"
    patient, request = workflow._resolve_patient_metadata({"name": "Confirmed name"}, extracted, 37)
    assert patient["name"] == "Confirmed name" and request is None


def test_extracted_name_reaches_ready_report_metadata():
    session = {"extracted": {"eyes": [_eye("OD"), _eye("OS")],
               "document_contexts": [{"document_type": "PENTACAM_TOPOGRAPHY",
               "patient_first_name": "AYŞE", "patient_last_name": "KOŞTUR"}]},
               "ready": None, "source_images": []}
    response = workflow._respond(SimpleNamespace(APP_VERSION="test"), "token", session,
                                 37, {"OD": _plan(), "OS": _plan()}, _modifiers(), {}, {})
    assert response["workflow_status"] == "READY"
    assert session["ready"]["patient"]["name"] == "AYŞE KOŞTUR"
    assert response["patient_metadata"]["name"] == "AYŞE KOŞTUR"


def _eye(name="OD", **overrides):
    values = {
        "eye": name, "Kmean_D": 43.0, "K2_D": 44.0,
        "central_pachy_um": 550.0, "pachy_thinnest_um": 545.0,
        "BAD_D": 1.0, "Df": -0.2, "Db": 0.4, "Dp": 0.3, "Dt": 0.2, "Da": 0.5,
        "ARTmax_um": 380.0, "PPI_min": 0.7, "PPI_avg": 1.0, "PPI_max": 1.2,
        "I_S": 0.0, "topographic_astig_D": 1.0, "bad_flat_axis_deg": 90.0, "topographic_steep_axis_deg": 90.0,
        "posterior_Kmean_D": -6.0 if name == "OD" else -6.05,
        "F_Ele_Th_um": 5.0, "B_Ele_Th_um": 10.0, "srax": "NO", "srax_deg": 10.0,
        "data_conflicts": [], "missing_or_unreadable": [], "field_provenance": {},
    }
    values.update(overrides)
    return values


def _plan(**overrides):
    values = {
        "prior": "no", "procedure": "LASIK", "flap_um": 100.0, "ablation_um": 50.0,
        "manifest_entered_sphere_D": -2.0, "manifest_cylinder_signed_D": -1.0,
        "manifest_axis_deg": 90.0, "intended_entered_sphere_D": -2.0,
        "intended_cylinder_signed_D": -1.0, "intended_axis_deg": 90.0,
        "stable": "yes", "progression": "no", "cdva_below_20_20": "no",
    }
    values.update(overrides)
    return values


def _modifiers(**overrides):
    values = {
        "contact_lens_type": "NONE", "eye_rubbing": "no", "family_history": "no",
        "inter_eye_asymmetry": "no", "pregnancy_nursing": "no",
        "collagen_tissue_disease": "no", "drug_usage": "no", "dry_eye": "no",
        "systemic_disease": "no",
    }
    values.update(overrides)
    return values


def _respond(*, od=None, plans=None, modifiers=None):
    session = {
        "extracted": {"eyes": [od or _eye("OD"), _eye("OS")], "critical_input_issues": []},
        "ready": None, "expires": 0, "source_images": [],
    }
    return workflow._respond(
        SimpleNamespace(APP_VERSION="stage11-test"), "token", session, 35,
        plans or {"OD": _plan(), "OS": _plan()}, modifiers or _modifiers(),
        {"name": "Stage 11 Patient"}, {},
    )


def test_missing_signed_i_s_request_names_all_systems_and_exact_registry_source():
    response = _respond(od=_eye("OD", I_S=None))
    request = next(item for item in response["input_requests"] if item.get("eye") == "OD" and item.get("key") == "I_S")
    assert request["required_for"] == ["Randleman", "NICE"]
    assert request["source_screen"] == "Show 2 Exams – Topometric"
    assert request["source_box"] == "center — Indices (in 8 mm zone) → I-S"
    assert response["report_token"] is None


def test_contact_lens_washout_returns_completable_requirement_not_generic_error():
    response = _respond(modifiers=_modifiers(contact_lens_type="SOFT", contact_lens_discontinuation_days=9))
    assert response["workflow_status"] == "CONTACT_LENS_WASHOUT_REQUIRED"
    assert response["report_token"] is None
    request = next(item for item in response["input_requests"] if item.get("form_id") == "contact_lens_days")
    assert request["kind"] == "form"
    assert "10" in response["message"]


def test_ps3_factor_is_expanded_to_each_exact_missing_canonical_field():
    response = _respond(od=_eye("OD", F_Ele_Th_um=None, B_Ele_Th_um=None))
    requests = {
        item["key"]: item for item in response["input_requests"]
        if item.get("eye") == "OD" and "PS3" in item.get("required_for", [])
    }
    assert requests["F_Ele_Th_um"]["source_box"] == "central numeric box → F.Ele.Th"
    assert requests["B_Ele_Th_um"]["source_box"] == "central numeric box → B.Ele.Th"


def test_ps3_intereye_requirement_identifies_the_actual_eye_and_field():
    response = _respond(od=_eye("OD", posterior_Kmean_D=None))
    request = next(item for item in response["input_requests"] if item.get("key") == "posterior_Kmean_D")
    assert request["eye"] == "OD"
    assert request["required_for"] == ["PS3"]
    assert request["source_screen"] == "Show 2 Exams – Topometric"
    assert request["source_box"] == "Cornea Back → Km"


def test_ps3_astigmatic_study_requests_missing_map_and_manifest_inputs_separately():
    response = _respond(
        od=_eye("OD", topographic_astig_D=None, bad_flat_axis_deg=None),
        plans={"OD": _plan(manifest_cylinder_signed_D=None, manifest_axis_deg=None), "OS": _plan()},
    )
    od = {item["key"]: item for item in response["input_requests"] if item.get("eye") == "OD"}
    assert {"topographic_astig_D", "bad_flat_axis_deg", "manifest_cylinder_signed_D", "manifest_axis_deg"} <= set(od)
    assert od["topographic_astig_D"]["source_box"] == "Cornea Front → Astig"
    assert od["manifest_cylinder_signed_D"]["form_id"] == "od_manifest_cylinder"


def test_prior_surgery_cannot_receive_virgin_cornea_report_token():
    response = _respond(plans={"OD": _plan(prior="prk", procedure=""), "OS": _plan()})
    assert response["workflow_status"] == "NEEDS_INPUT"
    assert response["report_token"] is None
    request = next(item for item in response["input_requests"] if item.get("eye") == "OD")
    assert request["key"] == "prior_surgery_pathway"
    assert request["destination"] == "separate_pathway"
    assert "virgin-cornea" in request["label"]


def test_frontend_supports_all_nonready_states_and_never_leaves_analyze_stuck_disabled():
    html = (ROOT / "static" / "index.html").read_text()
    readiness = (ROOT / "static" / "assessment-readiness.js").read_text()
    assert "this.panel.hidden=response.workflow_status==='READY'" in readiness
    assert "CONTACT_LENS_WASHOUT_REQUIRED" in html
    assert "const sourceBlocked=" not in html
    assert "assessBtn.disabled=false" in html
    assert "hard_stop_summary" in html


def test_prior_surgery_ui_submits_specific_procedure_not_ambiguous_yes():
    html = (ROOT / "static" / "index.html").read_text()
    assert '<option value="prk">Yes — PRK</option>' in html
    assert '<option value="lasik">Yes — LASIK</option>' in html
    assert '<option value="smile">Yes — SMILE</option>' in html
    prior_row = next(line for line in html.splitlines() if 'id="${eye}_prior"' in line)
    assert '<option value="yes">Yes</option>' not in prior_row


def test_browser_result_view_consumes_canonical_report_payload_only():
    html = (ROOT / "static" / "index.html").read_text()
    render_source = html[html.index("function renderEye("):html.index("function patientPayload(")]
    assert "r.report_payload" in render_source
    for section in (
        "Randleman / ERSS", "NICE", "PS3", "Belin/Ambrósio BAD-D",
        "Procedural safety", "Procedure planning", "Decision basis",
        "Canonical Pentacam values and provenance", "Surgeon-completed values",
    ):
        assert section in render_source
    assert "r.randleman_erss" not in render_source
    assert "topography_classification" not in render_source
    assert "inferior_opposite_steepening_D" not in render_source
    assert "posterior_elevation_thinnest_um" not in render_source
    assert "extracted.eyes" not in render_source


def test_readiness_javascript_renders_contact_lens_status_as_visible():
    if not shutil.which("node"):
        pytest.skip("Node is not available")
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element{
  constructor(tag='div'){this.tagName=tag.toUpperCase();this.hidden=false;this.children=[];this.classList={add(){}};}
  append(...items){this.children.push(...items)} replaceChildren(){this.children=[]}
  addEventListener(){} scrollIntoView(){} set textContent(value){this._text=value} get textContent(){return this._text||''}
}
const panel=new Element();panel.querySelectorAll=()=>[];
const document={getElementById:id=>id==='imageInput'?null:null,createElement:tag=>new Element(tag)};
const context={window:{},document,URL:{revokeObjectURL(){}},console};vm.createContext(context);
vm.runInContext(fs.readFileSync('static/assessment-readiness.js','utf8'),context);
const readiness=new context.window.HCReadiness(panel);
const shown=readiness.show({assessment_token:'t',workflow_status:'CONTACT_LENS_WASHOUT_REQUIRED',input_requests:[]});
assert.equal(shown,true);assert.equal(panel.hidden,false);assert.equal(readiness.token,'t');
'''
    subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
