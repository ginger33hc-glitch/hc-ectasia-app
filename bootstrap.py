from importlib import import_module

# Canonical runtime module.
core = import_module("app")

# Install policy modules in the established order.  Each module patches the same
# canonical app module object; this file is intentionally small so start.py and
# tests import a single composed runtime.
for module_name in (
    "extraction_guard",
    "erss_topography_guard",
    "erss_visual_morphology_policy",
    "randleman_bad_independence",
    "nice_policy",
    "erss_auto_read_policy",
    "assessment_workflow",
):
    import_module(module_name)

__all__ = ["core"]
