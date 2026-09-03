"""Retire all visual-morphology completion requests from ERSS/Randleman.

CER-AI ERSS topography is numeric-only. Signed I-S and automatically derived
SRAX are the only active topography evidence. Visual morphology, asymmetric
bow-tie recognition, inferior-steepening morphology, or a surgeon-selected
"topography category" must never be requested as completion input.
"""

_previous_hc_engine = None


_RETIRED_MORPHOLOGY_TERMS = (
    "morphology",
    "topography category",
    "topographic category",
    "asymmetric bow",
    "asymmetric_bow",
    "srax",
    "inferior steep",
)


def _is_retired_morphology_request(item):
    text = str(item).lower()
    return any(term in text for term in _RETIRED_MORPHOLOGY_TERMS)


def _clean_missing(result):
    """Remove every retired visual/topography-category completion request."""
    result["missing"] = list(
        dict.fromkeys(
            item
            for item in result.get("missing") or []
            if not _is_retired_morphology_request(item)
        )
    )
    erss = result.get("randleman_erss")
    if isinstance(erss, dict):
        erss["missing_erss_inputs"] = [
            item
            for item in erss.get("missing_erss_inputs") or []
            if str(item).lower() not in {"topography", "morphology", "topography_category"}
            and not _is_retired_morphology_request(item)
        ]
    return result


def hc_engine_with_erss_auto_read(extracted, age, eye_plans, patient_modifiers, patient_metadata=None):
    decision = _previous_hc_engine(extracted, age, eye_plans, patient_modifiers, patient_metadata)
    for result in decision.get("eyes", []):
        _clean_missing(result)
    decision["critical_input_issues"] = [
        item
        for item in decision.get("critical_input_issues") or []
        if not _is_retired_morphology_request(item)
    ]
    return decision


def install(core) -> None:
    """Attach numeric-only ERSS missing-field cleanup explicitly and at most once."""
    global _previous_hc_engine

    if getattr(core, "_erss_auto_read_policy_installed", False):
        return
    _previous_hc_engine = core.hc_engine
    core.hc_engine = hc_engine_with_erss_auto_read
    core._erss_auto_read_policy_installed = True
