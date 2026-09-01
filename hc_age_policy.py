"""CER-AI protocol modification: age scoring for ectasia risk assessment.

This intentionally overrides the source-study age bands in the runtime engine.
CER-AI age bands:
- age 18: 3 points
- age 19-20: 2 points
- age >=21: 0 points
Ages <18 or unavailable are not scored.
"""


def hc_age_points(age):
    if not isinstance(age, (int, float)) or isinstance(age, bool) or age < 18:
        return None
    age = float(age)
    if age < 19:
        return 3
    if age < 21:
        return 2
    return 0


def install(core, *, score_audit_owner=None) -> None:
    """Attach the age policy and its provenance note explicitly and once."""
    if getattr(core, "_hc_age_policy_installed", False):
        return

    # assess_eye resolves age_points from the app module at call time, so this
    # applies the policy consistently to LASIK and PRK scoring.
    core.age_points = hc_age_points

    # Preserve the existing score-audit implementation while adding the
    # CER-AI-specific provenance note.
    original_score_audit = getattr(score_audit_owner, "_score_audit", None)
    if original_score_audit:

        def score_audit_with_hc_age(result):
            audit = original_score_audit(result)
            if audit and (result.get("values") or {}).get("procedure") in (
                "LASIK",
                "PRK",
            ):
                audit["source"] = (
                    audit.get("source", "") + "; CER-AI-modified age bands"
                )
            return audit

        score_audit_owner._score_audit = score_audit_with_hc_age

    core._hc_age_policy_installed = True
