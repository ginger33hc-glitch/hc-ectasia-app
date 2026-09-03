"""Pure pre-assessment readiness rules for CER-AI.

These rules run before clinical scoring. They contain no FastAPI/session/runtime
state and are introduced in parallel for Phase 2 equivalence only.
"""
from __future__ import annotations

from math import isfinite

SOFT_CONTACT_LENS_WASHOUT_DAYS = 10
RIGID_CONTACT_LENS_WASHOUT_DAYS = 21


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def contact_lens_washout(modifiers: dict | None):
    """Return the frozen blocking readiness payload, or None when ready."""
    modifiers = modifiers or {}
    lens_type = str(modifiers.get("contact_lens_type") or "UNKNOWN").upper()
    days = modifiers.get("contact_lens_discontinuation_days")

    if lens_type == "NONE":
        return None
    if lens_type not in {"SOFT", "RIGID"}:
        return {
            "type": lens_type,
            "days": days,
            "required_days": None,
            "message": "Contact-lens type must be documented before CER-AI can proceed.",
            "form_id": "contact_lens_type",
        }

    required = SOFT_CONTACT_LENS_WASHOUT_DAYS if lens_type == "SOFT" else RIGID_CONTACT_LENS_WASHOUT_DAYS
    if not _finite(days) or int(days) != days:
        return {
            "type": lens_type,
            "days": days,
            "required_days": required,
            "message": f"Document the number of full days {lens_type.lower()} contact lenses were discontinued before Pentacam. Required washout: at least {required} days.",
            "form_id": "contact_lens_days",
        }

    days = int(days)
    if days < required:
        remaining = required - days
        lens_name = "soft contact lenses" if lens_type == "SOFT" else "rigid / RGP contact lenses"
        return {
            "type": lens_type,
            "days": days,
            "required_days": required,
            "remaining_days": remaining,
            "message": (
                f"Do not proceed with CER-AI assessment. The patient used {lens_name} and stopped only {days} day(s) before Pentacam. "
                f"Wait until at least {required} full days off lenses have elapsed, then repeat Pentacam and reassess."
            ),
            "form_id": "contact_lens_days",
        }
    return None
