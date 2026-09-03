"""Retire obsolete visual/pattern completion requests from CER-AI readiness.

General visual morphology remains retired. SRAX is no longer retired: when it
cannot be determined from the Axial/Sagittal Curvature (Front) map, the
readiness workflow must preserve the explicit surgeon question asking whether
SRAX/skewed axis is >20 degrees.

The legacy generic anterior/posterior elevation-at-thinnest fields are also not
active readiness inputs. NICE/PS3 elevation ownership is through the explicitly
labeled F. Ele.Th and B. Ele.Th boxes on the BAD/Belin-Ambrosio Display.
"""

_previous_hc_engine = None


_RETIRED_REQUEST_TERMS = (
    "morphology",
    "topography category",
    "topographic category",
    "asymmetric bow",
    "asymmetric_bow",
    "inferior steep",
    "anterior pattern",
    "posterior pattern",
    "anterior_pattern",
    "posterior_pattern",
)

_LEGACY_GENERIC_ELEVATION_FIELDS = (
    "anterior_elevation_thinnest_um",
    "posterior_elevation_thinnest_um",
)


def _is_retired_request(item):
    text = str(item).lower()
    # NICE never owns SRAX; preserve only the ERSS/Front-map SRAX completion
    # request introduced by the source-locked ERSS policy.
    if "nice" in text and "srax" in text:
        return True
    if any(term in text for term in _RETIRED_REQUEST_TERMS):
        return True
    return any(field in text for field in _LEGACY_GENERIC_ELEVATION_FIELDS)


def _clean_missing(result):
    """Remove retired morphology/generic-elevation requests while preserving SRAX."""
    result["missing"] = list(
        dict.fromkeys(
            item
            for item in result.get("missing") or []
            if not _is_retired_request(item)
        )
    )
    erss = result.get("randleman_erss")
    if isinstance(erss, dict):
        erss["missing_erss_inputs"] = [
            item
            for item in erss.get("missing_erss_inputs") or []
            if str(item).lower() not in {"topography", "morphology", "topography_category"}
            and not _is_retired_request(item)
        ]
    return result


def hc_engine_with_erss_auto_read(extracted, age, eye_plans, patient_modifiers, patient_metadata=None):
    decision = _previous_hc_engine(extracted, age, eye_plans, patient_modifiers, patient_metadata)
    for result in decision.get("eyes", []):
        _clean_missing(result)
    decision["critical_input_issues"] = [
        item
        for item in decision.get("critical_input_issues") or []
        if not _is_retired_request(item)
    ]
    return decision


def install(core) -> None:
    """Attach readiness cleanup explicitly and at most once."""
    global _previous_hc_engine

    if getattr(core, "_erss_auto_read_policy_installed", False):
        return
    _previous_hc_engine = core.hc_engine
    core.hc_engine = hc_engine_with_erss_auto_read
    core._erss_auto_read_policy_installed = True
