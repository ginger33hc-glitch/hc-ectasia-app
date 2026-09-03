"""Phase 1 launch-contract golden tests for CER-AI v0.7.71."""
import pytest
import canonical_engine
import clinical_disposition
import mandatory_source_set_policy
from nice_scoring import score_nice
from ps3_policy import ALLOWED, DEFER, PS3EyeInput, evaluate_ps3

core = canonical_engine.core

def _erss_eye(i_s, *, srax_deg=0.0):
    verified=["I_S"] if i_s is not None else []
    return {
        "I_S":i_s,"I_S_status":"CONFIDENT" if i_s is not None else "NOT_SHOWN",
        "table_verified_numeric_fields":verified,"data_conflicts":[],
        "field_provenance":{name:[{"source":"GOLDEN_TEST"}] for name in verified},
        "_erss_i_s_gate_required":True,
        "morphology":"ABNORMAL_ECTATIC","morphology_confidence":"HIGH",
        "morphology_evidence":["must be ignored"],"asymmetric_bow_tie":"YES",
        "srax":"YES" if srax_deg>20 else "NO","srax_deg":srax_deg,
        "inferior_opposite_steepening_D":4.0,
    }

def _source(screen,eye=None,*,document_type="PENTACAM_TOPOGRAPHY",laterality=None):
    eyes=[] if eye is None else [{"eye":eye,"screen_types":[screen]}]
    return {"document_context":{"document_type":document_type,"laterality":laterality or eye or "UNKNOWN"},"eyes":eyes,"treatment_corrections":[]}

def _mandatory_set(include_card=False):
    items=[_source("4 Maps Refractive","OD"),_source("FOUR_MAPS_REFRACTIVE","OS"),_source("Belin/Ambrósio Enhanced Ectasia Display","OD"),_source("BELIN_AMBROSIO_ENHANCED_ECTASIA_DISPLAY","OS"),_source("Show 2 Exams Topometric","OD")]
    if include_card:items.append(_source("EXCIMER_LASER_TREATMENT_CARD",document_type="TREATMENT_CARD"))
    return items

def test_launch_contract_version_and_runtime_startup():
    assert canonical_engine.CANONICAL_VERSION=="0.7.71"; assert canonical_engine.runtime_invariants() is True

def test_mandatory_five_source_set_accepts_real_label_variants():
    s=mandatory_source_set_policy.validate_source_set(_mandatory_set());assert s["mandatory_count"]==5;assert s["missing"]==[];assert s["uploaded_count"]==5

def test_optional_excimer_card_is_sixth_source_only():
    s=mandatory_source_set_policy.validate_source_set(_mandatory_set(include_card=True));assert s["mandatory_count"]==5;assert s["treatment_card_count"]==1;assert s["uploaded_count"]==6

def test_missing_mandatory_source_blocks_before_assessment():
    items=_mandatory_set();items.pop(3)
    with pytest.raises(Exception) as exc:mandatory_source_set_policy.validate_source_set(items)
    assert getattr(exc.value,"status_code",None)==422;assert "OS Belin/Ambrosio Display" in str(getattr(exc.value,"detail",exc.value))

@pytest.mark.parametrize(("i_s","category","points"),[(-5.0,"ASYMMETRIC_BOWTIE",1),(-0.5001,"ASYMMETRIC_BOWTIE",1),(-0.50,"NORMAL_SYMMETRIC",0),(0.0,"NORMAL_SYMMETRIC",0),(0.50,"NORMAL_SYMMETRIC",0),(0.5001,"ASYMMETRIC_BOWTIE",1),(1.00,"ASYMMETRIC_BOWTIE",1),(1.0001,"INFERIOR_STEEPENING_SRA",3),(1.3999,"INFERIOR_STEEPENING_SRA",3),(1.40,"ABNORMAL_ECTATIC",4)])
def test_signed_i_s_golden_boundaries(i_s,category,points):
    scored=core.scoring_morphology(_erss_eye(i_s));assert scored["category"]==category;assert core.lasik_topography_points(category)==points

def test_visual_morphology_has_no_erss_authority():
    scored=core.scoring_morphology(_erss_eye(0.0));assert scored["category"]=="NORMAL_SYMMETRIC";assert core.lasik_topography_points(scored["category"])==0

def test_randleman_srax_threshold_is_strictly_greater_than_twenty_degrees():
    at_20=core.scoring_morphology(_erss_eye(0.5,srax_deg=20.0));above_20=core.scoring_morphology(_erss_eye(0.5,srax_deg=20.1))
    assert at_20["category"]=="NORMAL_SYMMETRIC";assert above_20["category"]=="INFERIOR_STEEPENING_SRA";assert core.lasik_topography_points(above_20["category"])==3

def test_erss_channels_choose_highest_single_category_not_sum():
    scored=core.scoring_morphology(_erss_eye(0.8,srax_deg=21.0));assert scored["category"]=="INFERIOR_STEEPENING_SRA";assert core.lasik_topography_points(scored["category"])==3

@pytest.mark.parametrize(("age","points"),[(18,3),(19,2),(20,2),(21,0),(30,0)])
def test_age_policy_golden_boundaries(age,points):assert core.age_points(age)==points
@pytest.mark.parametrize(("pachy","points"),[(479,None),(480,2),(499,2),(500,1),(509,1),(510,0),(511,0)])
def test_pachymetry_policy_golden_boundaries(pachy,points):assert core.lasik_pachy_points(pachy)==points
@pytest.mark.parametrize(("bad_d","classification"),[(1.60,"NORMAL"),(1.6001,"SUSPICIOUS"),(2.5999,"SUSPICIOUS"),(2.60,"ABNORMAL")])
def test_final_bad_d_golden_boundaries(bad_d,classification):assert core.bad_classification(bad_d,final=True)==classification

def test_nice_golden_disposition_bands():
    a=score_nice(44.0,530.0,15.0,0.5);b=score_nice(46.0,510.0,16.0,1.2);c=score_nice(48.0,490.0,18.0,1.5)
    assert (a["total"],a["category"])==(4,"NO_NICE_ESCALATION");assert (b["total"],b["category"])==(8,"CAUTION");assert (c["total"],c["category"])==(12,"HARD_STOP")

def test_nice_missing_input_is_incomplete():
    r=score_nice(44.0,None,15.0,0.5);assert r["total"] is None;assert r["category"]=="INCOMPLETE";assert "central_pachy_um" in r["missing"]

def _ps3_base(**changes):
    values=dict(anterior_km_d=47.0,thinnest_um=520.0,topographic_astig_d=1.0,topographic_steep_axis_deg=90.0,manifest_astig_d=1.0,manifest_axis_deg=90.0,ppi_avg=1.0,srax="NO",srax_deg=0.0,bfte_front_um=10.0,bfte_back_um=10.0)
    values.update(changes);return evaluate_ps3(PS3EyeInput(**values))

def test_ps3_no_flags_allows_all_three_procedures():
    r=_ps3_base();assert r.high_count==0;assert r.moderate_count==0;assert (r.disposition.prk,r.disposition.smile,r.disposition.lasik)==(ALLOWED,ALLOWED,ALLOWED)

def test_ps3_one_moderate_defers_lasik_only():
    r=_ps3_base(thinnest_um=490.0);assert r.high_count==0;assert r.moderate_count==1;assert (r.disposition.prk,r.disposition.smile,r.disposition.lasik)==(ALLOWED,ALLOWED,DEFER)

def test_ps3_two_moderates_defer_all():
    r=_ps3_base(thinnest_um=490.0,ppi_avg=1.3);assert r.moderate_count>=2;assert (r.disposition.prk,r.disposition.smile,r.disposition.lasik)==(DEFER,DEFER,DEFER)

def test_ps3_high_finding_defers_all():
    r=_ps3_base(anterior_km_d=51.0);assert r.high_count>=1;assert (r.disposition.prk,r.disposition.smile,r.disposition.lasik)==(DEFER,DEFER,DEFER)

def test_ps3_srax_uses_same_strict_twenty_degree_front_map_threshold():
    at_20=_ps3_base(srax_deg=20.0);above_20=_ps3_base(srax="YES",srax_deg=20.1)
    af=next(x for x in at_20.findings if x.key=="srax");bf=next(x for x in above_20.findings if x.key=="srax")
    assert af.status=="NORMAL";assert bf.status=="HIGH"

def test_canonical_status_order_is_frozen():
    assert clinical_disposition.combine_status("PASS","CAUTION")=="CAUTION";assert clinical_disposition.combine_status("CAUTION","POST-REFRACTIVE PATHWAY REQUIRED")=="POST-REFRACTIVE PATHWAY REQUIRED";assert clinical_disposition.combine_status("POST-REFRACTIVE PATHWAY REQUIRED","DATA INSUFFICIENT")=="DATA INSUFFICIENT";assert clinical_disposition.combine_status("DATA INSUFFICIENT","STOP-DEFER")=="STOP-DEFER"

def test_key_safety_constants_are_frozen():
    assert core.PRK_EPITHELIUM_UM==50;assert core.FINAL_KMEAN_MIN_D==36.0;assert core.FINAL_KMEAN_MAX_D==48.0

def test_phase1_contract_runtime_layers_are_present():
    assert core._cerai_erss_numeric_extraction_installed;assert core._erss_topography_evidence_policy_installed;assert core._hc_nice_installed;assert core._cerai_ps3_runtime_installed;assert core._cerai_mandatory_source_set_installed;assert core._hc_final_decision_hierarchy_installed;assert "ERSS VISUAL MORPHOLOGY DISABLED:" in core.PROMPT;assert "ERSS SRAX SOURCE LOCK:" in core.PROMPT
