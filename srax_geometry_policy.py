"""Install deterministic SRAX geometry as the only automated SRAX source."""

from __future__ import annotations

from srax_geometry import analyze_srax_bytes

_previous_extract_one_image = None


def extract_one_image_with_geometric_srax(raw: bytes, filename: str):
    result = _previous_extract_one_image(raw, filename)
    context = result.get("document_context") or {}
    if context.get("document_type") != "PENTACAM_TOPOGRAPHY":
        return result

    geometry = analyze_srax_bytes(raw)
    for eye in result.get("eyes", []):
        if not isinstance(eye, dict):
            continue
        # Retire model visual SRAX. Only deterministic geometry or later explicit
        # surgeon confirmation may resolve these fields.
        eye["srax"] = "UNCERTAIN"
        eye["srax_deg"] = None
        eye["srax_geometry_source"] = geometry.source
        eye["srax_geometry_confidence"] = geometry.confidence
        eye["srax_geometry_reason"] = geometry.reason
        eye["srax_superior_axis_deg"] = geometry.superior_axis_deg
        eye["srax_inferior_axis_deg"] = geometry.inferior_axis_deg
        eye["srax_geometry_uncertainty_deg"] = geometry.uncertainty_deg

        if geometry.status in {"YES", "NO"} and geometry.confidence == "HIGH":
            eye["srax"] = geometry.status
            eye["srax_deg"] = geometry.srax_deg
            evidence = list(eye.get("morphology_evidence") or [])
            evidence.append(
                "Deterministic Front-map SRAX geometry: "
                f"superior axis {geometry.superior_axis_deg:.1f}°, "
                f"inferior axis {geometry.inferior_axis_deg:.1f}°, "
                f"SRAX {geometry.srax_deg:.1f}°; criterion is strictly >20°."
            )
            eye["morphology_evidence"] = list(dict.fromkeys(evidence))
    return result


def install(core) -> None:
    global _previous_extract_one_image
    if getattr(core, "_cerai_srax_geometry_installed", False):
        return
    _previous_extract_one_image = core.extract_one_image
    core.extract_one_image = extract_one_image_with_geometric_srax
    core._cerai_srax_geometry_installed = True
