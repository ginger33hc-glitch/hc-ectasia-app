"""Locks absence-preserving treatment-card extraction."""
from pathlib import Path
import re


def test_prompt_never_converts_absent_cylinder_or_axis_to_zero():
    source = (Path(__file__).resolve().parents[1] / "app.py").read_text()
    assert "only one signed refractive value" in source
    assert "Never convert absent cylinder or axis notation into zero" in source
    assert "return cylinder_D=0, axis_deg=0" not in source
    assert re.search(
        r"absent, obscured, cropped, ambiguous, or unreadable cylinder region\s*must remain null",
        source,
    )
