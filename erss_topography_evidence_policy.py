"""Deterministic evidence gate for canonical Randleman/ERSS topography.

Recovery contract:
- General visual morphology is retired as a scoring pathway.
- Signed labeled/confirmed I-S supplies the numeric topography category.
- SRAX is a separate direct observation from Axial/Sagittal Curvature (Front).
- SRAX is positive only when strictly >20 degrees.
- No KISA/Kmax/I-S/astigmatism/BAD-D surrogate may derive SRAX.
- Unresolved SRAX stays unresolved and requires surgeon confirmation.
- This module validates evidence only; the existing point mapper and ERSS calculator
  remain the scoring authorities.
"""

core = None
_previous_scoring_morphology = None
_previous_required_tomography_missing = None
_previous_assess_eye = None

VALID_I_S_STATUSES = {"CONFIDENT", "SURGEON_CONFIRMED"}
_CATEGORY_RANK = {
    "NORMAL_SYMMETRIC": 0,
    "ASYMMETRIC_BOWTIE": 1,
    "INFERIOR_STEEPENING_SRA": 3,
    "ABNORMAL_ECTATIC": 4,
}
_SRAX_COMPLETION = "SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map"


def _field_conflict(eye, field):
    return any(str(item).split(":", 1)[0].strip() == field for item in (eye.get("data_conflicts") or []))


def _i_s_status(eye):
    if _field_conflict(eye, "I_S"):
        return "CONFLICT"
    explicit = eye.get("I_S_status")
    if explicit in {"CONFIDENT", "SURGEON_CONFIRMED", "CONFLICT", "UNREADABLE", "NOT_SHOWN"}:
        return explicit
    if core.is_number(eye.get("I_S")) and "I_S" in set(eye.get("table_verified_numeric_fields") or []):
        return "CONFIDENT"
    if core.is_number(eye.get("I_S")) and "I_S" in set(eye.get("surgeon_verified_numeric_fields") or []):
        return "SURGEON_CONFIRMED"
    return "UNREADABLE" if eye.get("I_S") is not None else "NOT_SHOWN"


def _i_s_source(eye):
    if _i_s_status(eye) == "SURGEON_CONFIRMED":
        return "SURGEON_ENTRY"
    provenance = (eye.get("field_provenance") or {}).get("I_S") or []
    if provenance or "I_S" in set(eye.get("table_verified_numeric_fields") or []):
        return "PENTACAM_LABELED_IS_INDEX"
    return None


def _i_s_category(eye):
    value = eye.get("I_S")
    if not (core.is_number(value) and _i_s_status(eye) in VALID_I_S_STATUSES):
        return None, "Signed I-S is unresolved."
    value = float(value)
    if value >= 1.40:
        return "ABNORMAL_ECTATIC", f"Signed I-S {value:+.2f} D is >= +1.40 D."
    if value > 1.00:
        return "INFERIOR_STEEPENING_SRA", f"Signed I-S {value:+.2f} D is > +1.00 and < +1.40 D."
    if value > 0.50:
        return "ASYMMETRIC_BOWTIE", f"Signed I-S {value:+.2f} D is > +0.50 and <= +1.00 D."
    if value < -0.50:
        return "ASYMMETRIC_BOWTIE", f"Signed I-S {value:+.2f} D is < -0.50 D; negative ABT has no lower limit."
    return "NORMAL_SYMMETRIC", f"Signed I-S {value:+.2f} D is within -0.50 to +0.50 D."


def _surgeon_srax_status(eye):
    status = str(eye.get("srax") or "").upper()
    if status not in {"YES", "NO"}:
        return None
    provenance = (eye.get("field_provenance") or {}).get("srax") or []
    confirmed = any(
        isinstance(item, dict) and str(item.get("source") or "").upper() == "SURGEON_CONFIRMED"
        for item in provenance
    )
    return status if confirmed else None


def _front_map_srax(eye):
    """Return only a direct Front-map or surgeon-confirmed SRAX observation."""
    if _field_conflict(eye, "srax_deg") or _field_conflict(eye, "srax"):
        return None, None, None, "Conflicting SRAX observations were not used."

    value = eye.get("srax_deg")
    source = str(eye.get("srax_source") or "").upper()
    direct_source = source in {
        "AXIAL_SAGITTAL_CURVATURE_FRONT",
        "PENTACAM_AXIAL_SAGITTAL_CURVATURE_FRONT",
    }
    if core.is_number(value) and direct_source:
        degrees = float(value)
        if 0.0 <= degrees <= 90.0:
            status = "YES" if degrees > 20.0 else "NO"
            return status, degrees, "AXIAL_SAGITTAL_CURVATURE_FRONT", (
                f"Direct Front-map SRAX {degrees:.1f}°; positive criterion is strictly >20°."
            )
        return None, None, None, f"Direct SRAX {degrees:g}° is outside the accepted 0-90° range."

    confirmed = _surgeon_srax_status(eye)
    if confirmed:
        return confirmed, None, "SURGEON_CONFIRMED_FRONT_MAP_REVIEW", (
            "Surgeon confirmed SRAX >20° from the Front map."
            if confirmed == "YES"
            else "Surgeon confirmed SRAX is not >20° from the Front map."
        )

    return None, None, None, "SRAX is unresolved on the Axial/Sagittal Curvature (Front) map."


def _prepared_eye(eye, plan):
    prepared = dict(eye)
    prepared["_erss_i_s_gate_required"] = (plan or {}).get("procedure") == "LASIK"
    manual_i_s = (plan or {}).get("surgeon_I_S_D")
    prepared["_surgeon_I_S_invalid"] = manual_i_s is not None and not core.is_number(manual_i_s)
    if core.is_number(manual_i_s):
        prepared["I_S"] = float(manual_i_s)
        prepared["I_S_status"] = "SURGEON_CONFIRMED"
        prepared["I_S_source"] = "SURGEON_ENTRY"
    # General morphology is deliberately not accepted as an alternate scoring input.
    return prepared


def scoring_morphology_with_i_s_evidence_gate(eye):
    if not eye.get("_erss_i_s_gate_required"):
        return _previous_scoring_morphology(eye)

    evidence = []
    i_s_category, i_s_evidence = _i_s_category(eye)
    evidence.append(i_s_evidence)
    srax_status, srax_deg, srax_source, srax_evidence = _front_map_srax(eye)
    evidence.append(srax_evidence)

    # Both channels must be resolved so a missing SRAX can never masquerade as normal.
    if i_s_category is None or srax_status is None:
        return {
            "category": "UNCERTAIN",
            "category_source": "UNRESOLVED_ERSS_TOPOGRAPHY_EVIDENCE",
            "srax_status": srax_status,
            "srax_deg": srax_deg,
            "srax_source": srax_source,
            "evidence": list(dict.fromkeys(evidence)),
        }

    candidates = [(i_s_category, "CANONICAL_SIGNED_I_S")]
    if srax_status == "YES":
        candidates.append(("INFERIOR_STEEPENING_SRA", "FRONT_MAP_SRAX_GT_20"))
    category, category_source = max(candidates, key=lambda item: _CATEGORY_RANK[item[0]])
    evidence.append("Highest applicable single topography category selected; I-S and SRAX points are never added.")
    return {
        "category": category,
        "category_source": category_source,
        "srax_status": srax_status,
        "srax_deg": srax_deg,
        "srax_source": srax_source,
        "evidence": list(dict.fromkeys(evidence)),
    }


def required_tomography_missing_with_i_s(eye):
    missing = list(_previous_required_tomography_missing(eye))
    if not eye.get("_erss_i_s_gate_required"):
        return missing
    if not (core.is_number(eye.get("I_S")) and _i_s_status(eye) in VALID_I_S_STATUSES):
        missing.append("usable signed I-S value for Randleman topography")
    srax_status, _, _, _ = _front_map_srax(eye)
    if srax_status is None:
        missing.append(_SRAX_COMPLETION)
    return list(dict.fromkeys(missing))


def assess_eye_with_i_s_evidence(eye, plan, age, patient_modifiers):
    if (plan or {}).get("procedure") != "LASIK":
        return _previous_assess_eye(eye, plan, age, patient_modifiers)
    working_eye = _prepared_eye(eye, plan or {})
    # Retire generic visual morphology so it cannot compete with signed I-S.
    working_eye["morphology"] = "UNCERTAIN"
    working_eye["morphology_confidence"] = "UNREADABLE"
    working_eye["morphology_evidence"] = []
    working_eye["asymmetric_bow_tie"] = "UNCERTAIN"
    working_eye["inferior_opposite_steepening_D"] = None

    result = _previous_assess_eye(working_eye, plan, age, patient_modifiers)
    validated = scoring_morphology_with_i_s_evidence_gate(working_eye)
    status = _i_s_status(working_eye)
    result["erss_topography_evidence"] = {
        "I_S_D": working_eye.get("I_S") if core.is_number(working_eye.get("I_S")) else None,
        "I_S_status": status,
        "I_S_source": _i_s_source(working_eye),
        "SRAX_deg": validated.get("srax_deg"),
        "SRAX_status": validated.get("srax_status") or "UNRESOLVED",
        "SRAX_source": validated.get("srax_source"),
        "validated_category": validated.get("category", "UNCERTAIN"),
        "category_source": validated.get("category_source", "UNRESOLVED"),
        "single_category_rule": "Highest applicable category from signed I-S and direct Front-map SRAX; never additive.",
        "needs_surgeon_I_S": not (core.is_number(working_eye.get("I_S")) and status in VALID_I_S_STATUSES),
        "needs_surgeon_SRAX": validated.get("srax_status") is None,
    }
    if working_eye.get("_surgeon_I_S_invalid"):
        result.setdefault("missing", []).append("valid numeric surgeon-confirmed I-S value")
    result["missing"] = list(dict.fromkeys(result.get("missing") or []))
    return result


def install(runtime_core) -> None:
    global core, _previous_scoring_morphology, _previous_required_tomography_missing, _previous_assess_eye
    if getattr(runtime_core, "_erss_topography_evidence_policy_installed", False):
        return
    core = runtime_core
    _previous_scoring_morphology = runtime_core.scoring_morphology
    _previous_required_tomography_missing = runtime_core.required_tomography_missing
    _previous_assess_eye = runtime_core.assess_eye
    runtime_core.scoring_morphology = scoring_morphology_with_i_s_evidence_gate
    runtime_core.required_tomography_missing = required_tomography_missing_with_i_s
    runtime_core.assess_eye = assess_eye_with_i_s_evidence
    runtime_core._erss_topography_evidence_policy_installed = True
