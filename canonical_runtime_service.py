"""Direct case-level runtime for the CER-AI canonical clinical core.

This module is the authoritative clinical runtime boundary. It does not install
or wrap application functions. It receives already-reconciled extraction,
surgeon plans, and documented patient modifiers; resolves treatment-role source
precedence exactly once; maps each virgin eye into ``ClinicalCoreInput``; supplies
pure eligibility findings; calls the canonical clinical core once; and projects
that result into the stable case payload consumed by workflow/report/archive.

No Pentacam reading, clinical threshold table, score formula, or downstream
correction belongs here.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from canonical_input_adapter import (
    astigmatic_disparity_from_plan,
    build_clinical_core_input,
    resolve_case_plans,
)
from clinical_core.disposition import (
    ASSESSMENT_INCOMPLETE,
    CAUTION,
    PASS_WITH_CAUTION,
    PASS,
    STOP_DEFER,
    DecisionFinding,
    finalize_disposition,
)
from clinical_core.pipeline import evaluate_normalized_case
from clinical_core.planning import (
    LASIK_PLANS,
    LASIK_PLAN_SELECTION_RULE,
    PlanEvaluation,
    estimate_myopic_ablation_um,
    mmc_guidance,
    lasik_plan_definition,
    select_first_safe_lasik_plan,
)
from clinical_core.refraction import (
    HYPEROPIC,
    MIXED,
    MYOPIC,
    normalize_minus_cylinder,
    refractive_group,
)
from clinical_core.report_payload import build_report_payload
from clinical_core.version import CLINICAL_POLICY_VERSION, SRAX_POLICY_VERSION
from clinical_eligibility import evaluate_eligibility
from pentacam_canonical_source_lock import POLICY_VERSION as SOURCE_REGISTRY_VERSION
from planning.microkeratome import MicrokeratomePlanningInput, plan_microkeratome

POST_REFRACTIVE = "POST-REFRACTIVE PATHWAY REQUIRED"
SUPPORTED_PROCEDURES = frozenset({"LASIK", "PRK", "SMILE"})


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return _plain(asdict(value))
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _eye_by_name(extracted: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(item.get("eye")): item
        for item in extracted.get("eyes") or []
        if isinstance(item, Mapping) and item.get("eye") in {"OD", "OS"}
    }


def _hard_stop_reasons(safety: Mapping[str, Any]) -> list[str]:
    return [key for key, active in (safety.get("hard_stops") or {}).items() if active]


def _decision_reasons(core_result: Mapping[str, Any]) -> list[str]:
    final = core_result.get("final_disposition")
    if final is None:
        return []
    drivers = []
    for attr in ("stop_drivers", "incomplete_drivers", "caution_drivers"):
        for finding in getattr(final, attr, ()):
            text = finding.detail or finding.key
            if text not in drivers:
                drivers.append(text)
    return drivers


def _missing(core_result: Mapping[str, Any], eligibility_missing=()) -> list[str]:
    missing = []
    bad = core_result.get("bad_d") or {}
    if bad.get("classification") == "UNAVAILABLE":
        missing.append("BAD-D: BAD_D")
    erss = core_result.get("erss") or {}
    for key in erss.get("missing") or []:
        missing.append(f"Randleman: {key}")
    for field in (core_result.get("nice") or {}).get("missing") or []:
        missing.append(f"NICE: {field}")
    ps3 = core_result.get("ps3")
    if ps3 is not None:
        for key in getattr(ps3, "missing_keys", ()):
            missing.append(f"PS3: {key}")
    for key in (core_result.get("procedural_safety") or {}).get("missing") or []:
        missing.append(f"Safety: {key}")
    for key in eligibility_missing or ():
        missing.append(f"Clinical eligibility: {key}")
    return list(dict.fromkeys(missing))


def _values(core_result: Mapping[str, Any]) -> dict[str, Any]:
    safety = core_result.get("procedural_safety") or {}
    bad_result = (core_result.get("bad_d") or {}).get("result")
    values = {
        "LASIK_RSB_um": safety.get("LASIK_RSB_um"),
        "PRK_RST_um": safety.get("PRK_RST_um"),
        "LASIK_PTA_percent": safety.get("LASIK_PTA_percent"),
        "PRK_PTA_percent": safety.get("PRK_PTA_percent"),
        "estimated_final_Kmean_D": safety.get("estimated_final_Kmean_D"),
        "intended_refractive_group": core_result.get("intended_refractive_group"),
    }
    if bad_result is not None:
        values["BAD_D"] = getattr(bad_result, "final_d", None)
    return values


def _action(status: str) -> str:
    if status == STOP_DEFER:
        return "STOP-DEFER — do not proceed with elective corneal refractive surgery."
    if status == ASSESSMENT_INCOMPLETE:
        return "ASSESSMENT INCOMPLETE — complete decision-critical data before proceeding."
    if status in {CAUTION, PASS_WITH_CAUTION}:
        return f"{status} — surgeon review required."
    if status == PASS:
        return "PASS — final CER-AI combination criteria met; review individual findings."
    if status == POST_REFRACTIVE:
        return "Use the post-refractive-surgery pathway; virgin-cornea engine not applicable."
    return "Clinical review required."


def _report_payload(
    eye_name: str,
    source_eye: Mapping[str, Any],
    core_result: Mapping[str, Any],
    software_version: str | None,
    *,
    planning=None,
    microkeratome_planning=None,
    astigmatic_disparity=None,
) -> dict[str, Any]:
    return build_report_payload(
        core_result,
        eye=eye_name,
        software_version=software_version or "UNSPECIFIED",
        clinical_policy_version=CLINICAL_POLICY_VERSION,
        source_registry_version=SOURCE_REGISTRY_VERSION,
        srax_algorithm_version=SRAX_POLICY_VERSION,
        source_eye=source_eye,
        planning=planning,
        microkeratome_planning=microkeratome_planning,
        astigmatic_disparity=astigmatic_disparity,
        manual_corrections=source_eye.get("surgeon_corrections") or (),
    )


def _virgin_eye_payload(
    eye_name: str,
    source_eye: Mapping[str, Any],
    core_result: Mapping[str, Any],
    software_version: str | None,
    *,
    eligibility_missing=(),
    eligibility_notes=(),
    planning=None,
    microkeratome_planning=None,
    astigmatic_disparity=None,
) -> dict[str, Any]:
    safety = core_result.get("procedural_safety") or {}
    status = str(core_result.get("status") or ASSESSMENT_INCOMPLETE)
    bad = core_result.get("bad_d") or {}
    ps3 = core_result.get("ps3")
    payload = {
        "eye": eye_name,
        "status": status,
        "action": _action(status),
        "score": _plain(core_result.get("erss")),
        "bad_summary": {
            "value": getattr(bad.get("result"), "final_d", None),
            "category": bad.get("classification"),
        },
        "bad": _plain(bad.get("result")),
        "nice": _plain(core_result.get("nice")),
        "ps3": _plain(ps3),
        "astigmatic_disparity": _plain(astigmatic_disparity),
        "values": _values(core_result),
        "hard_stops": _hard_stop_reasons(safety),
        "reasons": _decision_reasons(core_result),
        "warnings": [],
        "clinical_modifiers": list(eligibility_notes or ()),
        "missing": _missing(core_result, eligibility_missing),
        "planning": _plain(planning or {}),
        "report_payload": _report_payload(
            eye_name,
            source_eye,
            core_result,
            software_version,
            planning=planning,
            microkeratome_planning=microkeratome_planning,
            astigmatic_disparity=astigmatic_disparity,
        ),
        "canonical_result": _plain(core_result),
    }
    if microkeratome_planning:
        payload["microkeratome_planning"] = _plain(microkeratome_planning)
    if (
        isinstance(astigmatic_disparity, Mapping)
        and astigmatic_disparity.get("status") == "VALIDATION_REQUIRED"
    ):
        payload["warnings"].append(astigmatic_disparity.get("detail"))
    return payload


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _plan_number(plan: Mapping[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = plan.get(key)
        if _finite_number(value):
            return float(value)
    return None


def _intended_refraction_from_input(inp):
    if not _finite_number(inp.intended_sphere_d) or not _finite_number(inp.intended_cylinder_d):
        return None
    cylinder = float(inp.intended_cylinder_d)
    axis = inp.intended_axis_deg
    if not _finite_number(axis):
        return None
    return normalize_minus_cylinder(inp.intended_sphere_d, cylinder, axis)


def _candidate_matches_actual_plan(plan: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    optical_zone = _plan_number(plan, "optical_zone_mm")
    transition_zone = _plan_number(plan, "transition_zone_mm")
    if optical_zone is None and transition_zone is None:
        return spec.get("name") == "Plan A"
    if optical_zone is None or transition_zone is None:
        return False
    return (
        abs(optical_zone - float(spec["optical_zone_mm"])) <= 1e-9
        and abs(transition_zone - float(spec["transition_zone_mm"])) <= 1e-9
    )


def _candidate_ablation(plan, spec, intended_group, intended_mrse_d):
    actual = _plan_number(plan, "max_ablation_um", "ablation_um")
    explicit_zones = _plan_number(plan, "optical_zone_mm") is not None
    if actual is not None and (
        _candidate_matches_actual_plan(plan, spec)
        or (not explicit_zones and spec["name"] == "Plan A")
    ):
        return actual, str(plan.get("ablation_source") or "ENTERED_OR_ACTUAL_PLAN_MAX_ABLATION")
    if intended_group == MYOPIC:
        estimated = estimate_myopic_ablation_um(intended_mrse_d, spec["optical_zone_mm"])
        if estimated is not None:
            return float(estimated), "CERAI_MYOPIC_ESTIMATE"
    return None, "ACTUAL_PLAN_MAX_ABLATION_REQUIRED"


def _candidate_rejection_reasons(core_result, eligibility_missing=()):
    reasons = _hard_stop_reasons(core_result.get("procedural_safety") or {})
    reasons.extend(
        reason for reason in _decision_reasons(core_result) if reason not in reasons
    )
    if reasons:
        return tuple(reasons)
    missing = _missing(core_result, eligibility_missing)
    if missing:
        return tuple(missing)
    return (str(core_result.get("status") or ASSESSMENT_INCOMPLETE),)


def _preplanning_gate(core_result: Mapping[str, Any]):
    """Finalize plan-independent findings before candidate evaluation.

    ERSS and procedural safety depend on RSB/ablation and therefore must be
    evaluated against each candidate by the canonical core. BAD-D, NICE, PS3,
    and eligibility are already plan-independent and may block planning here.
    """
    findings = tuple(
        finding
        for finding in core_result.get("decision_findings") or ()
        if getattr(finding, "key", None) not in {"randleman_erss", "procedural_safety"}
    )
    return finalize_disposition(findings)


def _evaluate_lasik_planning(source_eye, resolved_plan, *, age_years, extracted, eligibility):
    preliminary_plan = dict(resolved_plan)
    preliminary = build_clinical_core_input(
        source_eye,
        preliminary_plan,
        age_years=age_years,
        extracted=extracted,
        plan_already_resolved=True,
    )
    intended = _intended_refraction_from_input(preliminary)
    intended_group = refractive_group(intended) if intended is not None else None
    preliminary_core = evaluate_normalized_case(
        preliminary, external_findings=eligibility.findings
    )
    upstream = _preplanning_gate(preliminary_core)
    if upstream.status not in {PASS, PASS_WITH_CAUTION, CAUTION}:
        reasons = [
            finding.detail or finding.key
            for finding in (
                upstream.stop_drivers
                + upstream.incomplete_drivers
                + upstream.caution_drivers
            )
        ]
        planning = {
            "selected_plan": None,
            "sequence": [],
            "rejection_reasons": list(dict.fromkeys(reasons)),
            "mmc_guidance": "NOT_APPLICABLE",
        }
        return preliminary_core, preliminary_plan, planning
    if not _finite_number(resolved_plan.get("flap_um")):
        planning = {
            "selected_plan": None,
            "sequence": [],
            "rejection_reasons": [
                "LASIK flap selection required before automatic A/B/C planning."
            ],
            "mmc_guidance": "NOT_APPLICABLE",
        }
        return preliminary_core, dict(resolved_plan), planning

    candidate_meta = {}

    def evaluator(spec):
        candidate = dict(resolved_plan)
        candidate.update({
            "plan_name": spec["name"],
            "flap_um": float(spec["flap_um"]),
            "optical_zone_mm": float(spec["optical_zone_mm"]),
            "transition_zone_mm": float(spec["transition_zone_mm"]),
        })
        ablation, source = _candidate_ablation(
            resolved_plan, spec, intended_group, preliminary.intended_mrse_d
        )
        candidate["ablation_source"] = source
        if ablation is None:
            reason = (
                "Actual maximum ablation is required for this plan; the myopic linear "
                "estimate is not permitted for this refractive profile."
            )
            candidate_meta[spec["name"]] = {
                "candidate_plan": candidate,
                "status": ASSESSMENT_INCOMPLETE,
                "ablation_um": None,
                "ablation_source": source,
            }
            return PlanEvaluation(spec["name"], False, (reason,))
        candidate["ablation_um"] = float(ablation)
        candidate["max_ablation_um"] = float(ablation)
        normalized = build_clinical_core_input(
            source_eye,
            candidate,
            age_years=age_years,
            extracted=extracted,
            plan_already_resolved=True,
        )
        core_result = evaluate_normalized_case(
            normalized, external_findings=eligibility.findings
        )
        status = str(core_result.get("status") or ASSESSMENT_INCOMPLETE)
        safe = status in {PASS, PASS_WITH_CAUTION, CAUTION}
        reasons = () if safe else _candidate_rejection_reasons(core_result, eligibility.missing)
        candidate_meta[spec["name"]] = {
            "candidate_plan": candidate,
            "status": status,
            "ablation_um": float(ablation),
            "ablation_source": source,
        }
        return PlanEvaluation(spec["name"], safe, reasons, core_result)

    selected = select_first_safe_lasik_plan(evaluator)
    first_safe = next((item.plan for item in selected.sequence if item.safe), None)
    if selected.selected_plan != first_safe:
        raise RuntimeError(
            "Canonical LASIK planning priority violated: the selected plan must be "
            "the first safe candidate in Plan A → Plan B → Plan C order."
        )
    sequence = []
    for evaluation in selected.sequence:
        spec = next(item for item in LASIK_PLANS if item["name"] == evaluation.plan)
        meta = candidate_meta[evaluation.plan]
        sequence.append({
            "plan": evaluation.plan,
            "definition": lasik_plan_definition(evaluation.plan),
            "safe": evaluation.safe,
            "rejection_reasons": list(evaluation.rejection_reasons),
            "status": meta["status"],
            "flap_um": float(spec["flap_um"]),
            "optical_zone_mm": float(spec["optical_zone_mm"]),
            "transition_zone_mm": float(spec["transition_zone_mm"]),
            "ablation_um": meta["ablation_um"],
            "ablation_source": meta["ablation_source"],
        })
    planning = {
        "selected_plan": selected.selected_plan,
        "selected_plan_definition": lasik_plan_definition(selected.selected_plan),
        "selection_rule": LASIK_PLAN_SELECTION_RULE,
        "sequence": sequence,
        "rejection_reasons": [],
        "mmc_guidance": "NOT_APPLICABLE",
    }
    if selected.selected_plan is not None:
        evaluation = next(
            item for item in selected.sequence if item.plan == selected.selected_plan
        )
        return (
            evaluation.result,
            dict(candidate_meta[selected.selected_plan]["candidate_plan"]),
            planning,
        )
    evaluated = [item for item in selected.sequence if item.result is not None]
    core_result = (
        evaluated[-1].result
        if evaluated
        else preliminary_core
    )
    return core_result, dict(resolved_plan), planning


def _non_lasik_planning(procedure, normalized, core_result):
    return {
        "selected_plan": None,
        "sequence": [],
        "rejection_reasons": [],
        "mmc_guidance": mmc_guidance(
            procedure,
            core_result.get("intended_refractive_group"),
            normalized.intended_mrse_d,
        ),
    }


def _keratometry(source_eye: Mapping[str, Any]):
    k1 = _plan_number(source_eye, "ml7_k1_d")
    k2 = _plan_number(source_eye, "ml7_k2_d")
    if k1 is None or k2 is None:
        return None, None, None
    if k2 > k1:
        return k2, k1, _plan_number(source_eye, "K2_axis_deg")
    if k1 > k2:
        return k1, k2, _plan_number(source_eye, "K1_axis_deg")
    return k1, k2, None


def _horizontal_wtw(source_eye: Mapping[str, Any]):
    # HWTW may arrive either from the source-locked labeled Pentacam box or
    # from the explicit surgeon-completion path.  Both paths retain distinct
    # provenance; an unverified extraction remains prohibited.
    verified = set(source_eye.get("table_verified_numeric_fields") or ())
    surgeon_verified = set(source_eye.get("surgeon_verified_numeric_fields") or ())
    if "corneal_diameter_mm" not in verified | surgeon_verified:
        return None
    return _plan_number(source_eye, "corneal_diameter_mm")


def _microkeratome_planning(
    source_eye: Mapping[str, Any],
    effective_plan: Mapping[str, Any],
    core_result: Mapping[str, Any],
):
    """Build the ML7 record directly after favorable canonical LASIK planning."""
    status = str(core_result.get("status") or ASSESSMENT_INCOMPLETE)
    procedure = str(effective_plan.get("procedure") or "").strip().upper()
    if procedure != "LASIK" or status not in {PASS, PASS_WITH_CAUTION, CAUTION}:
        return None

    steep, flat, steep_axis = _keratometry(source_eye)
    intended_group = str(core_result.get("intended_refractive_group") or "").upper()
    result = plan_microkeratome(MicrokeratomePlanningInput(
        assessment_status=status,
        procedure=procedure,
        steepest_k_d=steep,
        flattest_k_d=flat,
        steep_axis_deg=steep_axis,
        w2w_mm=_horizontal_wtw(source_eye),
        pachy_um=_plan_number(source_eye, "pachy_thinnest_um"),
        t_zone_mm=_plan_number(effective_plan, "transition_zone_mm"),
        hyperopic=intended_group == HYPEROPIC,
        mixed_cylinder=intended_group == MIXED,
        hinge_site_lowest_k_d=None,
        superior_hinge_anatomically_possible=None,
        planned_flap_um=_plan_number(effective_plan, "flap_um"),
        max_ablation_um=_plan_number(effective_plan, "max_ablation_um", "ablation_um"),
    )).as_dict()
    issues = list(source_eye.get("planning_data_issues") or [])
    if issues:
        result["warnings"] = list(dict.fromkeys(
            list(result.get("warnings") or []) + issues
        ))
    result["status_independent"] = True
    return result


def _post_refractive_eye_payload(eye_name: str) -> dict[str, Any]:
    return {
        "eye": eye_name,
        "status": POST_REFRACTIVE,
        "action": _action(POST_REFRACTIVE),
        "score": None,
        "bad_summary": None,
        "bad": None,
        "nice": {"total": None, "category": "NOT_APPLICABLE", "rows": {}, "missing": []},
        "ps3": {"applicable": False, "reason": "Virgin-cornea PS3 pathway not applicable."},
        "values": {},
        "hard_stops": [],
        "reasons": ["Prior corneal refractive surgery requires a separate pathway."],
        "warnings": [],
        "clinical_modifiers": [],
        "missing": [],
        "report_payload": None,
        "canonical_result": None,
    }


def _overall_status(eyes: list[Mapping[str, Any]]) -> str:
    virgin = [eye for eye in eyes if eye.get("status") != POST_REFRACTIVE]
    if not virgin:
        return POST_REFRACTIVE
    findings = tuple(
        DecisionFinding(f"eye_{eye['eye']}", str(eye.get("status") or ASSESSMENT_INCOMPLETE))
        for eye in virgin
    )
    overall = finalize_disposition(findings).status
    if any(eye.get("status") == POST_REFRACTIVE for eye in eyes) and overall == PASS:
        return POST_REFRACTIVE
    return overall


def evaluate_case(
    extracted: Mapping[str, Any],
    age_years: Any,
    eye_plans: Mapping[str, Mapping[str, Any]],
    patient_modifiers: Mapping[str, Any],
    *,
    software_version: str | None = None,
) -> dict[str, Any]:
    """Evaluate requested procedures and failed-LASIK PRK alternatives through the canonical core."""
    if not isinstance(patient_modifiers, Mapping):
        raise TypeError("patient_modifiers must be a mapping")

    source = _eye_by_name(extracted)
    resolved_plans = resolve_case_plans(extracted, eye_plans)
    effective_plans = {eye: dict(plan) for eye, plan in resolved_plans.items()}
    results: list[dict[str, Any]] = []
    procedure_transitions = []

    for eye_name in ("OD", "OS"):
        eye = source.get(eye_name)
        plan = effective_plans.get(eye_name)
        if eye is None or not isinstance(plan, Mapping):
            continue
        prior = str(plan.get("prior") or "").strip().lower()
        if prior and prior != "no":
            results.append(_post_refractive_eye_payload(eye_name))
            continue
        procedure = str(plan.get("procedure") or "").strip().upper()
        if procedure not in SUPPORTED_PROCEDURES:
            results.append({
                "eye": eye_name,
                "status": ASSESSMENT_INCOMPLETE,
                "action": _action(ASSESSMENT_INCOMPLETE),
                "score": None,
                "bad_summary": None,
                "bad": None,
                "nice": {"total": None, "category": "INCOMPLETE", "rows": {}, "missing": []},
                "ps3": None,
                "values": {},
                "hard_stops": [],
                "reasons": ["Supported procedure is required."],
                "warnings": [],
                "clinical_modifiers": [],
                "missing": ["procedure"],
                "report_payload": None,
                "canonical_result": None,
            })
            continue

        eligibility = evaluate_eligibility(plan, patient_modifiers)
        normalized = build_clinical_core_input(
            eye, plan, age_years=age_years, extracted=extracted, plan_already_resolved=True,
        )
        intended = _intended_refraction_from_input(normalized)
        if (procedure in {"LASIK", "PRK"}
                and _plan_number(plan, "max_ablation_um", "ablation_um") is None
                and intended is not None and refractive_group(intended) == MYOPIC):
            estimated = estimate_myopic_ablation_um(
                normalized.intended_mrse_d, _plan_number(plan, "optical_zone_mm"),
            )
            if estimated is not None:
                plan = dict(plan, ablation_um=float(estimated), max_ablation_um=float(estimated),
                            ablation_source="CERAI_MYOPIC_ESTIMATE")
                effective_plans[eye_name] = plan
                normalized = build_clinical_core_input(
                    eye, plan, age_years=age_years, extracted=extracted, plan_already_resolved=True,
                )
        if procedure == "LASIK":
            core_result, effective_plan, planning = _evaluate_lasik_planning(
                eye,
                plan,
                age_years=age_years,
                extracted=extracted,
                eligibility=eligibility,
            )
            effective_plans[eye_name] = effective_plan
        else:
            core_result = evaluate_normalized_case(
                normalized,
                external_findings=eligibility.findings,
            )
            planning = _non_lasik_planning(procedure, normalized, core_result)
        lasik_assessment = None
        transition_message = None
        astigmatic_disparity = astigmatic_disparity_from_plan(eye, plan).as_dict()
        if procedure == "LASIK" and core_result.get("status") == STOP_DEFER:
            # Keep the complete original LASIK assessment; PRK starts from the requested
            # correction and optical zone, never the last rejected LASIK candidate.
            lasik_assessment = _virgin_eye_payload(
                eye_name, eye, core_result, software_version,
                eligibility_missing=eligibility.missing, eligibility_notes=eligibility.notes,
                planning=planning, microkeratome_planning=None,
                astigmatic_disparity=astigmatic_disparity,
            )
            prk_plan = dict(plan, procedure="PRK", flap_um=None)
            normalized = build_clinical_core_input(
                eye, prk_plan, age_years=age_years, extracted=extracted,
                plan_already_resolved=True,
            )
            core_result = evaluate_normalized_case(normalized, external_findings=eligibility.findings)
            planning = _non_lasik_planning("PRK", normalized, core_result)
            transition_message = f"{eye_name}: LASIK failed. Now evaluating PRK."
            planning["procedure_transition"] = transition_message
            planning["prior_lasik_status"] = STOP_DEFER
            planning["prior_lasik_reasons"] = list(lasik_assessment.get("reasons") or [])
            effective_plans[eye_name] = prk_plan
            procedure_transitions.append({"eye": eye_name, "from": "LASIK", "to": "PRK", "message": transition_message})
        microkeratome_planning = _microkeratome_planning(
            eye,
            effective_plans.get(eye_name) or plan,
            core_result,
        )
        results.append(_virgin_eye_payload(
            eye_name,
            eye,
            core_result,
            software_version,
            eligibility_missing=eligibility.missing,
            eligibility_notes=eligibility.notes,
            planning=planning,
            microkeratome_planning=microkeratome_planning,
            astigmatic_disparity=astigmatic_disparity,
        ))
        if lasik_assessment is not None:
            results[-1]["lasik_assessment"] = lasik_assessment
            results[-1]["warnings"].append(transition_message)

    overall_status = _overall_status(results) if results else ASSESSMENT_INCOMPLETE
    return {
        "status": overall_status,
        "action": _action(overall_status),
        "eyes": results,
        "effective_eye_plans": _plain(effective_plans),
        "procedure_transitions": procedure_transitions,
        "version": software_version,
        "policy_versions": {
            "clinical": CLINICAL_POLICY_VERSION,
            "source_registry": SOURCE_REGISTRY_VERSION,
            "srax": SRAX_POLICY_VERSION,
        },
        "engine": "CERAI_CANONICAL_CLINICAL_CORE",
    }
