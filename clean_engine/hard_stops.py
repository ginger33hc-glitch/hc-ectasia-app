"""Pure independent hard-stop evaluation for the parallel clean engine."""
from dataclasses import dataclass
from typing import Optional,Tuple
from .policy import POLICY,score_decision_band
@dataclass(frozen=True)
class HardStopInput:
    procedure:str;pachy_thinnest_um:Optional[float];morphology:str;bad_d_status:str;intended_sphere_d:Optional[float];lasik_rsb_um:Optional[float]=None;prk_rst_um:Optional[float]=None;final_kmean_d:Optional[float]=None;lasik_erss_total:Optional[float]=None
def evaluate_hard_stops(inp:HardStopInput)->Tuple[str,...]:
    stops=[];procedure=(inp.procedure or "").upper()
    if inp.pachy_thinnest_um is not None and float(inp.pachy_thinnest_um)<=POLICY.pachymetry_hard_stop_um:stops.append("PACHYMETRY_LE_480")
    if inp.morphology=="ABNORMAL_ECTATIC":stops.append("ABNORMAL_ECTATIC_TOPOGRAPHY")
    if inp.bad_d_status=="ABNORMAL":stops.append("FINAL_BAD_D_ABNORMAL")
    if inp.intended_sphere_d is not None:
        sphere=float(inp.intended_sphere_d)
        if sphere<-10.0:stops.append("INTENDED_SPHERE_LT_MINUS_10")
        if sphere>6.0:stops.append("INTENDED_SPHERE_GT_PLUS_6")
    if procedure=="LASIK" and inp.lasik_rsb_um is not None and float(inp.lasik_rsb_um)<POLICY.lasik_rsb_hard_stop_um:stops.append("LASIK_RSB_LT_300")
    if procedure=="PRK" and inp.prk_rst_um is not None and float(inp.prk_rst_um)<POLICY.prk_rst_hard_stop_um:stops.append("PRK_RST_LT_310")
    if inp.final_kmean_d is not None and not(POLICY.final_kmean_min_d<=float(inp.final_kmean_d)<=POLICY.final_kmean_max_d):stops.append("FINAL_KMEAN_OUTSIDE_36_48")
    if procedure=="LASIK" and score_decision_band(inp.lasik_erss_total)=="STOP":stops.append("ERSS_GE_4")
    return tuple(stops)
