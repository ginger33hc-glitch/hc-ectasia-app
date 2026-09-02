"""PS3 presentation adapter for CER-AI PDF/DOCX reports.

The report builders remain untouched. This module extends their shared metric
and finding seams so PDF and DOCX stay aligned. PS3 remains an independent
risk channel and is never added to Randleman/ERSS, BAD-D, or NICE.
"""


def _procedure_summary(ps3):
    disposition = ps3.get("disposition") or {}
    return (
        f"PRK {disposition.get('prk', 'NOT EVALUATED')} / "
        f"SMILE {disposition.get('smile', 'NOT EVALUATED')} / "
        f"LASIK {disposition.get('lasik', 'NOT EVALUATED')}"
    )


def _overall_classification(ps3):
    moderate = int(ps3.get("moderate_count") or 0)
    high = int(ps3.get("high_count") or 0)
    if high >= 1 or moderate >= 2:
        return "FAIL / DEFER"
    if moderate == 1:
        return "MODERATE"
    return "NO PS3 RISK FACTOR"


def _ps3_finding_lines(ps3):
    lines = []
    for finding in ps3.get("findings") or []:
        key = str(finding.get("key") or "PS3 item").replace("_", " ").title()
        status = str(finding.get("status") or "NOT_EVALUATED")
        detail = str(finding.get("detail") or "")
        lines.append(f"{key}: {status}" + (f" — {detail}" if detail else ""))
    return lines


def _triggering_findings(ps3):
    triggers = []
    for finding in ps3.get("findings") or []:
        status = str(finding.get("status") or "")
        if status not in {"MODERATE", "HIGH"}:
            continue
        key = str(finding.get("key") or "PS3 item").replace("_", " ").title()
        detail = str(finding.get("detail") or "")
        triggers.append(f"{key}: {status}" + (f" — {detail}" if detail else ""))
    return triggers


def _interpretation_lines(ps3):
    moderate = int(ps3.get("moderate_count") or 0)
    high = int(ps3.get("high_count") or 0)
    classification = _overall_classification(ps3)
    procedures = _procedure_summary(ps3)
    triggers = _triggering_findings(ps3)

    if classification == "NO PS3 RISK FACTOR":
        return [
            "PS3 classification: NO PS3 RISK FACTOR. No Moderate or High PS3 criterion was detected among evaluated components.",
            f"PS3 procedure disposition: {procedures}.",
        ]

    if classification == "MODERATE":
        lines = [
            "PS3 classification: MODERATE — exactly one Moderate PS3 risk factor was detected and no High-risk factor was detected.",
            "PS3 procedure rule: surface ablation/PRK and SMILE remain allowed by PS3; LASIK is DEFERRED by PS3.",
        ]
        lines.extend(f"Triggering PS3 criterion: {item}" for item in triggers)
        return lines

    lines = [
        f"PS3 classification: FAIL / DEFER — {moderate} Moderate and {high} High PS3 risk factor(s) detected.",
        "PS3 procedure rule: two or more Moderate factors, or any one High factor, DEFER PRK/surface ablation, SMILE, and LASIK under PS3.",
    ]
    lines.extend(f"Triggering PS3 criterion: {item}" for item in triggers)
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
            (tr("PS3 / classification"), tr(f"{moderate} moderate / {high} high — {_overall_classification(ps3)}")),
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
        interpretation = [tr(line) for line in _interpretation_lines(ps3)]
        ps3_lines = [tr(line) for line in _ps3_finding_lines(ps3)]
        review_lines = [tr(str(note)) for note in ps3.get("review_notes") or []]

        # These groups are intentionally appended after all existing findings so
        # PS3 appears as a distinct final report section, analogous to the
        # independent BAD-D / ERSS / NICE channels rather than being blended
        # into any of them.
        if interpretation:
            groups.append((tr("PS3 summary and interpretation"), interpretation))
        if ps3_lines:
            groups.append((tr("PS3 criteria audit"), ps3_lines))
        if review_lines:
            groups.append((tr("PS3 surgeon review required"), review_lines))
        return groups

    report_module._eye_metrics = eye_metrics_with_ps3
    report_module._findings = findings_with_ps3
    report_module._cerai_ps3_report_installed = True
