"""Readiness adapter for unresolved source-locked SRAX.

When SRAX cannot be measured from the Axial/Sagittal Curvature (Front) map,
CER-AI asks the surgeon one explicit binary question. The answer is stored as a
surgeon-confirmed `srax` measurement (YES/NO) and is then consumed by both ERSS
and PS3. No SRAX number is reconstructed from other Pentacam indices.
"""

_previous_request = None
_workflow = None


def _request_with_srax(eye, message, extracted):
    text = str(message).lower()
    if "srax" in text and "20" in text:
        if eye == "GLOBAL" and str(message)[:2] in {"OD", "OS"}:
            eye = str(message)[:2]
        return {
            "eye": eye,
            "label": "Is SRAX / skewed axis >20° on the Axial/Sagittal Curvature (Front) map?",
            "kind": "select",
            "key": "srax",
            "destination": "measurement",
            "options": ["YES", "NO"],
            "help": (
                "Inspect only the Axial/Sagittal Curvature (Front) map. "
                "Choose YES only when the skew amount is greater than 20°. "
                "Exact 20° is NO. Do not use KISA, Kmax, I-S, BAD-D, elevation, "
                "pachymetry, or another surrogate to answer this question."
            ),
        }
    return _previous_request(eye, message, extracted)


def install(assessment_workflow) -> None:
    global _previous_request
    global _workflow

    if getattr(assessment_workflow, "_cerai_srax_completion_installed", False):
        return
    _workflow = assessment_workflow
    assessment_workflow.PATTERNS["srax"] = ["YES", "NO"]
    _previous_request = assessment_workflow._request
    assessment_workflow._request = _request_with_srax
    assessment_workflow._cerai_srax_completion_installed = True
