"""PS3 presentation adapter. Reports stored PS3 outputs only; never recalculates SRAX or clinical scores."""
def _procedure_summary(p):
    d=p.get("disposition") or {};return f"PRK {d.get('prk','NOT EVALUATED')} / SMILE {d.get('smile','NOT EVALUATED')} / LASIK {d.get('lasik','NOT EVALUATED')}"
def _overall(p):
    m=int(p.get("moderate_count") or 0);h=int(p.get("high_count") or 0);return "FAIL / DEFER" if h>=1 or m>=2 else "MODERATE" if m==1 else "NO PS3 RISK FACTOR"
def _finding_lines(p):
    return [f"{str(x.get('key') or 'PS3 item').replace('_',' ').title()}: {str(x.get('status') or 'NOT_EVALUATED')}"+(f" — {x.get('detail')}" if x.get('detail') else "") for x in p.get("findings") or []]
def _triggers(p):return [x for x in _finding_lines(p) if ": MODERATE" in x or ": HIGH" in x]
def _interpretation(p):
    m=int(p.get("moderate_count") or 0);h=int(p.get("high_count") or 0);c=_overall(p);pr=_procedure_summary(p);t=_triggers(p)
    if c=="NO PS3 RISK FACTOR":return ["PS3 classification: NO PS3 RISK FACTOR. No Moderate or High PS3 criterion was detected among evaluated components.",f"PS3 procedure disposition: {pr}."]
    if c=="MODERATE":return ["PS3 classification: MODERATE — exactly one Moderate PS3 risk factor was detected and no High-risk factor was detected.","PS3 procedure rule: PRK/surface ablation and SMILE remain allowed by PS3; LASIK is DEFERRED by PS3."]+[f"Triggering PS3 criterion: {x}" for x in t]
    return [f"PS3 classification: FAIL / DEFER — {m} Moderate and {h} High PS3 risk factor(s) detected.","PS3 procedure rule: two or more Moderate factors, or any one High factor, DEFER PRK/surface ablation, SMILE, and LASIK under PS3."]+[f"Triggering PS3 criterion: {x}" for x in t]
def _stored_srax_text(p):
    finding=next((x for x in p.get("findings") or [] if x.get("key")=="srax"),None)
    if not finding:return "Not evaluated"
    status=str(finding.get("status") or "NOT_EVALUATED");detail=str(finding.get("detail") or "")
    return f"{status} — {detail}" if detail else status

def install(report_module):
    if getattr(report_module,"_cerai_ps3_report_installed",False):return
    previous_metrics=report_module._eye_metrics;previous_findings=report_module._findings
    def metrics(eye,locale="en"):
        rows=list(previous_metrics(eye,locale));p=eye.get("ps3") or {}
        if not p.get("applicable"):return rows
        tr=lambda x:report_module.translate_text(x,locale);m=p.get("moderate_count");h=p.get("high_count");inter=p.get("inter_eye_score")
        rows.extend([(tr("PS3 / classification"),tr(f"{m} moderate / {h} high — {_overall(p)}")),(tr("PS3 procedure disposition"),tr(_procedure_summary(p))),(tr("PS3 inter-eye asymmetry score"),tr("Not evaluated" if inter is None else f"{inter}/5")),(tr("PS3 SRAX (authoritative Front-map state)"),tr(_stored_srax_text(p)))])
        return rows
    def findings(eye,locale="en"):
        groups=list(previous_findings(eye,locale));p=eye.get("ps3") or {}
        if not p.get("applicable"):return groups
        tr=lambda x:report_module.translate_text(x,locale);interpret=[tr(x) for x in _interpretation(p)];audit=[tr(x) for x in _finding_lines(p)];review=[tr(str(x)) for x in p.get("review_notes") or []]
        if interpret:groups.append((tr("PS3 summary and interpretation"),interpret))
        if audit:groups.append((tr("PS3 criteria audit"),audit))
        if review:groups.append((tr("PS3 surgeon review required"),review))
        return groups
    report_module._eye_metrics=metrics;report_module._findings=findings;report_module._cerai_ps3_report_installed=True
