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
         "patient_last_name": "KOŞTUR", "four_maps_eyes": ["OD"]},
        {"document_type": "PENTACAM_TOPOGRAPHY", "patient_first_name": "AYŞE",
         "patient_last_name": "KOŞTUR"},
    ]}
    patient, request = workflow._resolve_patient_metadata({"name": None}, extracted, 37)
    assert patient["name"] == "AYŞE KOŞTUR" and patient["age"] == 37
    assert request is None
    extracted["document_contexts"][1]["patient_last_name"] = "OTHER"
    patient, request = workflow._resolve_patient_metadata({}, extracted, 37)
    assert patient["name"] == "AYŞE KOŞTUR" and request is None
    extracted["document_contexts"][0]["patient_first_name"] = None
    patient, request = workflow._resolve_patient_metadata({}, extracted, 37)
    assert not patient.get("name") and request["form_id"] == "patient_name"
    patient, request = workflow._resolve_patient_metadata({"name": "Confirmed name"}, extracted, 37)
    assert patient["name"] == "Confirmed name" and request is None


def test_extracted_name_reaches_ready_report_metadata():
    session = {"extracted": {"eyes": [_eye("OD"), _eye("OS")],
               "document_contexts": [{"document_type": "PENTACAM_TOPOGRAPHY",
               "patient_first_name": "AYŞE", "patient_last_name": "KOŞTUR", "four_maps_eyes": ["OD"]}]},
               "ready": None, "source_images": []}
    response = workflow._respond(SimpleNamespace(APP_VERSION="test"), "token", session,
                                 37, {"OD": _plan(), "OS": _plan()}, _modifiers(), {}, {})
    assert response["workflow_status"] == "READY"
    assert session["ready"]["patient"]["name"] == "AYŞE KOŞTUR"
    assert response["patient_metadata"]["name"] == "AYŞE KOŞTUR"


def test_name_source_prefers_od_and_uses_os_only_if_od_absent():
    os = {"document_type": "PENTACAM_TOPOGRAPHY", "four_maps_eyes": ["OS"],
          "patient_first_name": "LEFT", "patient_last_name": "NAME"}
    od = dict(os, four_maps_eyes=["OD"], patient_first_name="RIGHT")
    patient, request = workflow._resolve_patient_metadata({}, {"document_contexts": [os, od]}, 37)
    assert patient["name"] == "RIGHT NAME" and request is None
    patient, request = workflow._resolve_patient_metadata({}, {"document_contexts": [os]}, 37)
    assert patient["name"] == "LEFT NAME" and request is None


def _eye(name="OD", **overrides):
    values = {
        "eye": name, "Kmean_D": 43.0, "K2_D": 44.0,
        "ml7_k1_d": 42.0, "ml7_k2_d": 44.0,
        "corneal_diameter_mm": 11.8,
        "table_verified_numeric_fields": ["corneal_diameter_mm"],
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
        "pregnancy_nursing": "no",
        "collagen_tissue_disease": "no", "drug_usage": "no", "dry_eye": "no",
        "systemic_disease": "no",
    }
    values.update(overrides)
    return values


def _respond(*, od=None, plans=None, modifiers=None, overrides=None, extracted_overrides=None,
             source_confirmations=None):
    extracted = {"eyes": [od or _eye("OD"), _eye("OS")], "critical_input_issues": []}
    extracted.update(extracted_overrides or {})
    session = {
        "extracted": extracted,
        "ready": None, "expires": 0, "source_images": [],
    }
    return workflow._respond(
        SimpleNamespace(APP_VERSION="stage11-test"), "token", session, 35,
        plans or {"OD": _plan(), "OS": _plan()}, modifiers or _modifiers(),
        {"name": "Stage 11 Patient"}, overrides or {}, source_confirmations or {},
    )


def test_exam_date_conflict_offers_surgeon_review_and_approval_is_audited():
    conflict = "Conflicting Pentacam examination dates across uploaded sources."
    contexts = [
        {"document_type": "PENTACAM_TOPOGRAPHY", "four_maps_eyes": ["OD"],
         "source_filename": "od.png", "exam_date": "23/09/2026",
         "targeted_exam_date_reread_evidence": {"value": "03/09/2026"}},
        {"document_type": "PENTACAM_TOPOGRAPHY", "four_maps_eyes": ["OS"],
         "source_filename": "os.png", "exam_date": "13/09/2026",
         "targeted_exam_date_reread_evidence": {"value": None}},
    ]
    first = _respond(extracted_overrides={
        "critical_input_issues": [conflict], "document_contexts": contexts,
    })
    assert first["workflow_status"] == "NEEDS_INPUT"
    request = next(item for item in first["input_requests"] if item["destination"] == "source_confirmation")
    assert request["kind"] == "confirmation"
    assert request["options"] == ["APPROVE_CONTINUE"]
    assert "initial 23/09/2026; focused reread 03/09/2026" in request["help"]
    assert "initial 13/09/2026; focused reread unreadable/not returned" in request["help"]

    approved = _respond(
        extracted_overrides={"critical_input_issues": [conflict], "document_contexts": contexts},
        source_confirmations={"pentacam_exam_date_conflict": "APPROVE_CONTINUE"},
    )
    assert approved["workflow_status"] == "READY"
    assert approved["report_token"]
    assert not approved["extracted"]["critical_input_issues"]
    assert approved["extracted"]["surgeon_source_confirmations"][0]["decision"] == "APPROVE_CONTINUE"
    assert any("surgeon reviewed" in item for item in approved["decision"]["identity_warnings"])


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
    assert requests["F_Ele_Th_um"]["source_box"] == (
        "central results table — elevation label/value row immediately above Progression Index "
        "→ F.Ele.Th — adjacent signed µm value"
    )
    assert requests["B_Ele_Th_um"]["source_box"] == (
        "central results table — elevation label/value row immediately above Progression Index "
        "→ B.Ele.Th — adjacent signed µm value"
    )


def test_ps3_intereye_requirement_identifies_the_actual_eye_and_field():
    response = _respond(od=_eye("OD", posterior_Kmean_D=None))
    request = next(item for item in response["input_requests"] if item.get("key") == "posterior_Kmean_D")
    assert request["eye"] == "OD"
    assert request["required_for"] == ["PS3"]
    assert request["source_screen"] == "Show 2 Exams – Topometric"
    assert request["source_box"] == "Cornea Back → Km"


def test_missing_astigmatic_disparity_inputs_do_not_block_ps3_or_request_completion():
    response = _respond(
        od=_eye("OD", topographic_astig_D=None, bad_flat_axis_deg=None),
        plans={"OD": _plan(manifest_cylinder_signed_D=None, manifest_axis_deg=None), "OS": _plan()},
    )
    od_keys = {item["key"] for item in response["input_requests"] if item.get("eye") == "OD"}
    assert "topographic_astig_D" not in od_keys
    assert "bad_flat_axis_deg" not in od_keys


def test_favorable_lasik_requires_missing_ml7_ring_inputs_before_report_release():
    verified_decision_fields = [
        "pachy_thinnest_um", "BAD_D", "Df", "Db", "Dp", "Dt", "Da",
        "ARTmax_um", "PPI_max",
    ]
    od = _eye(
        "OD", ml7_k1_d=None, ml7_k2_d=None, corneal_diameter_mm=None,
        table_verified_numeric_fields=verified_decision_fields,
    )
    response = _respond(od=od)
    requests = {
        item["key"]: item for item in response["input_requests"]
        if item.get("eye") == "OD"
    }
    assert response["workflow_status"] == "NEEDS_INPUT"
    assert response["report_token"] is None
    assert {"ml7_k1_d", "ml7_k2_d", "corneal_diameter_mm"} <= set(requests)
    assert requests["ml7_k1_d"]["source_screen"] == "4 Maps Refractive"
    assert "Anterior Sagittal Curvature (Front)" in requests["ml7_k1_d"]["source_box"]
    assert requests["corneal_diameter_mm"]["source_screen"] == "4 Maps Refractive"
    assert requests["ml7_k1_d"]["required_for"] == ["CER-AI"]

    completed = _respond(od=od, overrides={"OD": {
        "ml7_k1_d": 42.0,
        "ml7_k2_d": 44.0,
        "corneal_diameter_mm": 11.8,
    }})
    assert completed["workflow_status"] == "READY"
    ml7 = completed["decision"]["eyes"][0]["report_payload"]["microkeratome_planning"]
    assert ml7["vacuum_ring_mm"] == 9.0
    assert ml7["vacuum_pressure_mmhg"] == "550"


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


def test_browser_places_plan_definition_beside_name_and_marks_only_requested_safe_ml7_rows():
    html = (ROOT / "static" / "index.html").read_text()
    render_source = html[html.index("function renderEye("):html.index("function patientPayload(")]
    assert 'key==="selected_plan"?(p.planning?.selected_plan_definition||value):value' in render_source
    assert '!["selected_plan_definition","selected_procedure_plan"].includes(key)' in render_source
    for label in (
        "Selected LASIK plan",
        "ML7 Preferred hinge location",
        "ML7 Vacuum ring",
        "ML7 Vacuum pressure",
    ):
        assert label in render_source
    assert '"ML7 blade_recommendations"' not in render_source
    assert "function reportDisplayValue(" in html
    assert "value.map(reportDisplayValue)" in html


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
