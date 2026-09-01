"""Single non-blocking Pentacam acquisition-quality policy.

QS and generic source-image quality are preserved as surgeon-facing warnings.
They never replace missing clinical measurements and never decide a clinical score.
"""

from __future__ import annotations

from typing import Any


WARNING_HEADING = "PENTACAM ACQUISITION QUALITY — SURGEON ATTENTION"


def warnings_for_extracted(extracted: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    for eye in extracted.get("eyes") or []:
        eye_id = eye.get("eye")
        if eye_id not in {"OD", "OS"}:
            continue
        qs = str(eye.get("pentacam_qs") or "NOT_SHOWN")
        quality = str(eye.get("quality") or "UNREADABLE")
        concerns = []
        if qs != "OK":
            concerns.append(
                "device QS is NOT_OK" if qs == "NOT_OK"
                else f"explicit QS: OK was not confirmed ({qs})"
            )
        if quality in {"LIMITED", "INADEQUATE"}:
            concerns.append(f"source image quality is {quality}")
        if concerns:
            warnings.append(
                f"{eye_id}: {', '.join(concerns)}. The assessment was generated from the readable "
                "data, but acquisition quality is not confirmed as OK. The surgeon must review "
                "the source images and interpret all findings with caution."
            )
    return list(dict.fromkeys(warnings))


def is_quality_only_issue(message: Any) -> bool:
    text = str(message or "").casefold()
    return (
        text == "explicit pentacam qs: ok"
        or text == "adequate-quality tomography/topography"
        or text.startswith("pentacam acquisition requires a same-exam explicit qs: ok")
        or "source image quality: limited/inadequate decision source" in text
    )
