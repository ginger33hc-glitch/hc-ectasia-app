"""Independent Practical Subjective Scoring System (PS3) policy for CER-AI.

PS3 does not modify Randleman/ERSS, BAD-D, NICE, or tissue-safety scores.
SRAX is an input observation only. This module never calculates or reconstructs SRAX.
The authoritative SRAX state must already have been resolved from the
Axial/Sagittal Curvature (Front) map or explicit surgeon confirmation.
"""
from dataclasses import dataclass, field
from math import isfinite
from typing import Optional, Tuple

NORMAL="NORMAL"; MODERATE="MODERATE"; HIGH="HIGH"; NOT_EVALUATED="NOT_EVALUATED"
ALLOWED="ALLOWED"; DEFER="DEFER"

@dataclass(frozen=True)
class PS3EyeInput:
    anterior_km_d: Optional[float]=None
    thinnest_um: Optional[float]=None
    topographic_astig_d: Optional[float]=None
    topographic_steep_axis_deg: Optional[float]=None
    manifest_astig_d: Optional[float]=None
    manifest_axis_deg: Optional[float]=None
    ppi_avg: Optional[float]=None
    srax_status: Optional[str]=None
    srax_deg: Optional[float]=None
    srax_source: Optional[str]=None
    bfs_front_um: Optional[float]=None
    bfs_back_um: Optional[float]=None
    bfte_front_um: Optional[float]=None
    bfte_back_um: Optional[float]=None
    refractive_group: Optional[str]=None

@dataclass(frozen=True)
class PS3InterEyeInput:
    od_anterior_km_d: Optional[float]=None; os_anterior_km_d: Optional[float]=None
    od_posterior_km_d: Optional[float]=None; os_posterior_km_d: Optional[float]=None
    od_thinnest_um: Optional[float]=None; os_thinnest_um: Optional[float]=None
    od_front_elevation_thinnest_um: Optional[float]=None; os_front_elevation_thinnest_um: Optional[float]=None
    od_back_elevation_thinnest_um: Optional[float]=None; os_back_elevation_thinnest_um: Optional[float]=None

@dataclass(frozen=True)
class PS3Finding:
    key:str; status:str; detail:str
@dataclass(frozen=True)
class PS3ProcedureDisposition:
    prk:str; smile:str; lasik:str
@dataclass(frozen=True)
class PS3Result:
    findings:Tuple[PS3Finding,...]; moderate_count:int; high_count:int
    disposition:PS3ProcedureDisposition; srax_deg:Optional[float]=None
    inter_eye_score:Optional[int]=None; review_notes:Tuple[str,...]=field(default_factory=tuple)

def _num(v):
    if isinstance(v,bool) or not isinstance(v,(int,float)): return None
    v=float(v); return v if isfinite(v) else None

def _axis_difference_deg(a,b):
    a=_num(a); b=_num(b)
    if a is None or b is None:return None
    d=abs((a%180)-(b%180)); return min(d,180-d)

def _inter_eye_score(inp):
    if inp is None:return None,PS3Finding("inter_eye_asymmetry",NOT_EVALUATED,"Bilateral PS3 inter-eye values unavailable.")
    pairs=(("anterior Km",inp.od_anterior_km_d,inp.os_anterior_km_d,.3),("posterior Km",inp.od_posterior_km_d,inp.os_posterior_km_d,.1),("thinnest pachymetry",inp.od_thinnest_um,inp.os_thinnest_um,12),("front elevation at thinnest",inp.od_front_elevation_thinnest_um,inp.os_front_elevation_thinnest_um,2),("back elevation at thinnest",inp.od_back_elevation_thinnest_um,inp.os_back_elevation_thinnest_um,5))
    if any(_num(a) is None or _num(b) is None for _,a,b,_ in pairs):return None,PS3Finding("inter_eye_asymmetry",NOT_EVALUATED,"One or more bilateral PS3 inter-eye values are unavailable.")
    exceeded=[label for label,a,b,t in pairs if abs(float(a)-float(b))>=t]
    score=len(exceeded); status=HIGH if score==5 else MODERATE if score==4 else NORMAL
    return score,PS3Finding("inter_eye_asymmetry",status,f"Inter-eye score {score}/5"+(f"; exceeded: {', '.join(exceeded)}." if exceeded else "."))

def _elevation_finding(i):
    bf,bb,tf,tb=map(_num,(i.bfs_front_um,i.bfs_back_um,i.bfte_front_um,i.bfte_back_um)); g=str(i.refractive_group or "").upper(); reasons=[]
    if g=="MYOPIC_EMMETROPIC":
        if bf is not None and bf>=8:reasons.append(f"BFS front {bf:g} µm >= 8")
        if bb is not None and bb>=18:reasons.append(f"BFS back {bb:g} µm >= 18")
    elif g=="HYPEROPIC_MIXED":
        if bf is not None and bf>=7:reasons.append(f"BFS front {bf:g} µm >= 7")
        if bb is not None and bb>=28:reasons.append(f"BFS back {bb:g} µm >= 28")
    if tf is not None and tf>12:reasons.append(f"BFTE front {tf:g} µm > 12")
    if tb is not None and tb>15:reasons.append(f"BFTE back {tb:g} µm > 15")
    if reasons:return PS3Finding("elevation",HIGH,"; ".join(reasons)+".")
    if None not in (tf,tb) or (g in {"MYOPIC_EMMETROPIC","HYPEROPIC_MIXED"} and None not in (bf,bb)):
        return PS3Finding("elevation",NORMAL,"Available elevation criteria are below PS3 high-risk thresholds.")
    return PS3Finding("elevation",NOT_EVALUATED,"Required PS3 elevation values are incomplete.")

def _srax_finding(eye):
    status=str(eye.srax_status or "UNRESOLVED").upper(); deg=_num(eye.srax_deg); source=str(eye.srax_source or "").upper()
    direct=source in {"AXIAL_SAGITTAL_CURVATURE_FRONT","SURGEON_CONFIRMED_FRONT_MAP_REVIEW"}
    if not direct:
        return PS3Finding("srax",NOT_EVALUATED,"Authoritative Front-map SRAX is unavailable; no surrogate calculation is permitted.")
    if deg is not None:
        if not 0<=deg<=90:return PS3Finding("srax",NOT_EVALUATED,"Front-map SRAX is outside the accepted 0-90° range.")
        expected="YES" if deg>20 else "NO"
        if status not in {expected,"UNRESOLVED"}:
            return PS3Finding("srax",NOT_EVALUATED,"SRAX status conflicts with the authoritative Front-map degree value.")
        return PS3Finding("srax",HIGH if deg>20 else NORMAL,f"Authoritative Front-map SRAX {deg:.1f}°; positive criterion is strictly >20°.")
    if status=="YES":return PS3Finding("srax",HIGH,"Surgeon confirmed SRAX >20° from the Axial/Sagittal Curvature (Front) map.")
    if status=="NO":return PS3Finding("srax",NORMAL,"Surgeon confirmed SRAX is not >20° from the Axial/Sagittal Curvature (Front) map.")
    return PS3Finding("srax",NOT_EVALUATED,"SRAX remains unresolved; surgeon Front-map confirmation is required.")

def evaluate_ps3(eye,inter_eye=None):
    findings=[]; km=_num(eye.anterior_km_d)
    findings.append(PS3Finding("anterior_km",NOT_EVALUATED,"Anterior Km unavailable.") if km is None else PS3Finding("anterior_km",HIGH,f"Anterior Km {km:g} D > 50 D.") if km>50 else PS3Finding("anterior_km",MODERATE,f"Anterior Km {km:g} D is 48-50 D.") if km>=48 else PS3Finding("anterior_km",NORMAL,f"Anterior Km {km:g} D < 48 D."))
    th=_num(eye.thinnest_um)
    findings.append(PS3Finding("thinnest",NOT_EVALUATED,"Thinnest pachymetry unavailable.") if th is None else PS3Finding("thinnest",HIGH,f"Thinnest {th:g} µm < 470 µm.") if th<470 else PS3Finding("thinnest",MODERATE,f"Thinnest {th:g} µm is 470-500 µm.") if th<=500 else PS3Finding("thinnest",NORMAL,f"Thinnest {th:g} µm > 500 µm."))
    ta,ma=_num(eye.topographic_astig_d),_num(eye.manifest_astig_d); ad=_axis_difference_deg(eye.topographic_steep_axis_deg,eye.manifest_axis_deg)
    if ta is None or ma is None or ad is None:findings.append(PS3Finding("astigmatic_study",NOT_EVALUATED,"Manifest/topographic astigmatism magnitude or axis unavailable."))
    else:
        md=abs(abs(ma)-abs(ta)); findings.append(PS3Finding("astigmatic_study",MODERATE if md>1 or ad>10 else NORMAL,f"Astigmatism difference {md:.2f} D; axis difference {ad:.1f}°."))
    findings.append(_elevation_finding(eye)); p=_num(eye.ppi_avg)
    findings.append(PS3Finding("ppi_average",NOT_EVALUATED,"PPI Average unavailable.") if p is None else PS3Finding("ppi_average",MODERATE,f"PPI Average {p:g} > 1.20.") if p>1.2 else PS3Finding("ppi_average",NORMAL,f"PPI Average {p:g} <= 1.20."))
    findings.append(_srax_finding(eye)); score,inter=_inter_eye_score(inter_eye); findings.append(inter)
    notes=("Corneal Thickness Map morphology (Dome/Bell/Globus) not evaluated — surgeon review required.","Relative Thickness Map not evaluated — surgeon review required.","PTI/CTSP thickness-profile morphology (S-shape/quick slope/inverted slope) not evaluated — surgeon review required.")
    findings.extend((PS3Finding("corneal_thickness_map_morphology",NOT_EVALUATED,notes[0]),PS3Finding("relative_thickness_map",NOT_EVALUATED,notes[1]),PS3Finding("pti_ctsp_morphology",NOT_EVALUATED,notes[2])))
    moderate=sum(x.status==MODERATE for x in findings); high=sum(x.status==HIGH for x in findings)
    disposition=PS3ProcedureDisposition(DEFER,DEFER,DEFER) if high>=1 or moderate>=2 else PS3ProcedureDisposition(ALLOWED,ALLOWED,DEFER) if moderate==1 else PS3ProcedureDisposition(ALLOWED,ALLOWED,ALLOWED)
    return PS3Result(tuple(findings),moderate,high,disposition,_num(eye.srax_deg),score,notes)
