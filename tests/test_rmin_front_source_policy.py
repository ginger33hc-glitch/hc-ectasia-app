from pathlib import Path

import canonical_engine
import pentacam_targeted_reread as reread
from pentacam_canonical_source_lock import SHOW_2_CORNEA_BACK, canonical_source_id


def test_rmin_has_one_canonical_source_and_no_map_fallback():
    assert canonical_source_id("Rmin_mm") == SHOW_2_CORNEA_BACK
    assert not hasattr(canonical_engine.core, "MAP_FALLBACK_NUMERIC_FIELDS")
    assert not Path("rmin_front_source_policy.py").exists()


def test_canonical_prompt_locks_rmin_to_show2_cornea_back():
    prompt = canonical_engine.core.PROMPT
    assert "Rmin_mm: exactly one accepted source" in prompt
    assert "Cornea Back" in prompt
    assert "No numeric map fallback is permitted" in prompt


def test_targeted_reread_rejects_cornea_front_rmin_source():
    assert not reread.source_supports_field("SHOW_2_EXAMS_TOPOMETRIC", "Rmin_mm", "Cornea Front")
    assert reread.source_supports_field("SHOW_2_EXAMS_TOPOMETRIC", "Rmin_mm", "Cornea Back")


def test_targeted_reread_distinguishes_topometric_rmin_from_cornea_back_rmin():
    assert reread.source_supports_field("SHOW_2_EXAMS_TOPOMETRIC", "topometric_RMin", "Indices (in 8 mm zone)")
    assert not reread.source_supports_field("SHOW_2_EXAMS_TOPOMETRIC", "topometric_RMin", "Cornea Back")
