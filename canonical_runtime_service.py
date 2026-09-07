"""Direct case-level runtime for the CER-AI canonical clinical core.

This module is the future authoritative clinical runtime boundary. It does not
install or wrap application functions. It receives already-reconciled extraction
and normalized surgeon plans, maps each virgin eye once into ``ClinicalCoreInput``,
calls the pure clinical core once, and projects that result into the stable case
decision payload consumed by workflow/report/archive.

No Pentacam reading, clinical threshold, score formula, or downstream correction
belongs here.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Mapping

from clinical_core.disposition import (
    ASSESSMENT_INCOMPLETE,
    CAUTION,
    PASS,
    STOP_DEFER,
    DecisionFinding,
    finalize_disposition,
)
from clinical_core.pipeline import evaluate_normalized_case
from phase3_normalized_adapter import build_clinical_core_input

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


def _missing(core_result: Mapping[str, Any]) -> list[str]:
    missing = []
    erss = core_result.get("erss") or {}
    for row, value in (erss.get("rows") or {}).items():
        if value is None:
            missing.append(f"Randleman: {row}")
    for field in (core_result.get("nice") or {}).get("missing") or []:
        missing.append(f"NICE: {field}")
    ps3 = core_result.get("ps3")
    if ps3 is not None:
        for key in getattr(ps3, "missing_keys", ()):
            missing.append(f"PS3: {key}")
    return list(dict.fromkeys(missing))


def _values(core_result: Mapping[str, Any]) -> dict[str, Any]:
    safety = core_result.get("procedural_safety") or {}
    bad_result = (core_result.get("bad_d") or {}).get("result")
    values = {
        "LASIK_RSB_um": safety.get("LASIK_RSB_um"),
        "PRK_RST_um": safety.get("PRK_RST_um"),
        "LASIK_PTA_percent": safety.get("LASIK_PTA_percent"),
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
    if status == CAUTION:
        return "CAUTION — surgeon review required."
    if status == PASS:
        return "PASS — no CER-AI escalation identified by the completed canonical assessment."
    if status == POST_REFRACTIVE:
        return "Use the post-refractive-surgery pathway; virgin-cornea engine not applicable."
    return "Clinical review required."


def _virgin_eye_payload(eye_name: str, core_result: Mapping[str, Any]) -> dict[str, Any]:
    safety = core_result.get("procedural_safety") or {}
    status = str(core_result.get("status") or ASSESSMENT_INCOMPLETE)
    bad = core_result.get("bad_d") or {}
    ps3 = core_result.get("ps3")
    return {
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
        "values": _values(core_result),
        "hard_stops": _hard_stop_reasons(safety),
        "reasons": _decision_reasons(core_result),
        "warnings": [],
        "missing": _missing(core_result),
        "canonical_result": _plain(core_result),
    }


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
        "missing": [],
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
    *,
    software_version: str | None = None,
) -> dict[str, Any]:
    """Evaluate each classified eye exactly once through the canonical core."""
    source = _eye_by_name(extracted)
    results: list[dict[str, Any]] = []

    for eye_name in ("OD", "OS"):
        eye = source.get(eye_name)
        plan = eye_plans.get(eye_name)
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
                "missing": ["procedure"],
                "canonical_result": None,
            })
            continue
        normalized = build_clinical_core_input(
            eye,
            plan,
            age_years=age_years,
            extracted=extracted,
        )
        results.append(_virgin_eye_payload(eye_name, evaluate_normalized_case(normalized)))

    return {
        "status": _overall_status(results) if results else ASSESSMENT_INCOMPLETE,
        "eyes": results,
        "version": software_version,
        "engine": "CERAI_CANONICAL_CLINICAL_CORE",
    }
