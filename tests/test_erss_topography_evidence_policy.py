import canonical_engine as runtime
from pathlib import Path
from test_hc_engine import MODIFIERS, normal_eye, plan
core=runtime.core

def lasik_plan():return plan("LASIK",sphere=-3.0,cylinder=0.0,ablation=60,flap=100)
def resolve_srax(eye,degrees):
    eye["srax_deg"]=degrees;eye["srax_source"]="AXIAL_SAGITTAL_CURVATURE_FRONT";eye["srax"]="YES" if degrees>20 else "NO";eye.setdefault("field_provenance",{})["srax"]=[{"source":"SURGEON_CONFIRMED","map":"AXIAL_SAGITTAL_CURVATURE_FRONT"}]

def test_evidence_module_does_not_replace_or_duplicate_point_mapper():
    assert core.lasik_topography_points.__module__=="app";assert core.lasik_topography_points("ASYMMETRIC_BOWTIE")==1;assert core.lasik_topography_points("INFERIOR_STEEPENING_SRA")==3

def test_dedicated_schema_and_browser_form_carry_i_s_confirmation():
    import erss_topography_guard as guard
    assert "I_S" in guard.ERSS_SCHEMA["required"]
    html=Path("static/index.html").read_text(encoding="utf-8");assert '${eye}_surgeon_i_s' in html;assert 'surgeon_I_S_D:numberOrNull' in html

def test_missing_i_s_and_srax_leave_topography_unresolved():
    eye=normal_eye();eye["I_S"]=None;eye["table_verified_numeric_fields"].remove("I_S")
    result=core.assess_eye(eye,lasik_plan(),30,MODIFIERS);e=result["erss_topography_evidence"]
    assert result["randleman_erss"]["rows"]["topography"] is None;assert result["randleman_erss"]["total"] is None;assert e["needs_surgeon_I_S"] is True;assert e["needs_surgeon_SRAX"] is True;assert "PASS" not in result["status"]

def test_visual_morphology_cannot_complete_erss_without_i_s():
    eye=normal_eye(morphology="ASYMMETRIC_BOWTIE");eye["I_S"]=None;eye["table_verified_numeric_fields"].remove("I_S");resolve_srax(eye,10)
    result=core.assess_eye(eye,lasik_plan(),30,MODIFIERS);assert result["randleman_erss"]["rows"]["topography"] is None;assert result["erss_topography_evidence"]["needs_surgeon_I_S"] is True

def test_visual_srax_label_without_authoritative_angle_cannot_complete_erss():
    eye=normal_eye(morphology="INFERIOR_STEEPENING_SRA");eye["srax"]="YES";eye["srax_deg"]=None
    result=core.assess_eye(eye,lasik_plan(),30,MODIFIERS);assert result["randleman_erss"]["rows"]["topography"] is None;assert result["erss_topography_evidence"]["needs_surgeon_SRAX"] is True

def test_lasik_i_s_gate_does_not_change_separate_prk_pathway():
    eye=normal_eye();eye["I_S"]=None;eye["table_verified_numeric_fields"].remove("I_S");result=core.assess_eye(eye,plan("PRK",sphere=-3.0,cylinder=0.0,ablation=60,flap=None),30,MODIFIERS);assert "erss_topography_evidence" not in result

def test_conflicting_i_s_is_not_resolved_by_scoring_maximum():
    eye=normal_eye();eye["data_conflicts"]=["I_S: 0.50 vs 1.50"];resolve_srax(eye,10);result=core.assess_eye(eye,lasik_plan(),30,MODIFIERS);assert result["erss_topography_evidence"]["I_S_status"]=="CONFLICT";assert result["randleman_erss"]["total"] is None

def test_dedicated_and_general_same_image_i_s_conflict_requires_confirmation(monkeypatch):
    import erss_topography_guard as guard
    from test_erss_runtime import eye as extracted_eye,result as extraction_result
    source_eye=extracted_eye(True,"NORMAL_SYMMETRIC","topometric.jpg");source_eye["I_S"]=0.5;source_eye["table_verified_numeric_fields"]=["I_S"];general=extraction_result(source_eye,"topometric.jpg")
    monkeypatch.setattr(guard,"_original_extract_one_image",lambda raw,filename:general);monkeypatch.setattr(guard,"_erss_second_pass",lambda raw,filename:{"display_type":"PENTACAM_TOPOMETRIC_KC","eye":"OD","I_S":0.75,"I_S_status":"CONFIDENT"})
    extracted=guard.extract_one_image_with_erss(b"image","topometric.jpg");assert extracted["eyes"][0]["I_S"] is None;assert any(str(item).startswith("I_S:") for item in extracted["eyes"][0]["data_conflicts"])

def test_i_s_abt_scores_one_when_srax_resolved_negative():
    eye=normal_eye();eye["I_S"]=0.75;resolve_srax(eye,10);result=core.assess_eye(eye,lasik_plan(),30,MODIFIERS);assert result["erss_topography_evidence"]["validated_category"]=="ASYMMETRIC_BOWTIE";assert result["randleman_erss"]["rows"]["topography"]==1

def test_srax_over_20_selects_single_three_point_category():
    eye=normal_eye();eye["I_S"]=0.8;resolve_srax(eye,20.1);result=core.assess_eye(eye,lasik_plan(),30,MODIFIERS);assert result["erss_topography_evidence"]["validated_category"]=="INFERIOR_STEEPENING_SRA";assert result["randleman_erss"]["rows"]["topography"]==3

def test_srax_exactly_20_is_not_positive():
    eye=normal_eye();eye["I_S"]=0.8;resolve_srax(eye,20.0);result=core.assess_eye(eye,lasik_plan(),30,MODIFIERS);assert result["erss_topography_evidence"]["validated_category"]=="ASYMMETRIC_BOWTIE";assert result["randleman_erss"]["rows"]["topography"]==1

def test_surgeon_i_s_enters_numeric_classifier_when_srax_resolved():
    eye=normal_eye();eye["I_S"]=None;eye["table_verified_numeric_fields"].remove("I_S");resolve_srax(eye,10);p=lasik_plan();p["surgeon_I_S_D"]=-0.61;result=core.assess_eye(eye,p,30,MODIFIERS);assert result["erss_topography_evidence"]["I_S_source"]=="SURGEON_ENTRY";assert result["erss_topography_evidence"]["validated_category"]=="ASYMMETRIC_BOWTIE"

def test_i_s_at_abnormal_threshold_uses_four_point_category_when_srax_resolved():
    eye=normal_eye();eye["I_S"]=1.4;resolve_srax(eye,10);result=core.assess_eye(eye,lasik_plan(),30,MODIFIERS);assert result["erss_topography_evidence"]["validated_category"]=="ABNORMAL_ECTATIC";assert result["randleman_erss"]["rows"]["topography"]==4

def test_all_five_lasik_erss_parameter_boundaries_are_locked():
    assert [core.lasik_rsb_points(x) for x in (239.999,240,260,280,300)]==[4,3,2,1,0]
    assert [core.age_points(x) for x in (18,19,20,21,30)]==[3,2,2,0,0]
    assert [core.lasik_pachy_points(x) for x in (479.999,480,480.001,499.999,500,509.999,510)]==[None,None,2,2,1,1,0]
    assert [core.lasik_mrse_points(x) for x in (-14.001,-14,-12,-10,-8)]==[4,3,2,1,0]

def test_complete_erss_rows_use_manifest_mrse_and_planned_rsb_with_authoritative_topography():
    eye=normal_eye(pachy=520);eye["I_S"]=0.0;resolve_srax(eye,10);p=lasik_plan();p.update({"manifest_sphere_D":-9.0,"manifest_cylinder_magnitude_D":2.0,"manifest_normalized_axis_deg":180,"flap_um":100,"ablation_um":140})
    result=core.assess_eye(eye,p,20,MODIFIERS);erss=result["randleman_erss"];assert result["values"]["MRSE_D"]==-10.0;assert erss["rows"]=={"topography":0,"RSB":0,"age":2,"pachymetry":0,"MRSE":1};assert erss["total"]==3;assert erss["bad_dependency"] is False
