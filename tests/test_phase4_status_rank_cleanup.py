"""Phase 4 lock for native canonical status aggregation."""
from pathlib import Path
from types import SimpleNamespace

import runtime_composition
import status_rank_policy
from clinical_disposition import combine_status as canonical_combine_status


ROOT = Path(__file__).resolve().parents[1]


def test_install_preserves_native_combine_status_identity():
    calls = []

    def native(current, new):
        calls.append((current, new))
        return canonical_combine_status(current, new)

    core = SimpleNamespace(combine_status=native)
    before = core.combine_status

    status_rank_policy.install(core)

    assert core.combine_status is before
    assert core.combine_status("PASS", "CAUTION") == "CAUTION"
    assert core.combine_status("CAUTION", "STOP-DEFER") == "STOP-DEFER"
    assert calls == [
        ("PASS", "CAUTION"),
        ("CAUTION", "STOP-DEFER"),
        ("PASS", "CAUTION"),
        ("CAUTION", "STOP-DEFER"),
    ]
    assert core._hc_status_rank_policy_installed is True


def test_production_core_uses_native_app_delegate():
    import app

    assert app.combine_status.__module__ == "app"
    assert app.combine_status("PASS", "CAUTION") == "CAUTION"
    assert app.combine_status("CAUTION", "STOP-DEFER") == "STOP-DEFER"


def test_status_rank_compatibility_module_is_not_in_production_composition():
    assert all(
        "status_rank_policy" not in modules
        for modules in runtime_composition.COMPOSITION_PHASES.values()
    )
    source = (ROOT / "runtime_composition.py").read_text(encoding="utf-8")
    assert "import status_rank_policy" not in source
    assert "status_rank_policy.install" not in source
