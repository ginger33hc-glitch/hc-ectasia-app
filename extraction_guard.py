"""Post-extraction validation guard for HC Ectasia App.

This module does not extract or infer clinical values. It audits the merged extraction payload,
records provenance/coverage, and flags implausible or internally inconsistent transcriptions before
the HC engine consumes them.
"""
from typing import Any, Dict, List

import bootstrap

core = bootstrap.core
_original_merge = core.merge_extractions

DECISION_FIELDS = (
    "pachy_thinnest_um", "BAD_D", "Df", "Db", "Dp", "Dt", "Da", "ARTmax_um", "PPI_max"
)
PLAUSIBLE = {
    "pachy_thinnest_um": (300.0, 800.0),
    "K1_D": (20.0, 80.0), "K2_D": (20.0, 80.0), "Kmax_D": (20.0, 90.0),
    "BAD_D": (-10.0, 20.0), "Df": (-10.0, 20.0), "Db": (-10.0, 20.0),
    "Dp": (-10.0, 20.0), "Dt": (-10.0, 20.0), "Da": (-10.0, 20.0),
    "ARTmax_um": (1.0, 1000.0), "PPI_min": (0.01, 10.0),
    "PPI_avg": (0.01, 10.0), "PPI_max": (0.01, 10.0), "Rmin_mm": (3.0, 15.0),
}

def _num(value: Any) -> bool:
    return core.is_number(value)


def _audit_eye(eye: Dict[str, Any]) -> Dict[str, Any]:
    provenance = eye.get("field_provenance") or {}
    verified = set(eye.get("table_verified_numeric_fields") or [])
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
        if field not in verified and field not in fallback:
            issues.append(f"{field}: decision-critical value has no accepted labeled-field/map-fallback provenance")
        if not provenance.get(field):
            warnings.append(f"{field}: source-file provenance record is unavailable")

    pmin, pavg, pmax = eye.get("PPI_min"), eye.get("PPI_avg"), eye.get("PPI_max")
    if all(_num(v) for v in (pmin, pavg, pmax)) and not float(pmin) <= float(pavg) <= float(pmax):
        issues.append("PPI internal check failed: expected PPI min ≤ average ≤ max")

    pachy, art = eye.get("pachy_thinnest_um"), eye.get("ARTmax_um")
    if all(_num(v) for v in (pachy, art, pmax)) and float(pmax) > 0:
        expected = float(pachy) / float(pmax)
        if abs(float(art) - expected) > max(20.0, 0.10 * expected):
            issues.append("ARTmax internal check failed against thinnest pachymetry / PPImax")

    conflicts = list(eye.get("data_conflicts") or [])
    if conflicts:
        issues.extend(f"unresolved multi-image conflict: {item}" for item in conflicts)

    available = sum(1 for field in DECISION_FIELDS if _num(eye.get(field)))
    table_count = sum(1 for field in DECISION_FIELDS if field in verified and _num(eye.get(field)))
    fallback_count = sum(1 for field in DECISION_FIELDS if field in fallback and _num(eye.get(field)))
    return {
        "status": "FAIL" if issues else "PASS" if available == len(DECISION_FIELDS) else "INCOMPLETE",
        "decision_fields_available": available,
        "decision_fields_required": len(DECISION_FIELDS),
        "decision_fields_from_labeled_tables": table_count,
        "decision_fields_from_permitted_map_fallback": fallback_count,
        "source_files": list(eye.get("source_files") or []),
        "issues": list(dict.fromkeys(issues)),
        "warnings": list(dict.fromkeys(warnings)),
    }


def merge_extractions_guarded(results):
    merged = _original_merge(results)
    audit = {}
    for eye in merged.get("eyes", []):
        eye_id = eye.get("eye", "UNKNOWN")
        result = _audit_eye(eye)
        audit[eye_id] = result
        eye["extraction_validation"] = result
        if result["issues"]:
            for issue in result["issues"]:
                message = f"{eye_id} extraction validation: {issue}"
                if message not in merged.setdefault("critical_input_issues", []):
                    merged["critical_input_issues"].append(message)
        if result["warnings"]:
            for warning in result["warnings"]:
                message = f"{eye_id} extraction audit: {warning}"
                if message not in merged.setdefault("global_warnings", []):
                    merged["global_warnings"].append(message)
    merged["extraction_validation"] = audit
    merged["critical_input_issues"] = sorted(set(merged.get("critical_input_issues", [])))
    merged["global_warnings"] = list(dict.fromkeys(merged.get("global_warnings", [])))
    return merged

core.merge_extractions = merge_extractions_guarded
