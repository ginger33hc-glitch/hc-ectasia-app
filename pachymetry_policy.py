"""HC pachymetry policy patch.

Policy:
- thinnest pachymetry <=480 µm: HC hard stop (no pachymetry score used for clearance)
- 481-499 µm: 2 points
- 500-510 µm: 1 point
- >=511 µm: 0 points

This is an HC-modified pachymetry component, not the original published ERSS pachymetry table.
"""
import critical_score_highlight as runtime
import bootstrap

core = bootstrap.core


def hc_lasik_pachy_points(pachy):
    if not core.is_number(pachy):
        return None
    value = float(pachy)
    if value <= 480:
        return None
    if value < 500:
        return 2
    if value <= 510:
        return 1
    return 0


# assess_eye resolves this module global at runtime, so the HC scoring function
# replaces only the LASIK pachymetry component while preserving the other ERSS components.
core.lasik_pachy_points = hc_lasik_pachy_points

_previous_assess_eye = core.assess_eye


def assess_eye_with_hc_pachymetry(eye, plan, age, patient_modifiers):
    original_pachy = eye.get("pachy_thinnest_um")
    working_eye = eye

    # The legacy engine had an explicit unresolved-boundary branch at exactly
    # 510 µm. Nudge only the internal legacy boundary check below 510; the HC
    # scorer still assigns 1 point and the reported clinical value is restored.
    if core.is_number(original_pachy) and float(original_pachy) == 510.0:
        working_eye = dict(eye)
        working_eye["pachy_thinnest_um"] = 509.999999

    result = _previous_assess_eye(working_eye, plan, age, patient_modifiers)

    if core.is_number(original_pachy):
        value = float(original_pachy)
        result.setdefault("values", {})["pachy_thinnest_um"] = original_pachy

        if value <= 480:
            stop = "HC operational hard stop: thinnest preoperative cornea <=480 µm."
            hard_stops = list(result.get("hard_stops") or [])
            # Remove superseded wording if present, then enforce the inclusive cutoff.
            hard_stops = [x for x in hard_stops if "thinnest preoperative cornea <480" not in str(x)]
            if stop not in hard_stops:
                hard_stops.append(stop)
            result["hard_stops"] = hard_stops

            reasons = list(result.get("reasons") or [])
            reasons = [x for x in reasons if "thinnest preoperative cornea <480" not in str(x)]
            if stop not in reasons:
                reasons.insert(0, stop)
            result["reasons"] = list(dict.fromkeys(reasons))
            result["status"] = "DO NOT PROCEED"
            result["action"] = "DO NOT PROCEED with elective corneal refractive surgery."

        # Make the report explicit that this pachymetry banding is HC-modified,
        # rather than presenting it as the original Randleman pachymetry table.
        if result.get("values", {}).get("procedure") == "LASIK":
            score = result.get("score") or {}
            if value <= 480:
                score.setdefault("rows", {})["pachymetry"] = None
            result["score"] = score
            warnings = list(result.get("warnings") or [])
            warnings.append(
                "HC-MODIFIED LASIK PACHYMETRY POLICY: <=480 µm = hard stop; "
                "481-499 µm = +2; 500-510 µm = +1; >=511 µm = +0. "
                "These pachymetry bands are an HC protocol modification and are not the original ERSS pachymetry bins."
            )
            result["warnings"] = list(dict.fromkeys(warnings))

    return result


core.assess_eye = assess_eye_with_hc_pachymetry

# Expose the already patched FastAPI app for Uvicorn.
app = runtime.app
