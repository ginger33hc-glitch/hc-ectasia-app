"""Post-extraction validation guard for CER-AI.

This module does not extract or infer clinical values. It audits the merged extraction payload,
records provenance/coverage, and flags implausible or internally inconsistent transcriptions before
the CER-AI engine consumes them.

Multi-image numeric reconciliation policy:
- The owner-defined canonical Pentacam fields are NEVER reconciled here. They are direct
  single-source transcriptions and fail closed when their canonical source is unreadable.
- For non-locked numeric parameters, readings from multiple valid sources of the same provenance
  class may use the historical <=1% reconciliation rule.
"""
import re
from typing import Any, Dict, List

import bootstrap
from pentacam_field_registry import EXCLUSIVE_LABELED_BOX_FIELDS
from pentacam_canonical_source_lock import LOCKED_FIELDS

core = bootstrap.core
_original_merge = core.merge_extractions

DECISION_FIELDS = (
    "pachy_thinnest_um", "BAD_D", "Df", "Db", "Dp", "Dt", "Da", "ARTmax_um", "PPI_max"
)
PLAUSIBLE = {
    "pachy_thinnest_um": (300.0, 800.0),
    "K1_D": (20.0, 80.0), "K2_D": (20.0, 80.0), "Kmax_D": (20.0, 90.0),
    "K1_axis_deg": (0.0, 180.0), "K2_axis_deg": (0.0, 180.0),
    "corneal_diameter_mm": (8.0, 16.0),
    "BAD_D": (-10.0, 20.0), "Df": (-10.0, 20.0), "Db": (-10.0, 20.0),
    "Dp": (-10.0, 20.0), "Dt": (-10.0, 20.0), "Da": (-10.0, 20.0),
    "ARTmax_um": (1.0, 1000.0), "PPI_min": (0.01, 10.0),
    "PPI_avg": (0.01, 10.0), "PPI_max": (0.01, 10.0), "Rmin_mm": (3.0, 15.0),
}
LOWER_IS_SAFETY_LIMITING = {"Rmin_mm"}
NON_BLOCKING_CONFLICT_FIELDS = {"morphology_confidence"}

_CONFLICT_RE = re.compile(
    r"^(?P<field>[A-Za-z0-9_]+):\s*"
    r"(?P<a>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s+vs\s+"
    r"(?P<b>[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)$"
)


def _num(value: Any) -> bool:
    return core.is_number(value)


def _within_one_percent(values: List[float]) -> bool:
    if len(values) < 2:
        return False
    low, high = min(values), max(values)
    denominator = max(abs(v) for v in values)
    if denominator == 0:
        return low == high
    return abs(high - low) / denominator <= 0.01 + 1e-12


def _source_class(raw_eye: Dict[str, Any], field: str) -> str:
    if field in set(raw_eye.get("table_verified_numeric_fields") or []):
        return "LABELED_TABLE"
    if field in set(raw_eye.get("map_fallback_numeric_fields") or []):
        return "PERMITTED_MAP_FALLBACK"
    return "UNVERIFIED"


def _safety_limiting_value(field: str, values: List[float]) -> float:
    return min(values) if field in LOWER_IS_SAFETY_LIMITING else max(values)


def _reconcile_one_percent(merged: Dict[str, Any], results: List[Dict[str, Any]]) -> None:
    """Historical duplicate tolerance for NON-LOCKED fields only."""
    observations: Dict[str, Dict[str, Dict[str, List[float]]]] = {}
    for result in results:
        for raw_eye in result.get("eyes", []):
            if not isinstance(raw_eye, dict):
                continue
            eye_id = raw_eye.get("eye")
            if not eye_id:
                continue
            for field, value in raw_eye.items():
                if field in LOCKED_FIELDS or field in EXCLUSIVE_LABELED_BOX_FIELDS:
                    continue
                if not _num(value):
                    continue
                source_class = _source_class(raw_eye, field)
                if source_class == "UNVERIFIED":
                    continue
                observations.setdefault(eye_id, {}).setdefault(field, {}).setdefault(source_class, []).append(float(value))

    for eye in merged.get("eyes", []):
        if not isinstance(eye, dict):
            continue
        eye_id = eye.get("eye")
        accepted_fields = set()
        for field, classes in observations.get(eye_id, {}).items():
            values = classes.get("LABELED_TABLE") or classes.get("PERMITTED_MAP_FALLBACK") or []
            if _within_one_percent(values):
                retained = _safety_limiting_value(field, values)
                eye[field] = retained
                accepted_fields.add(field)
                eye.setdefault("numeric_reconciliation", {})[field] = {
                    "rule": "RELATIVE_SPREAD_LE_1_PERCENT_USE_SAFETY_LIMITING",
                    "direction": "LOWER" if field in LOWER_IS_SAFETY_LIMITING else "HIGHER",
                    "values": sorted(set(values)), "retained": retained,
                }
        if not accepted_fields:
            continue
        kept_conflicts = []
        for item in list(eye.get("data_conflicts") or []):
            match = _CONFLICT_RE.match(str(item).strip())
            if match and match.group("field") in accepted_fields:
                a, b = float(match.group("a")), float(match.group("b"))
                if _within_one_percent([a, b]):
                    continue
            kept_conflicts.append(item)
        eye["data_conflicts"] = kept_conflicts
        for field in sorted(accepted_fields):
            details = eye["numeric_reconciliation"][field]
            merged.setdefault("global_warnings", []).append(
                f"{eye_id} {field}: duplicate numeric readings within 1% were accepted; "
                f"safety-limiting {details['direction'].lower()} value {details['retained']:g} retained."
            )


def _audit_eye(eye: Dict[str, Any]) -> Dict[str, Any]:
    provenance = eye.get("field_provenance") or {}
    verified = set(eye.get("table_verified_numeric_fields") or [])
    surgeon_verified = set(eye.get("surgeon_verified_numeric_fields") or [])
    fallback = set(eye.get("map_fallback_numeric_fields") or [])
    issues: List[str] = []
    warnings: List[str] = []
    for field, (low, high) in PLAUSIBLE.items():
        value = eye.get(field)
        if value is not None and (not _num(value) or not low <= float(value) <= high):
            issues.append(f"{field}: extracted value {value!r} is outside validation range {low:g}–{high:g}")
    for field in DECISION_FIELDS:
        value = eye.get(field)
        if value is None:
            continue
        if field not in verified and field not in fallback and field not in surgeon_verified:
            issues.append(f"{field}: decision-critical value has no accepted labeled-field/map-fallback provenance")
        if not provenance.get(field):
            warnings.append(f"{field}: source-file provenance record is unavailable")
    pmin, pavg, pmax = eye.get("PPI_min"), eye.get("PPI_avg"), eye.get("PPI_max")
    if all(_num(v) for v in (pmin, pavg, pmax)) and not float(pmin) <= float(pavg) <= float(pmax):
        issues.append("PPI internal check failed: expected PPI min ≤ average ≤ max")
    conflicts = [
        conflict for conflict in (eye.get("data_conflicts") or [])
        if str(conflict).split(":", 1)[0].strip() not in NON_BLOCKING_CONFLICT_FIELDS
    ]
    if conflicts:
        issues.extend(f"unresolved multi-image conflict: {item}" for item in conflicts)
    available = sum(1 for field in DECISION_FIELDS if _num(eye.get(field)))
    table_count = sum(1 for field in DECISION_FIELDS if field in verified and _num(eye.get(field)))
    fallback_count = sum(1 for field in DECISION_FIELDS if field in fallback and _num(eye.get(field)))
    return {
        "status": "FAIL" if issues else "PASS" if available == len(DECISION_FIELDS) else "INCOMPLETE",
        "decision_fields_available": available, "decision_fields_required": len(DECISION_FIELDS),
        "decision_fields_from_labeled_tables": table_count,
        "decision_fields_from_permitted_map_fallback": fallback_count,
        "source_files": list(eye.get("source_files") or []),
        "issues": list(dict.fromkeys(issues)), "warnings": list(dict.fromkeys(warnings)),
    }


def merge_extractions_guarded(results):
    merged = _original_merge(results)
    _reconcile_one_percent(merged, results)
    audit = {}
    for eye in merged.get("eyes", []):
        eye_id = eye.get("eye", "UNKNOWN")
        result = _audit_eye(eye)
        audit[eye_id] = result
        eye["extraction_validation"] = result
        for issue in result["issues"]:
            message = f"{eye_id} extraction validation: {issue}"
            if message not in merged.setdefault("critical_input_issues", []):
                merged["critical_input_issues"].append(message)
        for warning in result["warnings"]:
            message = f"{eye_id} extraction audit: {warning}"
            if message not in merged.setdefault("global_warnings", []):
                merged["global_warnings"].append(message)
    merged["extraction_validation"] = audit
    merged["critical_input_issues"] = sorted(set(merged.get("critical_input_issues", [])))
    merged["global_warnings"] = list(dict.fromkeys(merged.get("global_warnings", [])))
    return merged


core.merge_extractions = merge_extractions_guarded
