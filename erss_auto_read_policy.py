"""Keep ERSS/Randleman morphology auto-reading independent from NICE.

ABT, SRAX/SRA and inferior steepening are image-derived ERSS/Randleman findings.
They must never be requested because NICE is incomplete. Surgeon confirmation is
reserved for genuinely unresolved ERSS morphology after the dedicated anterior-
curvature read.
"""

_previous_hc_engine = None


def _is_unresolved_erss(result):
    erss = result.get("randleman_erss") or {}
    category = erss.get("topography_category")
    if category in {"NORMAL_SYMMETRIC", "ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA", "ABNORMAL_ECTATIC"}:
        return False
    missing = set(erss.get("missing_erss_inputs") or [])
    return "topography" in missing or category in {None, "UNCERTAIN"}


def _clean_missing(result):
    cleaned = []
    for item in result.get("missing") or []:
        text = str(item)
        upper = text.upper()
        # NICE owns only K2, central pachymetry, posterior elevation and I-S.
        # Never relabel morphology terms as NICE requirements.
        if upper.startswith("NICE:") and any(term in upper for term in ("ABT", "ASYMMETRIC", "SRAX", "SRA", "INFERIOR STEEP", "TOPOGRAPHY", "MORPHOLOGY")):
            continue
        cleaned.append(item)
    result["missing"] = list(dict.fromkeys(cleaned))
    return result


def hc_engine_with_erss_auto_read(extracted, age, eye_plans, patient_modifiers, patient_metadata=None):
    decision = _previous_hc_engine(extracted, age, eye_plans, patient_modifiers, patient_metadata)
    for result in decision.get("eyes", []):
        _clean_missing(result)
        # Do not ask for surgeon topography when the dedicated image reader already
        # resolved the ERSS category. If unresolved, preserve the existing request.
        if not _is_unresolved_erss(result):
            result["missing"] = [
                item for item in result.get("missing") or []
                if not (
                    "topograph" in str(item).lower()
                    or "morphology" in str(item).lower()
                    or "asymmetric bow" in str(item).lower()
                    or "srax" in str(item).lower()
                    or "inferior steep" in str(item).lower()
                )
            ]
    return decision


def install(core) -> None:
    """Attach ERSS missing-field cleanup explicitly and at most once."""
    global _previous_hc_engine

    if getattr(core, "_erss_auto_read_policy_installed", False):
        return
    _previous_hc_engine = core.hc_engine
    core.hc_engine = hc_engine_with_erss_auto_read
    core._erss_auto_read_policy_installed = True
