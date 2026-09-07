"""Canonical provenance and conflict resolution for locked Pentacam fields.

This module is pure and side-effect free. It accepts observations only from the
field's exact canonical source and never reconciles across screens, eyes or exam
dates. Same-eye/same-exam/same-source disagreement is a CONFLICT. Surgeon
correction is explicit and retains the original automatic observations.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Iterable

from pentacam_canonical_source_lock import canonical_source_id

AUTO = "AUTO"
SURGEON_CONFIRMED = "SURGEON_CONFIRMED"
RESOLVED = "RESOLVED"
CONFLICT = "CONFLICT"
UNREADABLE = "UNREADABLE"
WRONG_SOURCE = "WRONG_SOURCE"
EXAM_SELECTION_REQUIRED = "EXAM_SELECTION_REQUIRED"


@dataclass(frozen=True)
class Observation:
    eye: str
    exam_id: str
    field: str
    source_id: str
    value: Any
    origin: str = AUTO
    file: str | None = None
    source_box: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class ResolvedField:
    eye: str
    exam_id: str | None
    field: str
    status: str
    value: float | None
    provenance: tuple[Observation, ...]
    ignored_wrong_source: tuple[Observation, ...] = ()
    audit_history: tuple[Observation, ...] = ()


def _numeric(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
    )


def _same_number(values: list[float]) -> bool:
    return max(values) - min(values) <= 1e-9


def resolve_field(
    observations: Iterable[Observation],
    *,
    eye: str,
    field: str,
    exam_id: str | None = None,
) -> ResolvedField:
    """Resolve one eye/field from its exact canonical source only.

    Different-eye observations are outside this field and ignored. Wrong-source
    observations are retained only as audit evidence; they never create a
    conflict. If more than one exam date/id is represented and the caller has
    not selected one, explicit exam selection is required instead of merging.
    """
    expected_source = canonical_source_id(field)
    relevant_eye = [o for o in observations if o.eye == eye and o.field == field]
    wrong_source = tuple(
        o for o in relevant_eye if expected_source is not None and o.source_id != expected_source
    )
    canonical = [
        o for o in relevant_eye
        if expected_source is None or o.source_id == expected_source
    ]

    exam_ids = sorted({o.exam_id for o in canonical if o.exam_id})
    if exam_id is None and len(exam_ids) > 1:
        return ResolvedField(
            eye, None, field, EXAM_SELECTION_REQUIRED, None, tuple(canonical), wrong_source
        )
    selected_exam = exam_id or (exam_ids[0] if exam_ids else None)
    selected = [o for o in canonical if o.exam_id == selected_exam] if selected_exam else canonical

    surgeon = [o for o in selected if o.origin == SURGEON_CONFIRMED and _numeric(o.value)]
    automatic = [o for o in selected if o.origin != SURGEON_CONFIRMED]
    if surgeon:
        values = [float(o.value) for o in surgeon]
        if not _same_number(values):
            return ResolvedField(
                eye, selected_exam, field, CONFLICT, None, tuple(surgeon), wrong_source,
                tuple(automatic),
            )
        return ResolvedField(
            eye, selected_exam, field, RESOLVED, values[0], tuple(surgeon), wrong_source,
            tuple(automatic),
        )

    numeric = [o for o in automatic if _numeric(o.value)]
    if not numeric:
        return ResolvedField(
            eye, selected_exam, field, UNREADABLE, None, tuple(automatic), wrong_source
        )
    values = [float(o.value) for o in numeric]
    if not _same_number(values):
        return ResolvedField(
            eye, selected_exam, field, CONFLICT, None, tuple(numeric), wrong_source
        )
    return ResolvedField(
        eye, selected_exam, field, RESOLVED, values[0], tuple(numeric), wrong_source
    )


def surgeon_confirm(
    resolved: ResolvedField,
    *,
    value: float,
    file: str | None = None,
    source_box: tuple[int, int, int, int] | None = None,
) -> ResolvedField:
    """Return a new resolved field with an explicit surgeon-confirmed value.

    The original automatic observations remain in ``audit_history``. This
    function never mutates the prior result.
    """
    if not _numeric(value):
        raise ValueError("surgeon-confirmed value must be finite numeric")
    if not resolved.exam_id:
        raise ValueError("exam must be selected before surgeon confirmation")
    source_id = canonical_source_id(resolved.field)
    if source_id is None:
        raise ValueError("field has no canonical source")
    correction = Observation(
        eye=resolved.eye,
        exam_id=resolved.exam_id,
        field=resolved.field,
        source_id=source_id,
        value=float(value),
        origin=SURGEON_CONFIRMED,
        file=file,
        source_box=source_box,
    )
    prior = tuple(resolved.provenance) + tuple(resolved.audit_history)
    return ResolvedField(
        eye=resolved.eye,
        exam_id=resolved.exam_id,
        field=resolved.field,
        status=RESOLVED,
        value=float(value),
        provenance=(correction,),
        ignored_wrong_source=resolved.ignored_wrong_source,
        audit_history=prior,
    )
