"""Retire obsolete visual/pattern completion requests from CER-AI readiness.

General visual morphology remains retired. Morphology/geometry inspection is permitted only inside
the dedicated SRAX task on the Axial/Sagittal Curvature (Front) map. The resulting SRAX value/status
is shared by Randleman/ERSS and PS3. If SRAX cannot be resolved from that source, readiness must keep
the explicit surgeon confirmation request.

The legacy generic anterior/posterior elevation-at-thinnest fields are also not active readiness
inputs. NICE/PS3 elevation ownership is through the explicitly labeled F. Ele.Th and B. Ele.Th boxes
on the BAD/Belin-Ambrosio Display.
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

_ERSS_ROWS = ("topography", "RSB", "age", "pachymetry", "MRSE")
_ERSS_INCOMPLETE_PREFIX = "Randleman/ERSS score incomplete:"


def _is_retired_request(item):
    text = str(item).lower()
    # NICE never owns SRAX; preserve only the ERSS/Front-map SRAX completion
    # request introduced by the source-locked ERSS policy.
    if "nice" in text and "srax" in text:
        return True
    if any(term in text for term in _RETIRED_REQUEST_TERMS):
        return True
    return any(field in text for field in _LEGACY_GENERIC_ELEVATION_FIELDS)


def _lasik_result(result):
    return str((result.get("values") or {}).get("procedure") or "").upper() == "LASIK"


def _erss_missing_inputs(erss):
    rows = erss.get("rows") or {}
    declared = [str(item) for item in (erss.get("missing_erss_inputs") or [])]
    inferred = [name for name in _ERSS_ROWS if rows.get(name) is None]
    return list(dict.fromkeys(declared + inferred))


def _clean_missing(result):
    """Remove retired generic morphology requests, never canonical ERSS requirements."""
    cleaned = [
        item
        for item in result.get("missing") or []
        if not _is_retired_request(item)
        and not str(item).startswith(_ERSS_INCOMPLETE_PREFIX)
    ]

    erss = result.get("randleman_erss")
    if isinstance(erss, dict):
        # Do NOT delete canonical "topography" from missing_erss_inputs. That old cleanup
        # could make an unresolved SRAX/I-S topography row disappear while total stayed None,
        # allowing a report to be produced without a Randleman score.
        missing_inputs = [
            item
            for item in _erss_missing_inputs(erss)
            if not _is_retired_request(item)
            or str(item).lower() == "topography"
        ]
        erss["missing_erss_inputs"] = missing_inputs

        if _lasik_result(result) and erss.get("total") is None:
            label = ", ".join(missing_inputs) if missing_inputs else "unresolved required input"
            cleaned.append(f"{_ERSS_INCOMPLETE_PREFIX} {label}")

    result["missing"] = list(dict.fromkeys(cleaned))
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
