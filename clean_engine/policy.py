"""Pure CER-AI clinical policy definitions for the parallel clean engine.

Phase 2 rule: this module mirrors the active CER-AI clinical policy while remaining
architecturally separated from extraction, transport, and reporting concerns.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class HCPolicy:
    prk_epithelium_um:float=50.0
    corneal_effect_per_intended_mrse_d:float=0.8
    final_kmean_min_d:float=36.0
    final_kmean_max_d:float=48.0
    lasik_pta_cutoff_percent:float=40.0
    pachymetry_hard_stop_um:float=480.0
    lasik_rsb_hard_stop_um:float=300.0
    prk_rst_hard_stop_um:float=310.0
    bad_d_normal_max:float=1.6
    bad_d_abnormal_min:float=2.6
    score_caution:int=3
    score_stop:int=4
POLICY=HCPolicy()

def score_decision_band(score:Optional[float])->Optional[str]:
    if not isinstance(score,(int,float)) or isinstance(score,bool):return None
    value=float(score)
    if value>=POLICY.score_stop:return "STOP"
    if value>=POLICY.score_caution:return "CAUTION"
    return "NO_SCORE_ESCALATION"
def age_points(age:Optional[float])->Optional[int]:
    if not isinstance(age,(int,float)) or isinstance(age,bool) or age<18:return None
    if age<19:return 3
    if age<21:return 2
    return 0
def lasik_pachymetry_points(pachy_um:Optional[float])->Optional[int]:
    """CER-AI operational bands: <=480 hard stop; 481-499 +2; 500-509 +1; >=510 +0."""
    if not isinstance(pachy_um,(int,float)) or isinstance(pachy_um,bool):return None
    value=float(pachy_um)
    if value<=POLICY.pachymetry_hard_stop_um:return None
    if value<500:return 2
    if value<510:return 1
    return 0
def final_bad_d_classification(value:Optional[float])->str:
    if not isinstance(value,(int,float)) or isinstance(value,bool):return "UNAVAILABLE"
    value=float(value)
    if value<=POLICY.bad_d_normal_max:return "NORMAL"
    if value<POLICY.bad_d_abnormal_min:return "SUSPICIOUS"
    return "ABNORMAL"
def randleman_topography_points(morphology:str)->Optional[int]:
    return {"NORMAL_SYMMETRIC":0,"ASYMMETRIC_BOWTIE":1,"INFERIOR_STEEPENING_SRA":3,"ABNORMAL_ECTATIC":4}.get(morphology)
def lasik_rsb_points(rsb_um:Optional[float])->Optional[int]:
    if not isinstance(rsb_um,(int,float)) or isinstance(rsb_um,bool):return None
    value=float(rsb_um)
    if value<240:return 4
    if value<260:return 3
    if value<280:return 2
    if value<300:return 1
    return 0
def lasik_mrse_points(mrse_d:Optional[float])->Optional[int]:
    if not isinstance(mrse_d,(int,float)) or isinstance(mrse_d,bool):return None
    value=float(mrse_d)
    if value<-14:return 4
    if value<-12:return 3
    if value<-10:return 2
    if value<-8:return 1
    return 0
def lasik_erss_total(age,pachy,morphology,rsb,mrse):
    rows=(age_points(age),lasik_pachymetry_points(pachy),randleman_topography_points(morphology),lasik_rsb_points(rsb),lasik_mrse_points(mrse))
    return None if any(x is None for x in rows) else sum(rows)
