"""CER-AI pachymetry policy patch.

CER-AI policy:
- thinnest pachymetry <480 µm: hard stop (no pachymetry score used for clearance)
- 480-499 µm: 2 points
- 500-509 µm: 1 point
- >=510 µm: 0 points

Evidence note: this is an CER-AI-modified pachymetry component, not the original published
Randleman ERSS pachymetry table. The published ERSS grouped 481-510 µm together at +2.
The CER-AI modification deliberately introduces 500 µm as a clinical transition because the
refractive-surgery literature commonly discusses <500 µm as a thin-cornea risk phenotype,
while also recognizing that pachymetry alone has no validated binary safe/unsafe cutoff.
Exactly 480 µm remains scoreable because the independent CER-AI hard stop applies only below 480 µm.
"""
import bootstrap

core = bootstrap.core


def hc_lasik_pachy_points(pachy):
    if not core.is_number(pachy):
        return None
    value = float(pachy)
    if value < 480:
        return None
    if value < 500:
        return 2
    if value < 510:
        return 1
    return 0


# assess_eye resolves this module global at runtime, so the CER-AI scoring function
# replaces only the LASIK pachymetry component while preserving the other ERSS components.
core.lasik_pachy_points = hc_lasik_pachy_points

_previous_assess_eye = core.assess_eye


def assess_eye_with_hc_pachymetry(eye, plan, age, patient_modifiers):
    original_pachy = eye.get("pachy_thinnest_um")
    working_eye = eye

    # The legacy engine has an explicit unresolved-boundary branch at exactly 510 µm.
    # Move only the internal compatibility value just above that boundary; the CER-AI scorer
    # therefore assigns 0 points and the clinically reported pachymetry is restored to 510.
    if core.is_number(original_pachy) and float(original_pachy) == 510.0:
        working_eye = dict(eye)
        working_eye["pachy_thinnest_um"] = 510.000001

    result = _previous_assess_eye(working_eye, plan, age, patient_modifiers)

    # Prior-surgery cases belong to a separate post-refractive pathway. No
    # virgin-cornea pachymetry hard stop or score may overwrite that routing.
    if result.get("status") == "POST-REFRACTIVE PATHWAY REQUIRED":
        return result

    if core.is_number(original_pachy):
        value = float(original_pachy)
        result.setdefault("values", {})["pachy_thinnest_um"] = original_pachy

        if value < 480:
            stop = "CER-AI operational hard stop: thinnest preoperative cornea <480 µm."
            hard_stops = list(result.get("hard_stops") or [])
            hard_stops = [x for x in hard_stops if "thinnest preoperative cornea <480" not in str(x)]
            if stop not in hard_stops:
                hard_stops.append(stop)
            result["hard_stops"] = hard_stops

            reasons = list(result.get("reasons") or [])
            reasons = [x for x in reasons if "thinnest preoperative cornea <480" not in str(x)]
            if stop not in reasons:
                reasons.insert(0, stop)
            result["reasons"] = list(dict.fromkeys(reasons))
            result["status"] = "STOP-DEFER"
            result["action"] = "STOP-DEFER; do not proceed with elective corneal refractive surgery."

        if result.get("values", {}).get("procedure") == "LASIK":
            score = result.get("score") or {}
            if value < 480:
                score.setdefault("rows", {})["pachymetry"] = None
            result["score"] = score
            warnings = list(result.get("warnings") or [])
            warnings.append(
                "CER-AI-MODIFIED LASIK PACHYMETRY POLICY: <480 µm = hard stop; "
                "480-499 µm = +2; 500-509 µm = +1; >=510 µm = +0. "
                "This CER-AI banding is not the original published Randleman pachymetry table."
            )
            result["warnings"] = list(dict.fromkeys(warnings))

    return result


core.assess_eye = assess_eye_with_hc_pachymetry

app = bootstrap.app
