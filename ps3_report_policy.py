"""PS3 presentation adapter for CER-AI PDF/DOCX reports.

The report builders remain untouched. This module extends their shared metric
and finding seams so PDF and DOCX stay aligned.
"""


def _procedure_summary(ps3):
    disposition = ps3.get("disposition") or {}
    return (
        f"PRK {disposition.get('prk', 'NOT EVALUATED')} / "
        f"SMILE {disposition.get('smile', 'NOT EVALUATED')} / "
        f"LASIK {disposition.get('lasik', 'NOT EVALUATED')}"
    )


def _ps3_finding_lines(ps3):
    lines = []
    for finding in ps3.get("findings") or []:
        key = str(finding.get("key") or "PS3 item").replace("_", " ").title()
        status = str(finding.get("status") or "NOT_EVALUATED")
        detail = str(finding.get("detail") or "")
        lines.append(f"{key}: {status}" + (f" — {detail}" if detail else ""))
    return lines


def install(report_module):
    if getattr(report_module, "_cerai_ps3_report_installed", False):
        return

    previous_metrics = report_module._eye_metrics
    previous_findings = report_module._findings

    def eye_metrics_with_ps3(eye, locale="en"):
        rows = list(previous_metrics(eye, locale))
        ps3 = eye.get("ps3") or {}
        if not ps3.get("applicable"):
            return rows
        tr = lambda text: report_module.translate_text(text, locale)
        moderate = ps3.get("moderate_count")
        high = ps3.get("high_count")
        derived = ps3.get("derived_srax_deg")
        inter_eye = ps3.get("inter_eye_score")
        rows.extend([
            (tr("PS3 risk factors"), tr(f"{moderate} moderate / {high} high")),
            (tr("PS3 procedure disposition"), tr(_procedure_summary(ps3))),
            (tr("PS3 inter-eye asymmetry score"), tr("Not evaluated" if inter_eye is None else f"{inter_eye}/5")),
            (tr("PS3 derived SRAX"), tr("Not evaluated" if derived is None else f"{float(derived):.1f} degrees — derived, not directly reported by Pentacam")),
        ])
        return rows

    def findings_with_ps3(eye, locale="en"):
        groups = list(previous_findings(eye, locale))
        ps3 = eye.get("ps3") or {}
        if not ps3.get("applicable"):
            return groups
        tr = lambda text: report_module.translate_text(text, locale)
        ps3_lines = [tr(line) for line in _ps3_finding_lines(ps3)]
        review_lines = [tr(str(note)) for note in ps3.get("review_notes") or []]
        if ps3_lines:
            groups.append((tr("PS3 component assessment"), ps3_lines))
        if review_lines:
            groups.append((tr("PS3 surgeon review required"), review_lines))
        return groups

    report_module._eye_metrics = eye_metrics_with_ps3
    report_module._findings = findings_with_ps3
    report_module._cerai_ps3_report_installed = True
