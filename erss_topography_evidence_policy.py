"""Evidence gate for the existing Randleman/ERSS topography scorer.

This module owns no point table and calculates no ERSS total. It validates the
anterior-topography evidence passed to the canonical scorer. Signed I-S and
CER-AI derived SRAX are numeric Randleman inputs; the existing point mapper
remains the sole scoring authority.
"""

from derived_srax import derive_srax_deg

core = None
_previous_scoring_morphology = None
_previous_required_tomography_missing = None
_previous_assess_eye = None

VALID_CATEGORIES = {
    "NORMAL_SYMMETRIC",
    "ASYMMETRIC_BOWTIE",
    "INFERIOR_STEEPENING_SRA",
    "ABNORMAL_ECTATIC",
}
VALID_I_S_STATUSES = {"CONFIDENT", "SURGEON_CONFIRMED"}
_CATEGORY_RANK = {
    "NORMAL_SYMMETRIC": 0,
    "ASYMMETRIC_BOWTIE": 1,
    "INFERIOR_STEEPENING_SRA": 3,
    "ABNORMAL_ECTATIC": 4,
}


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
    if core.is_number(eye.get("I_S")) and "I_S" in set(eye.get("table_verified_numeric_fields") or []):
        return "CONFIDENT"
    return "UNREADABLE" if eye.get("I_S") is not None else "NOT_SHOWN"


def _i_s_source(eye):
    if _i_s_status(eye) == "SURGEON_CONFIRMED":
        return "SURGEON_ENTRY"
    provenance = (eye.get("field_provenance") or {}).get("I_S") or []
    if provenance or "I_S" in set(eye.get("table_verified_numeric_fields") or []):
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


def _i_s_category(eye):
    i_s = eye.get("I_S")
    if not (core.is_number(i_s) and _i_s_status(eye) in VALID_I_S_STATUSES):
        return None, None

    value = float(i_s)
    if value >= 1.40:
        return "ABNORMAL_ECTATIC", f"Canonical signed I-S {value:+.2f} D is >= +1.40 D."
    if 1.00 < value < 1.40:
        return "INFERIOR_STEEPENING_SRA", f"Canonical signed I-S {value:+.2f} D is > +1.00 and < +1.40 D."
    if 0.50 < value <= 1.00:
        return "ASYMMETRIC_BOWTIE", f"Canonical signed I-S {value:+.2f} D is > +0.50 and <= +1.00 D."
    if -1.00 <= value < -0.50:
        return "ASYMMETRIC_BOWTIE", f"Canonical signed I-S {value:+.2f} D is >= -1.00 and < -0.50 D."
    if -0.50 <= value <= 0.50:
        return "NORMAL_SYMMETRIC", f"Canonical signed I-S {value:+.2f} D is within -0.50 to +0.50 D."
    return None, f"Canonical signed I-S {value:+.2f} D lies outside the currently defined CER-AI I-S bands."


def _derived_srax(eye):
    return derive_srax_deg(
        kisa_percent=eye.get("KISA"),
        kmax_d=eye.get("Kmax_D"),
        i_s_d=eye.get("I_S"),
        astig_d=eye.get("topographic_astig_D"),
    )


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
    """Return one mutually exclusive Randleman topography category.

    All independently valid evidence is considered together: signed I-S,
    derived SRAX, a HIGH-confidence dedicated anterior-map category, and an
    explicit surgeon-confirmed category. The highest applicable category wins;
    categories are never added together. This prevents reassuring numeric data
    from downgrading stronger definite ectatic morphology evidence.
    """
    if not eye.get("_erss_i_s_gate_required"):
        return _previous_scoring_morphology(eye)

    evidence = list(eye.get("morphology_evidence") or [])
    candidates = []

    i_s_category, i_s_evidence = _i_s_category(eye)
    if i_s_evidence:
        evidence.append(i_s_evidence)
    if i_s_category:
        candidates.append((i_s_category, "CANONICAL_SIGNED_I_S"))

    derived = _derived_srax(eye)
    if derived is not None:
        evidence.append(
            f"CER-AI derived SRAX {derived:.1f}° from KISA%, Kmax, I-S and topographic astigmatism; not directly reported by Pentacam."
        )
        if derived >= 20.0:
            candidates.append(("INFERIOR_STEEPENING_SRA", "DERIVED_SRAX"))
            evidence.append("ERSS SRA criterion met: derived SRAX >=20°.")

    map_category = _high_confidence_map_category(eye)
    if map_category:
        candidates.append((map_category, "AUTOMATIC_HIGH_CONFIDENCE_MAP_EVIDENCE"))
        evidence.append(
            "Dedicated reader found a HIGH-confidence category on the complete anterior curvature map; no BAD/BAD-D field was used."
        )

    surgeon_category = eye.get("surgeon_topography_category")
    if surgeon_category in VALID_CATEGORIES:
        candidates.append((surgeon_category, "SURGEON_CONFIRMED"))
        evidence.append("Randleman anterior-topography category was explicitly confirmed by the surgeon.")

    if not candidates:
        confidence = eye.get("morphology_confidence") or "UNSPECIFIED"
        evidence.append(
            f"Randleman topography remains unscored: no usable I-S/SRAX numeric criterion, HIGH-confidence dedicated map category, or surgeon-confirmed category is available (map confidence: {confidence})."
        )
        if _i_s_status(eye) == "CONFLICT":
            evidence.append("Conflicting same-eye I-S readings were not used.")
        return {
            "category": "UNCERTAIN",
            "category_source": "UNRESOLVED",
            "derived_srax_deg": derived,
            "evidence": list(dict.fromkeys(evidence)),
        }

    category, source = max(candidates, key=lambda item: _CATEGORY_RANK[item[0]])
    evidence.append(
        "Highest applicable single Randleman topography category selected across numeric, map, and surgeon-confirmed evidence; categories are never added together."
    )
    return {
        "category": category,
        "category_source": source,
        "derived_srax_deg": derived,
        "evidence": list(dict.fromkeys(evidence)),
    }


def required_tomography_missing_with_i_s(eye):
    missing = list(_previous_required_tomography_missing(eye))
    if not eye.get("_erss_i_s_gate_required"):
        return missing
    validated = scoring_morphology_with_i_s_evidence_gate(eye).get("category")
    if validated == "UNCERTAIN":
        missing.append("surgeon-confirmed Randleman topography category when numeric I-S/SRAX evidence and HIGH-confidence map evidence are unavailable")
    return list(dict.fromkeys(missing))


def assess_eye_with_i_s_evidence(eye, plan, age, patient_modifiers):
    # The previously composed clinical chain retains the base prior-surgery
    # short circuit. Keeping this leaf policy dependent only on its immediate
    # predecessor avoids a hidden bootstrap/runtime-assembly dependency.
    if core.tri((plan or {}).get("prior")) == "yes":
        return _previous_assess_eye(eye, plan, age, patient_modifiers)

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
        "derived_SRAX_deg": validated.get("derived_srax_deg"),
        "derived_SRAX_source": "KISA_KMAX_IS_TOPOGRAPHIC_ASTIG" if validated.get("derived_srax_deg") is not None else None,
        "image_category": working_eye.get("morphology", "UNCERTAIN"),
        "image_category_confidence": working_eye.get("morphology_confidence", "UNSPECIFIED"),
        "validated_category": validated.get("category", "UNCERTAIN"),
        "category_source": validated.get("category_source", "UNRESOLVED"),
        "single_category_rule": "Highest applicable Randleman topography category only; evidence categories are never added.",
        "needs_surgeon_I_S": False,
        "needs_surgeon_category": validated.get("category") == "UNCERTAIN",
    }
    result["erss_topography_evidence"] = evidence_record
    result.setdefault("values", {}).update({
        "I_S_D": evidence_record["I_S_D"],
        "I_S_status": evidence_record["I_S_status"],
        "I_S_source": evidence_record["I_S_source"],
        "derived_SRAX_deg": evidence_record["derived_SRAX_deg"],
    })

    if working_eye.get("_surgeon_I_S_invalid"):
        result.setdefault("missing", []).append("valid numeric surgeon-confirmed I-S value")
    if working_eye.get("_surgeon_category_invalid"):
        result.setdefault("missing", []).append("valid surgeon-confirmed Randleman topography category")
    result["missing"] = list(dict.fromkeys(result.get("missing") or []))
    return result


def install(runtime_core) -> None:
    """Attach ERSS evidence gates explicitly and at most once."""
    global core
    global _previous_scoring_morphology
    global _previous_required_tomography_missing
    global _previous_assess_eye

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
