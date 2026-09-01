"""NICE input adapter and final restrictive-only policy, installed once at composition root.

The canonical ERSS/BAD scorers, their input rules, and LASIK fallback planner remain intact.
"""
from nice_scoring import score_nice, finite
from clinical_disposition import CAUTION, FAVORABLE_PLANNING_STATUSES, STOP_DEFER


B_ELE_TH_EXTRACTION_RULE = """B_Ele_Th_um is one dedicated NICE input only.
Use only the explicitly labeled 'B. Ele.Th' numeric box on the Pentacam BAD Display page.
Preserve the printed sign and value in micrometres. Never use an Elevation (Back) map, a pupil
boundary, BFS/Float values, BFTE, a colour scale, another elevation field, a neighboring number,
or a value calculated from any other parameter. If the B. Ele.Th label or attached digits are
unreadable, return null; no other source may substitute for this box."""


def b_ele_th_candidate_is_acceptable(candidate):
    """Canonical labeled-box gate shared by NICE extraction passes."""
    return (
        candidate.get("b_ele_th_status") == "CONFIDENT"
        and finite(candidate.get("B_Ele_Th_um"))
        and candidate.get("b_ele_th_landmark") == "B_ELE_TH_LABELED_BOX"
        and candidate.get("b_ele_th_page") == "BAD_DISPLAY"
    )


def install_schema(core):
    props = {
        "eye": {"type": "string", "enum": ["OD", "OS", "UNKNOWN"]},
        "central_pachy_um": {"type": ["number", "null"]},
        "central_status": {"type": "string", "enum": ["CONFIDENT", "UNREADABLE", "NOT_SHOWN"]},
        "central_landmark": {"type": "string", "enum": ["PUPIL_CENTER_PLUS", "OTHER", "UNREADABLE"]},
        "B_Ele_Th_um": {"type": ["number", "null"]},
        "b_ele_th_status": {"type": "string", "enum": ["CONFIDENT", "UNREADABLE", "NOT_SHOWN"]},
        "b_ele_th_landmark": {"type": "string", "enum": ["B_ELE_TH_LABELED_BOX", "OTHER", "UNREADABLE"]},
        "b_ele_th_page": {"type": "string", "enum": ["BAD_DISPLAY", "OTHER", "UNREADABLE"]},
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
plus-shaped (+) marker next to it. Set central_landmark=PUPIL_CENTER_PLUS only when both that
printed label and its plus marker are unambiguous. NEVER use 'Pachy Vertex N.', 'Thinnest Locat.',
the circle-marked thinnest value, or any number printed inside a corneal-thickness map as central
pachymetry. If the Pupil Center label, plus marker, or digits are unreadable, use null,
central_status=UNREADABLE and central_landmark=UNREADABLE.
{B_ELE_TH_EXTRACTION_RULE}
Set b_ele_th_landmark=B_ELE_TH_LABELED_BOX and b_ele_th_page=BAD_DISPLAY only when the printed
B. Ele.Th label, its attached value, and the BAD Display page identity are all unambiguous.
Otherwise use B_Ele_Th_um=null, b_ele_th_status=UNREADABLE, b_ele_th_landmark=UNREADABLE and
b_ele_th_page=UNREADABLE. Record the exact source label and raw signed value in evidence.
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
        if key == "central_pachy_um" and candidate.get("central_landmark") != "PUPIL_CENTER_PLUS":
            continue
        if key == "B_Ele_Th_um" and not b_ele_th_candidate_is_acceptable(candidate):
            continue
        candidates.append(candidate)
    # Pupil Center (+) is an exclusive printed-row source, not a consensus field.
    # Retain the first valid same-eye transcription and never create a cross-screen conflict.
    if key == "central_pachy_um" and candidates:
        return candidates[0][key], "PENTACAM_PRINTED", [candidates[0]]
    if key == "B_Ele_Th_um" and candidates:
        return candidates[0][key], "PENTACAM_BAD_DISPLAY_B_ELE_TH", [candidates[0]]
    distinct = {candidate[key] for candidate in candidates}
    if len(distinct) != 1:
        return None, "CONFLICT" if distinct else "UNREADABLE", candidates
    return distinct.pop(), "PENTACAM_PRINTED", candidates


def evaluate(eye, plan):
    central, central_source, central_evidence = _read(eye, plan, "central_pachy_um", "surgeon_nice_central_um", "central_status")
    pe, pe_source, pe_evidence = _read(eye, plan, "B_Ele_Th_um", "surgeon_nice_pe_um", "b_ele_th_status")
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
    result["input_sources"] = {"central_pachy": central_source, "B_Ele_Th": pe_source,
                               "K2": "SURGEON_CONFIRMED" if "K2_D" in (eye.get("surgeon_verified_numeric_fields") or []) else "PENTACAM_LABELED_K2",
                               "I_S": "SURGEON_CONFIRMED" if plan.get("surgeon_I_S_D") is not None else "PENTACAM_LABELED_IS"}
    result["evidence"] = {"central_pachy": central_evidence, "B_Ele_Th": pe_evidence}
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
                result["status"] = core.combine_status(result["status"], STOP_DEFER)
                result["action"] = "STOP-DEFER. NICE >=9 is a CER-AI hard stop."
            elif nice["total"] >= 5:
                result.setdefault("reasons", []).append(f"CER-AI NICE caution: total {nice['total']} is in 5-8 inclusive.")
                result["status"] = core.combine_status(result["status"], CAUTION)
                if result["status"] == CAUTION:
                    result["action"] = "CAUTION — surgeon review required; NICE 5-8 does not automatically defer surgery."
            if result["status"] not in FAVORABLE_PLANNING_STATUSES:
                result.pop("microkeratome_planning", None)
            decision["status"] = core.combine_status(decision["status"], result["status"])
        decision["version"] = f"software v{core.APP_VERSION} / CER-AI NICE and data-readiness policy"
        return decision

    core.hc_engine = hc_engine_with_nice
    core._hc_nice_installed = True
