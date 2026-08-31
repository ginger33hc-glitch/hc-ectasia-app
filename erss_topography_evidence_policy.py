"""Evidence gate for the existing Randleman/ERSS topography scorer.

This module deliberately owns no point table and calculates no ERSS total.  It only
validates the anterior-topography evidence passed to the canonical
``scoring_morphology`` function.  The existing ``lasik_topography_points`` mapping and
the BAD-independent five-row ERSS calculator remain the sole scoring authorities.
"""

import bootstrap


core = bootstrap.core
_previous_scoring_morphology = core.scoring_morphology
_previous_required_tomography_missing = core.required_tomography_missing
_previous_assess_eye = core.assess_eye

VALID_CATEGORIES = {
    "NORMAL_SYMMETRIC",
    "ASYMMETRIC_BOWTIE",
    "INFERIOR_STEEPENING_SRA",
    "ABNORMAL_ECTATIC",
}
VALID_I_S_STATUSES = {"CONFIDENT", "SURGEON_CONFIRMED"}


def _is_conflict(eye):
    return any(
        str(item).split(":", 1)[0].strip() == "I_S"
        for item in (eye.get("data_conflicts") or [])
    )


def _i_s_status(eye):
    if _is_conflict(eye):
        return "CONFLICT"
    explicit = eye.get("I_S_status")
    if explicit in {"CONFIDENT", "SURGEON_CONFIRMED", "CONFLICT", "UNREADABLE", "NOT_SHOWN"}:
        return explicit
    # Backward-compatible provenance for the existing strict extraction schema:
    # a numeric I-S is usable only when it came from its labeled Pentacam table.
    if core.is_number(eye.get("I_S")) and "I_S" in set(eye.get("table_verified_numeric_fields") or []):
        return "CONFIDENT"
    return "UNREADABLE" if eye.get("I_S") is not None else "NOT_SHOWN"


def _i_s_source(eye):
    if _i_s_status(eye) == "SURGEON_CONFIRMED":
        return "SURGEON_ENTRY"
    provenance = (eye.get("field_provenance") or {}).get("I_S") or []
    if provenance:
        return "PENTACAM_LABELED_IS_INDEX"
    if "I_S" in set(eye.get("table_verified_numeric_fields") or []):
        return "PENTACAM_LABELED_IS_INDEX"
    return None


def _prepared_eye(eye, plan):
    prepared = dict(eye)
    prepared["_erss_i_s_gate_required"] = (plan or {}).get("procedure") == "LASIK"
    manual_i_s = (plan or {}).get("surgeon_I_S_D")
    manual_category = (plan or {}).get("surgeon_topography_category")
    prepared["_surgeon_I_S_invalid"] = manual_i_s is not None and not core.is_number(manual_i_s)
    prepared["_surgeon_category_invalid"] = manual_category not in (None, "", *VALID_CATEGORIES)

    if core.is_number(manual_i_s):
        prepared["I_S"] = float(manual_i_s)
        prepared["I_S_status"] = "SURGEON_CONFIRMED"
        prepared["I_S_source"] = "SURGEON_ENTRY"
    if manual_category in VALID_CATEGORIES:
        prepared["surgeon_topography_category"] = manual_category
        prepared["surgeon_topography_category_status"] = "SURGEON_CONFIRMED"
    return prepared


_CATEGORY_RANK = {
    "NORMAL_SYMMETRIC": 0,
    "ASYMMETRIC_BOWTIE": 1,
    "INFERIOR_STEEPENING_SRA": 3,
    "ABNORMAL_ECTATIC": 4,
}


def _numeric_category(eye):
    """Return a category only when a published numeric pattern criterion is usable."""
    i_s = eye.get("I_S")
    i_s_usable = core.is_number(i_s) and _i_s_status(eye) in VALID_I_S_STATUSES
    srax = eye.get("srax_deg")
    opposite = eye.get("inferior_opposite_steepening_D")

    if i_s_usable and float(i_s) >= 1.4:
        return "ABNORMAL_ECTATIC", "Labeled/confirmed I-S is >=1.4 D."
    if core.is_number(srax) and float(srax) >= 20.0:
        return "INFERIOR_STEEPENING_SRA", "Documented SRA/SRAX is >=20 degrees."
    if (
        core.is_number(opposite)
        and float(opposite) >= 1.0
        and i_s_usable
        and float(i_s) < 1.4
    ):
        return (
            "INFERIOR_STEEPENING_SRA",
            "Documented inferior-versus-opposite steepening is >=1.0 D with I-S <1.4 D.",
        )
    if (
        core.is_number(opposite)
        and 0.5 < float(opposite) < 1.0
        and not (core.is_number(srax) and float(srax) >= 20.0)
    ):
        return (
            "ASYMMETRIC_BOWTIE",
            "Documented opposite-region asymmetry is >0.5 D and <1.0 D without qualifying SRA/SRAX.",
        )
    return None, None


def _high_confidence_map_category(eye):
    category = eye.get("morphology")
    if (
        eye.get("erss_source_read") == "DEDICATED_CURVATURE_PASS"
        and eye.get("anterior_curvature_map_visible") == "YES"
        and eye.get("morphology_confidence") == "HIGH"
        and category in VALID_CATEGORIES
    ):
        return category
    return None


def scoring_morphology_with_i_s_evidence_gate(eye):
    """Return one validated category to the existing point mapper.

    Categories are mutually exclusive.  No points are assigned here.
    """
    if not eye.get("_erss_i_s_gate_required"):
        return _previous_scoring_morphology(eye)

    evidence = list(eye.get("morphology_evidence") or [])
    numeric_category, numeric_evidence = _numeric_category(eye)
    map_category = _high_confidence_map_category(eye)
    surgeon_category = eye.get("surgeon_topography_category")

    candidates = []
    if numeric_category:
        candidates.append((numeric_category, "AUTOMATIC_NUMERIC_EVIDENCE"))
        evidence.append(numeric_evidence)
    if map_category:
        candidates.append((map_category, "AUTOMATIC_HIGH_CONFIDENCE_MAP_EVIDENCE"))
        evidence.append(
            "Dedicated reader found a HIGH-confidence category on the complete anterior curvature map; no BAD/BAD-D field was used."
        )
    if surgeon_category in VALID_CATEGORIES:
        candidates.append((surgeon_category, "SURGEON_CONFIRMED"))
        evidence.append("Randleman anterior-topography category was explicitly confirmed by the surgeon.")

    if not candidates:
        confidence = eye.get("morphology_confidence") or "UNSPECIFIED"
        evidence.append(
            f"Randleman topography remains unscored: no qualifying numeric criterion, HIGH-confidence dedicated map category, or surgeon-confirmed category is available (map confidence: {confidence})."
        )
        if _i_s_status(eye) == "CONFLICT":
            evidence.append("Conflicting same-eye I-S readings were not used.")
        return {"category": "UNCERTAIN", "category_source": "UNRESOLVED", "evidence": list(dict.fromkeys(evidence))}

    category, source = max(candidates, key=lambda item: _CATEGORY_RANK[item[0]])
    evidence.append(
        "Highest applicable single Randleman topography category selected; ABT and inferior-steepening/SRA points are never added."
    )
    return {"category": category, "category_source": source, "evidence": list(dict.fromkeys(evidence))}


def required_tomography_missing_with_i_s(eye):
    missing = list(_previous_required_tomography_missing(eye))
    if not eye.get("_erss_i_s_gate_required"):
        return missing
    validated = scoring_morphology_with_i_s_evidence_gate(eye).get("category")
    if validated == "UNCERTAIN":
        missing.append("surgeon-confirmed Randleman topography category when the dedicated anterior-map read is not HIGH confidence")
    return list(dict.fromkeys(missing))


def assess_eye_with_i_s_evidence(eye, plan, age, patient_modifiers):
    if (plan or {}).get("procedure") != "LASIK":
        return _previous_assess_eye(eye, plan, age, patient_modifiers)
    working_eye = _prepared_eye(eye, plan or {})
    result = _previous_assess_eye(working_eye, plan, age, patient_modifiers)
    validated = scoring_morphology_with_i_s_evidence_gate(working_eye)
    status = _i_s_status(working_eye)
    evidence_record = {
        "I_S_D": working_eye.get("I_S") if core.is_number(working_eye.get("I_S")) else None,
        "I_S_status": status,
        "I_S_source": _i_s_source(working_eye),
        "image_category": working_eye.get("morphology", "UNCERTAIN"),
        "image_category_confidence": working_eye.get("morphology_confidence", "UNSPECIFIED"),
        "validated_category": validated.get("category", "UNCERTAIN"),
        "category_source": validated.get("category_source", "UNRESOLVED"),
        "single_category_rule": "Highest applicable category only; ABT and inferior-steepening/SRA points are never added.",
        "needs_surgeon_I_S": False,
        "needs_surgeon_category": validated.get("category") == "UNCERTAIN",
    }
    result["erss_topography_evidence"] = evidence_record
    result.setdefault("values", {}).update({
        "I_S_D": evidence_record["I_S_D"],
        "I_S_status": evidence_record["I_S_status"],
        "I_S_source": evidence_record["I_S_source"],
    })

    if working_eye.get("_surgeon_I_S_invalid"):
        result.setdefault("missing", []).append("valid numeric surgeon-confirmed I-S value")
    if working_eye.get("_surgeon_category_invalid"):
        result.setdefault("missing", []).append("valid surgeon-confirmed Randleman topography category")
    result["missing"] = list(dict.fromkeys(result.get("missing") or []))
    return result


core.scoring_morphology = scoring_morphology_with_i_s_evidence_gate
core.required_tomography_missing = required_tomography_missing_with_i_s
core.assess_eye = assess_eye_with_i_s_evidence
core._erss_topography_evidence_policy_installed = True

app = bootstrap.app
