"""PS3 presentation adapter for CER-AI reports."""
def _procedure_summary(p):
 d=p.get("disposition") or {};return f"PRK {d.get('prk','NOT EVALUATED')} / SMILE {d.get('smile','NOT EVALUATED')} / LASIK {d.get('lasik','NOT EVALUATED')}"
def _overall_classification(p):
 m=int(p.get("moderate_count") or 0);h=int(p.get("high_count") or 0);return "FAIL / DEFER" if h>=1 or m>=2 else "MODERATE" if m==1 else "NO PS3 RISK FACTOR"
def _ps3_finding_lines(p):
 return [f"{str(x.get('key') or 'PS3 item').replace('_',' ').title()}: {str(x.get('status') or 'NOT_EVALUATED')}"+(f" — {x.get('detail')}" if x.get('detail') else "") for x in p.get("findings") or []]
def _triggering_findings(p):
 out=[]
 for x in p.get("findings") or []:
  if str(x.get("status") or "") in {"MODERATE","HIGH"}:out.append(f"{str(x.get('key') or 'PS3 item').replace('_',' ').title()}: {x.get('status')}"+(f" — {x.get('detail')}" if x.get('detail') else ""))
 return out
def _interpretation_lines(p):
 m=int(p.get("moderate_count") or 0);h=int(p.get("high_count") or 0);c=_overall_classification(p);pr=_procedure_summary(p);t=_triggering_findings(p)
 if c=="NO PS3 RISK FACTOR":return ["PS3 classification: NO PS3 RISK FACTOR. No Moderate or High PS3 criterion was detected among evaluated components.",f"PS3 procedure disposition: {pr}."]
 if c=="MODERATE":return ["PS3 classification: MODERATE — exactly one Moderate PS3 risk factor was detected and no High-risk factor was detected.","PS3 procedure rule: surface ablation/PRK and SMILE remain allowed by PS3; LASIK is DEFERRED by PS3."]+[f"Triggering PS3 criterion: {x}" for x in t]
 return [f"PS3 classification: FAIL / DEFER — {m} Moderate and {h} High PS3 risk factor(s) detected.","PS3 procedure rule: two or more Moderate factors, or any one High factor, DEFER PRK/surface ablation, SMILE, and LASIK under PS3."]+[f"Triggering PS3 criterion: {x}" for x in t]
def install(report_module):
 if getattr(report_module,"_cerai_ps3_report_installed",False):return
 pm=report_module._eye_metrics;pf=report_module._findings
 def metrics(e,locale="en"):
  rows=list(pm(e,locale));p=e.get("ps3") or {}
  if not p.get("applicable"):return rows
  tr=lambda x:report_module.translate_text(x,locale);m=p.get("moderate_count");h=p.get("high_count");s=p.get("srax_deg");inter=p.get("inter_eye_score")
  rows.extend([(tr("PS3 / classification"),tr(f"{m} moderate / {h} high — {_overall_classification(p)}")),(tr("PS3 procedure disposition"),tr(_procedure_summary(p))),(tr("PS3 inter-eye asymmetry score"),tr("Not evaluated" if inter is None else f"{inter}/5")),(tr("PS3 SRAX (Front map only)"),tr("Not evaluated — surgeon confirmation required if map cannot be classified" if s is None else f"{float(s):.1f} degrees"))]);return rows
 def findings(e,locale="en"):
  g=list(pf(e,locale));p=e.get("ps3") or {}
  if not p.get("applicable"):return g
  tr=lambda x:report_module.translate_text(x,locale);a=[tr(x) for x in _interpretation_lines(p)];b=[tr(x) for x in _ps3_finding_lines(p)];r=[tr(str(x)) for x in p.get("review_notes") or []]
  if a:g.append((tr("PS3 summary and interpretation"),a))
  if b:g.append((tr("PS3 criteria audit"),b))
  if r:g.append((tr("PS3 surgeon review required"),r))
  return g
 report_module._eye_metrics=metrics;report_module._findings=findings;report_module._cerai_ps3_report_installed=True
