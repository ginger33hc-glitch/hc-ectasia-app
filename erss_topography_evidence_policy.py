"""Evidence gate for canonical Randleman/ERSS topography scoring.

ERSS topography uses two independent evidence channels:
1) the signed Topometric I-S value; and
2) SRAX measured only from the Axial/Sagittal Curvature (Front) map.

SRAX is never reconstructed from KISA, Kmax, I-S, astigmatism, BAD-D, or any
other surrogate. If the Front-map SRAX cannot be determined, explicit surgeon
confirmation of whether SRAX is >20 degrees is required.
"""

core = None
_previous_scoring_morphology = None
_previous_required_tomography_missing = None
_previous_assess_eye = None
_prior_assess_eye = None

VALID_I_S_STATUSES = {"CONFIDENT", "SURGEON_CONFIRMED"}
_CATEGORY_RANK = {
    "NORMAL_SYMMETRIC": 0,
    "ASYMMETRIC_BOWTIE": 1,
    "INFERIOR_STEEPENING_SRA": 3,
    "ABNORMAL_ECTATIC": 4,
}


def _field_conflict(eye, field):
    return any(
        str(item).split(":", 1)[0].strip() == field
        for item in (eye.get("data_conflicts") or [])
    )


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


def _prepared_eye(eye, plan):
    prepared = dict(eye)
    prepared["_erss_i_s_gate_required"] = (plan or {}).get("procedure") == "LASIK"
    manual_i_s = (plan or {}).get("surgeon_I_S_D")
    prepared["_surgeon_I_S_invalid"] = manual_i_s is not None and not core.is_number(manual_i_s)

    if core.is_number(manual_i_s):
        prepared["I_S"] = float(manual_i_s)
        prepared["I_S_status"] = "SURGEON_CONFIRMED"
        prepared["I_S_source"] = "SURGEON_ENTRY"
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
    if value < -0.50:
        return "ASYMMETRIC_BOWTIE", f"Canonical signed I-S {value:+.2f} D is < -0.50 D; negative ABT has no lower limit."
    if -0.50 <= value <= 0.50:
        return "NORMAL_SYMMETRIC", f"Canonical signed I-S {value:+.2f} D is within -0.50 to +0.50 D."
    return None, f"Canonical signed I-S {value:+.2f} D lies outside the currently defined CER-AI I-S bands."


def _surgeon_confirmed_srax(eye):
    value = str(eye.get("srax") or "").upper()
    if value not in {"YES", "NO"}:
        return None
    provenance = (eye.get("field_provenance") or {}).get("srax") or []
    if any(str(item.get("source") or "").upper() == "SURGEON_CONFIRMED" for item in provenance if isinstance(item, dict)):
        return value
    return None


def _front_map_srax(eye):
    """Return (status, degrees, source, evidence) for source-locked SRAX.

    Numeric srax_deg is accepted only under the production extraction contract,
    which permits that field solely from the Axial/Sagittal Curvature (Front)
    map. A categorical image read without a numeric angle is not sufficient;
    the surgeon is asked instead.
    """
    if _field_conflict(eye, "srax_deg") or _field_conflict(eye, "srax"):
        return None, None, None, "Conflicting SRAX readings were not used."

    value = eye.get("srax_deg")
    if core.is_number(value):
        degrees = float(value)
        if 0.0 <= degrees <= 90.0:
            status = "YES" if degrees > 20.0 else "NO"
            return (
                status,
                degrees,
                "AXIAL_SAGITTAL_CURVATURE_FRONT",
                f"Front-map SRAX {degrees:.1f}°; criterion is strictly >20°.",
            )
        return None, None, None, f"SRAX {degrees:g}° is outside the accepted 0-90° skew range and was not used."

    confirmed = _surgeon_confirmed_srax(eye)
    if confirmed:
        return (
            confirmed,
            None,
            "SURGEON_CONFIRMED_FRONT_MAP_REVIEW",
            f"Surgeon confirmed SRAX {'>20°' if confirmed == 'YES' else 'is not >20°'} from the Axial/Sagittal Curvature (Front) map.",
        )

    return None, None, None, "SRAX could not be determined from the Axial/Sagittal Curvature (Front) map."


def scoring_morphology_with_i_s_evidence_gate(eye):
    """Return one mutually exclusive Randleman topography category.

    Both signed I-S and source-locked SRAX must be resolved. SRAX >20° is an
    independent 3-point topography criterion. The higher applicable single
    category wins; categories are never added together.
    """
    if not eye.get("_erss_i_s_gate_required"):
        return _previous_scoring_morphology(eye)

    evidence = []
    candidates = []

    i_s_category, i_s_evidence = _i_s_category(eye)
    if i_s_evidence:
        evidence.append(i_s_evidence)
    if i_s_category:
        candidates.append((i_s_category, "CANONICAL_SIGNED_I_S"))

    srax_status, srax_deg, srax_source, srax_evidence = _front_map_srax(eye)
    evidence.append(srax_evidence)
    if srax_status == "YES":
        candidates.append(("INFERIOR_STEEPENING_SRA", "FRONT_MAP_SRAX_GT_20"))
        evidence.append("Randleman SRAX criterion met: Front-map skew is >20°.")
    elif srax_status == "NO":
        evidence.append("Randleman SRAX >20° criterion is not met.")

    if i_s_category is None or srax_status is None:
        if _i_s_status(eye) == "CONFLICT":
            evidence.append("Conflicting same-eye I-S readings were not used.")
        evidence.append("Randleman topography remains unscored until both signed I-S and Front-map SRAX status are resolved.")
        return {
            "category": "UNCERTAIN",
            "category_source": "UNRESOLVED_ERSS_TOPOGRAPHY_EVIDENCE",
            "srax_deg": srax_deg,
            "srax_status": srax_status,
            "srax_source": srax_source,
            "evidence": list(dict.fromkeys(evidence)),
        }

    category, source = max(candidates, key=lambda item: _CATEGORY_RANK[item[0]])
    evidence.append(
        "Highest applicable single Randleman topography category selected from signed I-S and Front-map SRAX; categories are never added together."
    )
    return {
        "category": category,
        "category_source": source,
        "srax_deg": srax_deg,
        "srax_status": srax_status,
        "srax_source": srax_source,
        "evidence": list(dict.fromkeys(evidence)),
    }


def required_tomography_missing_with_i_s(eye):
    missing = [
        item for item in _previous_required_tomography_missing(eye)
        if not any(
            token in str(item).lower()
            for token in (
                "morphology", "topography category", "asymmetric bow", "inferior steep"
            )
        )
    ]
    if not eye.get("_erss_i_s_gate_required"):
        return missing

    if not (core.is_number(eye.get("I_S")) and _i_s_status(eye) in VALID_I_S_STATUSES):
        missing.append("usable signed I-S value for numeric Randleman topography scoring")
    srax_status, _, _, _ = _front_map_srax(eye)
    if srax_status is None:
        missing.append("SRAX >20° confirmation from the Axial/Sagittal Curvature (Front) map")
    return list(dict.fromkeys(missing))


def assess_eye_with_i_s_evidence(eye, plan, age, patient_modifiers):
    if core.tri((plan or {}).get("prior")) == "yes":
        assessor = _prior_assess_eye or _previous_assess_eye
        return assessor(eye, plan, age, patient_modifiers)

    if (plan or {}).get("procedure") != "LASIK":
        return _previous_assess_eye(eye, plan, age, patient_modifiers)

    working_eye = _prepared_eye(eye, plan or {})
    # Retire legacy morphology channels but preserve SRAX/srax_deg because they
    # are now an explicit independent source-locked ERSS component.
    working_eye["morphology"] = "UNCERTAIN"
    working_eye["morphology_confidence"] = "UNREADABLE"
    working_eye["morphology_evidence"] = []
    working_eye["asymmetric_bow_tie"] = "UNCERTAIN"
    working_eye["inferior_opposite_steepening_D"] = None

    result = _previous_assess_eye(working_eye, plan, age, patient_modifiers)
    validated = scoring_morphology_with_i_s_evidence_gate(working_eye)
    i_s_status = _i_s_status(working_eye)
    srax_status = validated.get("srax_status")
    evidence_record = {
        "I_S_D": working_eye.get("I_S") if core.is_number(working_eye.get("I_S")) else None,
        "I_S_status": i_s_status,
        "I_S_source": _i_s_source(working_eye),
        "SRAX_deg": validated.get("srax_deg"),
        "SRAX_status": srax_status or "UNRESOLVED",
        "SRAX_source": validated.get("srax_source"),
        "validated_category": validated.get("category", "UNCERTAIN"),
        "category_source": validated.get("category_source", "UNRESOLVED_ERSS_TOPOGRAPHY_EVIDENCE"),
        "single_category_rule": "Highest applicable category from signed I-S and Front-map SRAX; categories are never added.",
        "needs_surgeon_I_S": not (core.is_number(working_eye.get("I_S")) and i_s_status in VALID_I_S_STATUSES),
        "needs_surgeon_SRAX": srax_status is None,
    }
    result["erss_topography_evidence"] = evidence_record
    result.setdefault("values", {}).update({
        "I_S_D": evidence_record["I_S_D"],
        "I_S_status": evidence_record["I_S_status"],
        "I_S_source": evidence_record["I_S_source"],
        "SRAX_deg": evidence_record["SRAX_deg"],
        "SRAX_status": evidence_record["SRAX_status"],
        "SRAX_source": evidence_record["SRAX_source"],
    })

    if working_eye.get("_surgeon_I_S_invalid"):
        result.setdefault("missing", []).append("valid numeric surgeon-confirmed I-S value")
    result["missing"] = [
        item for item in dict.fromkeys(result.get("missing") or [])
        if not any(
            token in str(item).lower()
            for token in (
                "morphology", "topography category", "asymmetric bow", "inferior steep"
            )
        )
    ]
    return result


def install(runtime_core, prior_assess_eye=None) -> None:
    """Attach ERSS evidence gates explicitly and at most once."""
    global core
    global _previous_scoring_morphology
    global _previous_required_tomography_missing
    global _previous_assess_eye
    global _prior_assess_eye

    if getattr(runtime_core, "_erss_topography_evidence_policy_installed", False):
        return
    core = runtime_core
    _previous_scoring_morphology = runtime_core.scoring_morphology
    _previous_required_tomography_missing = runtime_core.required_tomography_missing
    _previous_assess_eye = runtime_core.assess_eye
    _prior_assess_eye = prior_assess_eye
    runtime_core.scoring_morphology = scoring_morphology_with_i_s_evidence_gate
    runtime_core.required_tomography_missing = required_tomography_missing_with_i_s
    runtime_core.assess_eye = assess_eye_with_i_s_evidence
    runtime_core._erss_topography_evidence_policy_installed = True
