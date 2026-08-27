"""HC protocol modification: age scoring for ectasia risk assessment.

This intentionally overrides the source-study age bands in the runtime engine.
HC age bands:
- age 18: 3 points
- age 19-20: 2 points
- age >=21: 0 points
Ages <18 or unavailable are not scored.
"""
import bootstrap

core = bootstrap.core


def hc_age_points(age):
    if not core.is_number(age) or age < 18:
        return None
    age = float(age)
    if age < 19:
        return 3
    if age < 21:
        return 2
    return 0


# assess_eye resolves age_points from the app module at call time, so replacing
# the module global applies this policy consistently to LASIK and PRK scoring.
core.age_points = hc_age_points

# Preserve the already-installed assessment wrappers while making provenance
# explicit in the score audit/report text.
_original_score_audit = getattr(bootstrap, "_score_audit", None)
if _original_score_audit:
    def _hc_score_audit(result):
        audit = _original_score_audit(result)
        if audit and (result.get("values") or {}).get("procedure") in ("LASIK", "PRK"):
            audit["source"] = audit.get("source", "") + "; HC-modified age bands"
        return audit
    bootstrap._score_audit = _hc_score_audit

app = bootstrap.app
