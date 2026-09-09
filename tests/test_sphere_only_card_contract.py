"""Locks the explicit sphere-only treatment-card extraction rule."""
from pathlib import Path
import re


def test_prompt_maps_clear_sphere_only_card_row_to_zero_cylinder_and_axis():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    assert "any one signed refractive value" in source
    assert "return cylinder_D=0, axis_deg=0" in source
    assert re.search(
        r"obscured,\s*cropped, ambiguous, or unreadable cylinder region must remain null",
        source,
    )
