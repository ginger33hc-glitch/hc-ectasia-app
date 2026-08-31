"""Pure non-scored inter-eye tomography discordance assessment.

This module intentionally does not change CER-AI score, status, hard stops, BAD-D,
or Randleman/ERSS logic. It reports only major bilateral categorical discordance.
"""
from typing import Any, Dict, Iterable

EYES = ("OD", "OS")


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _bad_category(value: Any) -> str:
    if not _is_number(value):
        return "UNAVAILABLE"
    value = float(value)
    if value <= 1.6:
        return "NORMAL"
    if value < 2.6:
        return "SUSPICIOUS"
    return "ABNORMAL"


def _eye_map(extracted_eyes: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        str(eye.get("eye")): eye
        for eye in extracted_eyes
        if isinstance(eye, dict) and eye.get("eye") in EYES
    }


def _morphology_major(a: str, b: str) -> bool:
    classifiable = {"NORMAL_SYMMETRIC", "ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA", "ABNORMAL_ECTATIC"}
    if a not in classifiable or b not in classifiable or a == b:
        return False
    if "NORMAL_SYMMETRIC" in {a, b}:
        return True
    if "ABNORMAL_ECTATIC" in {a, b}:
        return True
    return False


def _pattern_major(a: str, b: str) -> bool:
    classifiable = {"REASSURING", "BORDERLINE", "ABNORMAL"}
    if a not in classifiable or b not in classifiable or a == b:
        return False
    if "REASSURING" in {a, b}:
        return True
    if "ABNORMAL" in {a, b}:
        return True
    return False


def assess_inter_eye_tomography(extracted_eyes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Return a non-scored bilateral discordance finding.

    Positive if any major categorical discordance exists in Final BAD-D,
    anterior morphology, anterior elevation pattern, or posterior elevation pattern.
    A negative finding requires all four domains to be classifiable in both eyes;
    otherwise the result is NOT ASSESSABLE unless a positive discordance is already found.
    """
    eyes = _eye_map(extracted_eyes)
    if set(eyes) != set(EYES):
        return {
            "status": "NOT ASSESSABLE",
            "major_discordances": [],
            "note": "Bilateral OD/OS tomography is required for automated inter-eye assessment.",
            "scored": False,
            "decision_effect": "NONE",
        }

    od, os = eyes["OD"], eyes["OS"]
    discordances = []
    unavailable = []

    bad_od, bad_os = _bad_category(od.get("BAD_D")), _bad_category(os.get("BAD_D"))
    if "UNAVAILABLE" in {bad_od, bad_os}:
        unavailable.append("Final BAD-D")
    elif bad_od != bad_os:
        discordances.append(f"Final BAD-D category discordance: OD {bad_od} vs OS {bad_os}.")

    morph_od, morph_os = str(od.get("morphology") or ""), str(os.get("morphology") or "")
    if morph_od not in {"NORMAL_SYMMETRIC", "ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA", "ABNORMAL_ECTATIC"} or morph_os not in {"NORMAL_SYMMETRIC", "ASYMMETRIC_BOWTIE", "INFERIOR_STEEPENING_SRA", "ABNORMAL_ECTATIC"}:
        unavailable.append("anterior morphology")
    elif _morphology_major(morph_od, morph_os):
        discordances.append(f"Anterior morphology discordance: OD {morph_od} vs OS {morph_os}.")

    for label, key in (("anterior pattern", "anterior_pattern"), ("posterior pattern", "posterior_pattern")):
        a, b = str(od.get(key) or ""), str(os.get(key) or "")
        if a not in {"REASSURING", "BORDERLINE", "ABNORMAL"} or b not in {"REASSURING", "BORDERLINE", "ABNORMAL"}:
            unavailable.append(label)
        elif _pattern_major(a, b):
            discordances.append(f"{label.title()} discordance: OD {a} vs OS {b}.")

    if discordances:
        return {
            "status": "POSITIVE",
            "major_discordances": discordances,
            "unavailable_domains": unavailable,
            "note": "Major inter-eye tomography discordance detected. Non-scored contextual finding; review for asymmetric/subclinical ectatic phenotype.",
            "scored": False,
            "decision_effect": "NONE",
        }
    if unavailable:
        return {
            "status": "NOT ASSESSABLE",
            "major_discordances": [],
            "unavailable_domains": unavailable,
            "note": "No major discordance was demonstrated, but one or more required bilateral categorical domains are unavailable/unreadable.",
            "scored": False,
            "decision_effect": "NONE",
        }
    return {
        "status": "NO MAJOR INTER-EYE DISCORDANCE DETECTED",
        "major_discordances": [],
        "unavailable_domains": [],
        "note": "No major categorical inter-eye tomography discordance detected. This is not a clearance criterion and does not change the CER-AI score or final disposition.",
        "scored": False,
        "decision_effect": "NONE",
    }
