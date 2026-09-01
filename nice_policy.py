"""NICE input adapter and final restrictive-only policy, installed once at composition root.

The canonical ERSS/BAD scorers, their input rules, and LASIK fallback planner remain intact.
"""
from nice_scoring import score_nice, finite


POSTERIOR_PUPIL_EXTRACTION_RULE = """posterior_pupil_max_um is one dedicated NICE input only.
Use only the LOWER-RIGHT map explicitly titled 'Elevation (Back)' on a Pentacam 4 Maps
Refractive screen. Identify the central dashed pupil boundary, inspect every explicitly printed
signed elevation measurement whose measurement point lies inside that dashed boundary, and return
the highest positive printed value in micrometres. Do not use the upper-right Elevation (Front)
map, Corneal Thickness map, colour scale, a value outside the dashed boundary, elevation at the
thinnest point, or any other NICE/Pentacam parameter. The map must state BFS/Float with Dia 8.00 mm.
Never estimate from colour or interpolate an unprinted value."""


def posterior_candidate_is_acceptable(candidate):
    """Canonical source/geometry gate shared by NICE extraction passes."""
    return (
        candidate.get("posterior_status") == "CONFIDENT"
        and finite(candidate.get("posterior_pupil_max_um"))
        and candidate.get("posterior_pupil_max_um") > 0
        and candidate.get("posterior_reference") == "BFS_FLOAT"
        and candidate.get("bfs_diameter_mm") == 8
        and candidate.get("pupil_boundary_visible") is True
    )


def install_schema(core):
    props = {
        "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
        "central_pachy_um": {"type": ["number", "null"]},
        "central_status": {"type": "string", "enum": ["CONFIDENT", "UNREADABLE", "NOT_SHOWN"]},
        "posterior_pupil_max_um": {"type": ["number", "null"]},
        "posterior_status": {"type": "string", "enum": ["CONFIDENT", "UNREADABLE", "NOT_SHOWN"]},
        "posterior_reference": {"type": "string", "enum": ["BFS_FLOAT", "BFTE", "OTHER", "UNREADABLE"]},
        "bfs_diameter_mm": {"type": ["number", "null"]},
        "pupil_boundary_visible": {"type": "boolean"},
        "evidence": {"type": "string"},
    }
    core.SCHEMA["properties"]["nice_readings"] = {
        "type": "array", "items": {"type": "object", "additionalProperties": False,
        "properties": props, "required": list(props)}}
    core.SCHEMA["required"].append("nice_readings")
    core.PROMPT += f"""
NICE SEPARATE INPUT READING (do not calculate scores):
Return nice_readings only for Pentacam images with unambiguous OD/OS; otherwise [].
central_pachy_um: read the printed pachymetry value identified as 'Pupil Center' by the
plus-shaped (+) marker next to it. 'Pachy Vertex N.' remains acceptable when explicitly labeled
as the central/vertex pachymetry on that Pentacam screen. NEVER use 'Thinnest Locat.' or the
circle-marked thinnest value as central pachymetry. If the Pupil Center/central label, plus marker,
or digits are unreadable, use null and UNREADABLE.
{POSTERIOR_PUPIL_EXTRACTION_RULE}
Read the printed BFS/Float reference and diameter separately. Do not estimate any
number from colour or interpolate unprinted values. If the pupil boundary, sign,
measurement location or digits are ambiguous, return null and UNREADABLE.
Record the source label, raw value and location (relative to pupil) in evidence.
Never return zero to replace missing data. All negative values/no positive label
means unreadable for this positive-maximum field and requires surgeon confirmation.
"""


def attach_readings(merged, results):
    """Keep dedicated readings out of the legacy numeric reconciliation heuristics."""
    for eye in merged.get("eyes", []):
        candidates = []
        k2_readings = []
        for result in results:
            context = result.get("document_context") or {}
            if context.get("document_type") != "PENTACAM_TOPOGRAPHY":
                continue
            for raw_eye in result.get("eyes") or []:
                if raw_eye.get("eye") == eye.get("eye") and "K2_D" in (raw_eye.get("table_verified_numeric_fields") or []) and finite(raw_eye.get("K2_D")):
                    k2_readings.append(raw_eye["K2_D"])
            for reading in result.get("nice_readings") or []:
                if reading.get("eye") == eye.get("eye"):
                    candidates.append({**reading, "source_filename": context.get("source_filename")})
        eye["nice_candidates"] = candidates
        eye["nice_raw_k2_readings"] = k2_readings
    return merged


def _read(eye, plan, key, manual, status):
    if plan.get(manual) is not None:
        return plan[manual], "SURGEON_CONFIRMED", []
    candidates = []
    for candidate in eye.get("nice_candidates") or []:
        if candidate.get(status) != "CONFIDENT" or not finite(candidate.get(key)):
            continue
        if key == "posterior_pupil_max_um" and not posterior_candidate_is_acceptable(candidate):
            continue
        candidates.append(candidate)
    distinct = {candidate[key] for candidate in candidates}
    if len(distinct) != 1:
        return None, "CONFLICT" if distinct else "UNREADABLE", candidates
    return distinct.pop(), "PENTACAM_PRINTED", candidates


def evaluate(eye, plan):
    central, central_source, central_evidence = _read(eye, plan, "central_pachy_um", "surgeon_nice_central_um", "central_status")
    pe, pe_source, pe_evidence = _read(eye, plan, "posterior_pupil_max_um", "surgeon_nice_pe_um", "posterior_status")
    verified = set(eye.get("table_verified_numeric_fields") or []) | set(eye.get("surgeon_verified_numeric_fields") or [])
    conflicts = {str(x).split(":", 1)[0].strip() for x in eye.get("data_conflicts") or []}
    k2 = eye.get("K2_D") if "K2_D" in verified and "K2_D" not in conflicts else None
    # Legacy merge tolerances must never silently reconcile across a NICE boundary.
    if "K2_D" not in (eye.get("surgeon_verified_numeric_fields") or []):
        bands = {score_nice(value, 550, 8, .5)["rows"].get("K2") for value in eye.get("nice_raw_k2_readings") or []}
        if len(bands) > 1:
            k2 = None
    i_s = eye.get("I_S") if "I_S" in verified and "I_S" not in conflicts else None
    if plan.get("surgeon_I_S_D") is not None:
        i_s = plan["surgeon_I_S_D"]
    result = score_nice(k2, central, pe, i_s)
    result["input_sources"] = {"central_pachy": central_source, "posterior_elevation": pe_source,
                               "K2": "SURGEON_CONFIRMED" if "K2_D" in (eye.get("surgeon_verified_numeric_fields") or []) else "PENTACAM_LABELED_K2",
                               "I_S": "SURGEON_CONFIRMED" if plan.get("surgeon_I_S_D") is not None else "PENTACAM_LABELED_IS"}
    result["evidence"] = {"central_pachy": central_evidence, "posterior_elevation": pe_evidence}
    result["evidence_notes"] = list(dict.fromkeys(
        f"{candidate.get('source_filename') or 'Pentacam'}: {candidate['evidence']}"
        for candidate in central_evidence + pe_evidence if candidate.get("evidence")))
    return result


def install(core):
    install_schema(core)
    previous = core.hc_engine

    def hc_engine_with_nice(extracted, age, eye_plans, patient_modifiers, patient_metadata=None):
        decision = previous(extracted, age, eye_plans, patient_modifiers, patient_metadata)
        source = {x.get("eye"): x for x in extracted.get("eyes", [])}
        for result in decision.get("eyes", []):
            plan = eye_plans.get(result["eye"], {})
            if result.get("status") == "POST-REFRACTIVE PATHWAY REQUIRED" or plan.get("prior") != "no":
                result["nice"] = {"total": None, "category": "NOT_APPLICABLE", "rows": {}, "missing": []}
                continue
            nice = evaluate(source.get(result["eye"], {}), plan)
            result["nice"] = nice
            result["bad_summary"] = {"value": source.get(result["eye"], {}).get("BAD_D"),
                                     "category": core.bad_classification(source.get(result["eye"], {}).get("BAD_D"), final=True)}
            if nice["missing"]:
                result.setdefault("missing", []).extend(f"NICE: {field}" for field in nice["missing"])
                result["status"] = core.combine_status(result["status"], "DATA INSUFFICIENT")
            elif nice["total"] >= 9:
                reason = f"CER-AI NICE hard stop: total {nice['total']} >=9 (LASIK and PRK)."
                result.setdefault("hard_stops", []).append(reason)
                result.setdefault("reasons", []).append(reason)
                result["status"] = core.combine_status(result["status"], "DO NOT PROCEED")
                result["action"] = "DO NOT PROCEED with corneal refractive surgery. NICE >=9."
            elif nice["total"] >= 5:
                result.setdefault("reasons", []).append(f"CER-AI NICE caution: total {nice['total']} is in 5-8 inclusive.")
                old_status = result["status"]
                result["status"] = core.combine_status(old_status, "CAUTION — STOP/DEFER")
                if result["status"] != old_status or old_status.startswith("CAUTION"):
                    result["action"] = "STOP/DEFER; reassess after at least 6 months. NICE 5-8 does not clear surgery."
            # The previous post-assessment planner must never survive a NICE stop.
            if result["status"] not in {"PASS", "PASS WITH CAUTION"}:
                result.pop("microkeratome_planning", None)
            decision["status"] = core.combine_status(decision["status"], result["status"])
        decision["version"] = f"software v{core.APP_VERSION} / CER-AI NICE and data-readiness policy"
        return decision

    core.hc_engine = hc_engine_with_nice
    core._hc_nice_installed = True
