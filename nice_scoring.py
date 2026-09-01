"""Pure CER-AI-adapted NICE score. No ERSS/BAD calculations or framework dependencies."""
import math

SOURCE = "https://pmc.ncbi.nlm.nih.gov/articles/PMC10960505/"
POLICY_VERSION = "CER-AI-NICE-2026-09-01-B-ELE-TH"
NOTE = (
    "NICE (Navarro Index for Corneal Ectasia) combines K2, central pachymetry, "
    "posterior elevation and signed I-S. Each component contributes 1-3 points; total 4-12. "
    "CER-AI adaptation: posterior elevation <=15.5 um = 1, >15.5 to <18 um = 2, >=18 um = 3. "
    "The published table leaves 15 um unspecified. CER-AI uses only the explicitly labeled "
    "B. Ele.Th value on the Pentacam BAD Display page; no map or calculated substitute is accepted. "
    "Central pachymetry uses the plus-marked Pupil Center field (not Pachy Vertex N. or thinnest pachymetry), "
    "or a surgeon-confirmed central measurement. CER-AI disposition for LASIK and PRK: "
    "4 = no NICE-specific escalation, 5-8 = CAUTION / STOP-DEFER, >=9 = HARD STOP. "
    "NICE 4 does not establish surgical safety or override ERSS, BAD or other CER-AI stops. "
    "No individual absolute ectasia probability is inferred. Source: Navarro-Naranjo et al., "
    "Clin Ophthalmol 2024;18:881-883. DOI: 10.2147/OPTH.S464217."
)


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def score_nice(k2, central_pachy, b_ele_th, i_s):
    values = {"K2_D": k2, "central_pachy_um": central_pachy,
              "B_Ele_Th_um": b_ele_th, "I_S_D": i_s}
    missing = [key for key, value in values.items() if not finite(value)]
    for key, low, high in (("K2_D", 20, 80), ("central_pachy_um", 300, 800)):
        if finite(values[key]) and not low <= values[key] <= high:
            missing.append(key)
    if finite(b_ele_th) and not -300 <= b_ele_th <= 300:
        missing.append("B_Ele_Th_um")
    if missing:
        return {"total": None, "category": "INCOMPLETE", "rows": {}, "values": values,
                "missing": sorted(set(missing)), "policy_version": POLICY_VERSION,
                "source": SOURCE, "note": NOTE}
    rows = {
        "K2": 1 if k2 < 45 else 2 if k2 <= 47 else 3,
        "central_pachymetry": 1 if central_pachy > 520 else 2 if central_pachy >= 500 else 3,
        "B_Ele_Th": 1 if b_ele_th <= 15.5 else 2 if b_ele_th < 18 else 3,
        "I_S": 1 if i_s < 1 else 2 if i_s <= 1.4 else 3,
    }
    total = sum(rows.values())
    return {"total": total, "category": "NO_NICE_ESCALATION" if total == 4 else "CAUTION" if total <= 8 else "HARD_STOP",
            "rows": rows, "values": values, "missing": [], "policy_version": POLICY_VERSION,
            "source": SOURCE, "note": NOTE}
