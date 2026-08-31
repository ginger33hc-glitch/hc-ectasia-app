"""CER-AI-approved boundaries and fail-closed API/report completion behavior."""
from copy import deepcopy
from io import BytesIO
import itertools
import json

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader

import canonical_engine as runtime
import assessment_workflow as workflow
from nice_scoring import score_nice
from nice_policy import evaluate, attach_readings
from test_hc_engine import normal_eye, plan, MODIFIERS, document_context

core = runtime.core


def scenario(procedure="LASIK"):
    extracted = {"eyes": [normal_eye("OD"), normal_eye("OS")], "critical_input_issues": []}
    for eye in extracted["eyes"]:
        eye["morphology_confidence"] = "HIGH"
        eye["erss_source_read"] = "DEDICATED_CURVATURE_PASS"
    plans = {eye: plan(procedure, flap=100 if procedure == "LASIK" else None) for eye in ("OD", "OS")}
    return extracted, plans


@pytest.mark.parametrize("value,points", [(0,1),(14,1),(15,1),(15.5,1),(15.5001,2),(16,2),(17,2),(17.5,2),(17.999,2),(18,3),(50,3)])
def test_pe_boundary_no_gap_or_rounding(value, points):
    assert score_nice(43, 550, value, .5)["rows"]["posterior_elevation"] == points


@pytest.mark.parametrize("k2,pachy,pe,i_s", list(itertools.product([44,46,48],[550,510,490],[8,16,18],[.5,1.2,1.5])))
def test_all_81_score_combinations(k2,pachy,pe,i_s):
    result = score_nice(k2,pachy,pe,i_s)
    assert 4 <= result["total"] <= 12
    assert result["total"] == sum(result["rows"].values())
    assert result["category"] == ("NO_NICE_ESCALATION" if result["total"]==4 else "CAUTION" if result["total"]<=8 else "HARD_STOP")


@pytest.mark.parametrize("value", [None, True, "15", float("nan"), float("inf"), -1])
def test_invalid_pe_is_not_scored(value):
    assert score_nice(43,550,value,.5)["total"] is None


def test_exact_other_boundaries_and_signed_i_s():
    assert score_nice(45,520,15.5,1)["rows"] == {"K2":2,"central_pachymetry":2,"posterior_elevation":1,"I_S":2}
    assert score_nice(47,500,15.5,1.4)["rows"] == {"K2":2,"central_pachymetry":2,"posterior_elevation":1,"I_S":2}
    assert score_nice(43,550,8,-2)["rows"]["I_S"] == 1


def test_k2_merge_tolerance_cannot_cross_nice_boundary():
    eye = normal_eye()
    eye['nice_raw_k2_readings'] = [44.9, 45.1]
    assert 'K2_D' in evaluate(eye, plan())['missing']
    eye['surgeon_verified_numeric_fields'] = ['K2_D']
    eye['K2_D'] = 45.1
    assert evaluate(eye, plan())['rows']['K2'] == 2


def test_malformed_completion_nested_override_fails_closed():
    extracted, plans = scenario()
    ready = workflow.begin(core, extracted, 35, plans, MODIFIERS, {})
    plans['OD']['surgeon_I_S_D'] = .5
    client = TestClient(core.app)
    response = client.post('/assessment/complete', json={
        'assessment_token': ready['assessment_token'], 'age': 35,
        'eye_plans': plans, 'patient_modifiers': MODIFIERS, 'clinical_overrides': {'OD': None}})
    assert response.status_code == 422
    assert client.post('/report/pdf', json=ready).status_code == 409


@pytest.mark.parametrize("procedure", ["LASIK","PRK"])
@pytest.mark.parametrize("pe,k2,central,total,status", [(8,43,565,4,None),(16,43,565,5,"CAUTION"),(18,46,510,8,"CAUTION"),(18,46,490,9,"DO NOT PROCEED")])
def test_runtime_4_5_8_9_and_no_duplicate_erss(procedure,pe,k2,central,total,status):
    extracted,plans=scenario(procedure)
    eye=extracted["eyes"][0]
    eye["K2_D"]=k2
    eye["nice_candidates"][0].update(posterior_pupil_max_um=pe,central_pachy_um=central)
    from microkeratome_planning_policy import hc_engine_with_microkeratome_planning
    before=hc_engine_with_microkeratome_planning(deepcopy(extracted),35,deepcopy(plans),MODIFIERS)["eyes"][0]
    after=core.hc_engine(extracted,35,plans,MODIFIERS)["eyes"][0]
    assert after["nice"]["total"]==total
    assert before.get("randleman_erss")==after.get("randleman_erss")
    assert before["score"]==after["score"]
    assert before["tomography_review"]==after["tomography_review"]
    if status: assert after["status"].startswith(status)
    else: assert after["status"]==before["status"]
    if total>=5: assert "microkeratome_planning" not in after


def test_nice_cannot_reduce_bad_hard_stop_or_rescue_with_flap_change():
    extracted,plans=scenario()
    extracted["eyes"][0]["BAD_D"]=3.1
    assert core.hc_engine(extracted,35,plans,MODIFIERS)["eyes"][0]["status"]=="DO NOT PROCEED"
    extracted["eyes"][0]["BAD_D"]=1
    extracted["eyes"][0]["K2_D"]=48
    extracted["eyes"][0]["nice_candidates"][0].update(central_pachy_um=490,posterior_pupil_max_um=18)
    for flap in (90,100,120):
        plans["OD"]["flap_um"]=flap
        assert core.hc_engine(extracted,35,plans,MODIFIERS)["eyes"][0]["status"]=="DO NOT PROCEED"


@pytest.mark.parametrize("key,value", [("pupil_boundary_visible",False),("posterior_reference","BFTE"),("bfs_diameter_mm",9),("posterior_status","UNREADABLE")])
def test_wrong_map_settings_never_accepted(key,value):
    eye=normal_eye();eye["nice_candidates"][0][key]=value
    assert "posterior_pupil_max_um" in evaluate(eye,plan())["missing"]


def test_no_substitution_of_thinnest_pachy_or_elevation():
    eye=normal_eye();eye["nice_candidates"]=[]
    assert set(evaluate(eye,plan())["missing"])=={"central_pachy_um","posterior_pupil_max_um"}


def test_conflicting_nice_readings_require_confirmation_and_keep_source():
    eye=normal_eye();eye["nice_candidates"].append({**eye["nice_candidates"][0],"posterior_pupil_max_um":16})
    assert evaluate(eye,plan())["input_sources"]["posterior_elevation"]=="CONFLICT"
    result=evaluate(eye,{**plan(),"surgeon_nice_pe_um":15.5})
    assert result["rows"]["posterior_elevation"]==1
    assert result["input_sources"]["posterior_elevation"]=="SURGEON_CONFIRMED"


def test_dedicated_readings_laterality_and_schema():
    extracted,plans=scenario()
    reading={**normal_eye()["nice_candidates"][0],"eye":"OD"}
    attach_readings(extracted,[{"document_context":{"document_type":"PENTACAM_TOPOGRAPHY","source_filename":"od.jpg"},"nice_readings":[reading]}])
    assert len(extracted["eyes"][0]["nice_candidates"])==1
    assert extracted["eyes"][1]["nice_candidates"]==[]
    assert "nice_readings" in core.SCHEMA["required"]
    assert core.lasik_topography_points.__module__=="app"
    assert runtime.runtime_invariants()


def test_missing_manifest_bad_nice_all_prompt_together_no_report(monkeypatch):
    extracted,plans=scenario()
    extracted["eyes"][0]["BAD_D"]=None
    extracted["eyes"][1]["nice_candidates"]=[]
    plans["OD"]["manifest_sphere_D"]=None
    plans["OD"]["manifest_cylinder_magnitude_D"]=None
    result=workflow.begin(core,extracted,35,plans,MODIFIERS,{})
    assert result["workflow_status"]=="NEEDS_INPUT"
    assert "decision" not in result and result["report_token"] is None
    messages=" ".join(x["message"] for x in result["missing"])
    assert "manifest sphere" in messages and "BAD_D" in messages and "NICE:" in messages
    monkeypatch.setattr(core,"build_pdf",lambda _:pytest.fail("Incomplete report builder must not run"))
    response=TestClient(core.app).post("/report/pdf",json={"assessment_token":result["assessment_token"],"decision":{"status":"PASS"}})
    assert response.status_code==409


def test_complete_keeps_manual_signed_refraction_and_does_not_reextract(monkeypatch):
    extracted,plans=scenario()
    extracted["eyes"][0]["BAD_D"]=None
    plans["OD"].update(manifest_entered_sphere_D=-4,manifest_cylinder_signed_D=1,entered_axis_deg=8)
    result=workflow.begin(core,extracted,35,plans,MODIFIERS,{})
    monkeypatch.setattr(core,"extract_one_image",lambda *_:pytest.fail("Completion must not read images again"))
    response=TestClient(core.app).post("/assessment/complete",json={"assessment_token":result["assessment_token"],"age":35,
        "eye_plans":plans,"patient_modifiers":MODIFIERS,"clinical_overrides":{"OD":{"BAD_D":1}}})
    ready=response.json()
    assert ready["workflow_status"]=="READY",ready
    values=ready["decision"]["eyes"][0]["values"]
    assert values["manifest_entered_sphere_D"]==-4 and values["manifest_cylinder_signed_D"]==1
    assert values["manifest_sphere_D"]==-3 and values["manifest_normalized_axis_deg"]==98
    exported=workflow.export_payload({"assessment_token":ready["assessment_token"],"report_token":ready["report_token"],"decision":{"status":"FORGED"}})
    assert exported["decision"]["status"]!="FORGED"


def test_surgeon_i_s_resolves_conflict_for_both_scorers():
    extracted,plans=scenario()
    extracted["eyes"][0]["data_conflicts"]=["I_S: 0.5 vs 1.6"]
    result=workflow.begin(core,extracted,35,plans,MODIFIERS,{})
    plans["OD"]["surgeon_I_S_D"]=.5
    ready=workflow.complete(core,{"assessment_token":result["assessment_token"],"age":35,"eye_plans":plans,"patient_modifiers":MODIFIERS})
    assert ready["workflow_status"]=="READY",ready
    assert ready["decision"]["eyes"][0]["erss_topography_evidence"]["I_S_status"]=="SURGEON_CONFIRMED"
    assert ready["decision"]["eyes"][0]["nice"]["values"]["I_S_D"]==.5


def test_hard_stop_does_not_skip_other_missing_questions():
    extracted,plans=scenario()
    extracted["eyes"][0]["BAD_D"]=4
    plans["OS"]["manifest_sphere_D"]=None
    assert workflow.begin(core,extracted,35,plans,MODIFIERS,{})["workflow_status"]=="NEEDS_INPUT"


def test_prior_surgery_not_forced_through_nice():
    extracted,plans=scenario()
    for eye in extracted["eyes"]:eye["nice_candidates"]=[]
    for p in plans.values():p["prior"]="yes"
    result=workflow.begin(core,extracted,35,plans,MODIFIERS,{})
    assert result["workflow_status"]=="READY"
    assert all(e["nice"]["category"]=="NOT_APPLICABLE" for e in result["decision"]["eyes"])


def test_stale_or_forged_exports_rejected_and_expiry_safe():
    extracted,plans=scenario()
    ready=workflow.begin(core,extracted,35,plans,MODIFIERS,{})
    token=ready["assessment_token"]
    client=TestClient(core.app)
    assert client.post("/report/word",json={"assessment_token":token,"report_token":"fake"}).status_code==409
    plans["OD"]["manifest_sphere_D"]=None
    workflow.complete(core,{"assessment_token":token,"age":35,"eye_plans":plans,"patient_modifiers":MODIFIERS})
    assert client.post("/report/pdf",json={"assessment_token":token,"report_token":ready["report_token"]}).status_code==409
    workflow._sessions[token]["expires"]=0
    assert client.post("/assessment/complete",json={"assessment_token":token}).status_code==410


def test_nice_report_pdf_contains_values_class_and_hc_footnote():
    extracted,plans=scenario()
    extracted["eyes"][0]["nice_candidates"][0]["posterior_pupil_max_um"]=16
    ready=workflow.begin(core,extracted,35,plans,MODIFIERS,{"name":"SYNTHETIC QA"})
    pdf=TestClient(core.app).post("/report/pdf",json={"assessment_token":ready["assessment_token"],"report_token":ready["report_token"]})
    assert pdf.status_code==200
    text=" ".join(page.extract_text() for page in PdfReader(BytesIO(pdf.content)).pages)
    for required in ("NICE", "15.5", "5-8", ">=9", "Final BAD-D", "ERSS", "central_pachymetry"):
        assert required in text
