"""Post-extraction validation guard for CER-AI.

This module does not extract or infer clinical values. It audits the merged extraction payload,
records provenance/coverage, and flags implausible or internally inconsistent transcriptions before
the CER-AI engine consumes them.

Canonical numeric disagreements are not reconciled here. They remain explicit conflicts until resolved.
"""
from typing import Any, Dict, List


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
NON_BLOCKING_CONFLICT_FIELDS = {"morphology_confidence"}


def _num(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _audit_eye(eye: Dict[str, Any]) -> Dict[str, Any]:
    provenance = eye.get("field_provenance") or {}
    verified = set(eye.get("table_verified_numeric_fields") or [])
    surgeon_verified = set(eye.get("surgeon_verified_numeric_fields") or [])
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
        if field not in verified and field not in surgeon_verified:
            issues.append(f"{field}: decision-critical value has no accepted labeled-field provenance")
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
    return {
        "status": "FAIL" if issues else "PASS" if available == len(DECISION_FIELDS) else "INCOMPLETE",
        "decision_fields_available": available, "decision_fields_required": len(DECISION_FIELDS),
        "decision_fields_from_labeled_tables": table_count,
        "source_files": list(eye.get("source_files") or []),
        "issues": list(dict.fromkeys(issues)), "warnings": list(dict.fromkeys(warnings)),
    }


def apply_extraction_validation(merged):
    """Audit one already-canonical merged payload without replacing merge ownership."""
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
