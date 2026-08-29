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


def _automatic_numeric_support(eye, category):
    srax = eye.get("srax_deg")
    opposite = eye.get("inferior_opposite_steepening_D")
    if category == "INFERIOR_STEEPENING_SRA":
        return (
            (core.is_number(srax) and float(srax) >= 20.0)
            or (core.is_number(opposite) and float(opposite) >= 1.0)
        )
    if category == "ASYMMETRIC_BOWTIE":
        return (
            core.is_number(opposite)
            and 0.5 < float(opposite) < 1.0
            and not (core.is_number(srax) and float(srax) >= 20.0)
        )
    return True


def scoring_morphology_with_i_s_evidence_gate(eye):
    """Return one validated category to the existing point mapper.

    Categories are mutually exclusive.  No points are assigned here.
    """
    if not eye.get("_erss_i_s_gate_required"):
        return _previous_scoring_morphology(eye)

    evidence = list(eye.get("morphology_evidence") or [])
    i_s = eye.get("I_S")
    status = _i_s_status(eye)
    if not core.is_number(i_s) or status not in VALID_I_S_STATUSES:
        evidence.append(
            "Randleman topography not scored: a labeled Pentacam I-S value or surgeon-confirmed I-S value is required."
        )
        if status == "CONFLICT":
            evidence.append("Conflicting same-eye I-S readings require surgeon resolution; no conservative maximum was scored.")
        return {"category": "UNCERTAIN", "evidence": list(dict.fromkeys(evidence))}

    i_s = float(i_s)
    surgeon_category = eye.get("surgeon_topography_category")
    automatic = _previous_scoring_morphology(eye)
    automatic_category = automatic.get("category", "UNCERTAIN")
    evidence.extend(automatic.get("evidence") or [])

    # Highest applicable category wins; topography categories are never added together.
    if i_s >= 1.4 or automatic_category == "ABNORMAL_ECTATIC" or surgeon_category == "ABNORMAL_ECTATIC":
        evidence.append(
            "The I-S threshold or a confirmed abnormal/ectatic anterior pattern supports ABNORMAL_ECTATIC; this is the single highest applicable ERSS topography category."
        )
        return {"category": "ABNORMAL_ECTATIC", "evidence": list(dict.fromkeys(evidence))}

    srax = eye.get("srax_deg")
    opposite = eye.get("inferior_opposite_steepening_D")
    if (
        (core.is_number(srax) and float(srax) >= 20.0)
        or (core.is_number(opposite) and float(opposite) >= 1.0)
    ):
        evidence.append(
            "Inferior-steepening/SRA numeric support is present; this single category takes precedence over asymmetric bow-tie."
        )
        return {"category": "INFERIOR_STEEPENING_SRA", "evidence": list(dict.fromkeys(evidence))}

    if surgeon_category == "INFERIOR_STEEPENING_SRA":
        evidence.append("Inferior-steepening/SRA category confirmed by the surgeon; it takes precedence over ABT.")
        return {"category": "INFERIOR_STEEPENING_SRA", "evidence": list(dict.fromkeys(evidence))}

    if (
        (automatic_category == "ASYMMETRIC_BOWTIE" and _automatic_numeric_support(eye, automatic_category))
        or surgeon_category == "ASYMMETRIC_BOWTIE"
    ):
        evidence.append(
            "Validated asymmetric bow-tie evidence supplies the single ABT category; it is not added to another topography category."
        )
        return {"category": "ASYMMETRIC_BOWTIE", "evidence": list(dict.fromkeys(evidence))}

    if automatic_category == "NORMAL_SYMMETRIC" or surgeon_category == "NORMAL_SYMMETRIC":
        evidence.append("Normal/symmetric anterior topography is the single validated category.")
        return {"category": "NORMAL_SYMMETRIC", "evidence": list(dict.fromkeys(evidence))}

    category = automatic_category
    if category not in VALID_CATEGORIES:
        return {"category": "UNCERTAIN", "evidence": list(dict.fromkeys(evidence))}

    if category in {"ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA"} and not _automatic_numeric_support(eye, category):
        evidence.append(
            "Visual asymmetry alone was not scored: the published numeric support is unreadable, so surgeon category confirmation is required."
        )
        return {"category": "UNCERTAIN", "evidence": list(dict.fromkeys(evidence))}

    evidence.append(
        "I-S and anterior-curvature evidence passed the ERSS evidence gate; the category is forwarded to the existing point mapper."
    )
    return {"category": category, "evidence": list(dict.fromkeys(evidence))}


def required_tomography_missing_with_i_s(eye):
    missing = list(_previous_required_tomography_missing(eye))
    if not eye.get("_erss_i_s_gate_required"):
        return missing
    status = _i_s_status(eye)
    if not core.is_number(eye.get("I_S")) or status not in VALID_I_S_STATUSES:
        missing.append("labeled Pentacam I-S value or surgeon-confirmed I-S value for Randleman topography")

    raw_category = eye.get("morphology")
    validated = scoring_morphology_with_i_s_evidence_gate(eye).get("category")
    if raw_category in {"ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA"} and validated == "UNCERTAIN":
        missing.append("surgeon-confirmed Randleman topography category when numeric ABT/SRA support is unreadable")
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
        "validated_category": validated.get("category", "UNCERTAIN"),
        "category_source": (
            "SURGEON_CONFIRMED"
            if working_eye.get("surgeon_topography_category") == validated.get("category")
            else "AUTOMATIC_NUMERIC_AND_MAP_EVIDENCE"
            if validated.get("category") in VALID_CATEGORIES
            else "UNRESOLVED"
        ),
        "single_category_rule": "Highest applicable category only; ABT and inferior-steepening/SRA points are never added.",
        "needs_surgeon_I_S": status not in VALID_I_S_STATUSES,
        "needs_surgeon_category": (
            working_eye.get("morphology") in {"ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA"}
            and validated.get("category") == "UNCERTAIN"
        ),
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
