"""Composition root for CERAI runtime policy modules."""
import importlib

# Import app first so every policy module patches the same canonical module object.
import app as core

# Runtime policy modules. Order matters where wrappers are layered.
import extraction_guard  # noqa: F401
import erss_topography_guard  # noqa: F401
import erss_visual_morphology_policy  # noqa: F401
import randleman_bad_independence  # noqa: F401
import nice_policy  # noqa: F401
import erss_auto_read_policy  # noqa: F401
import assessment_workflow  # noqa: F401

__all__ = ["core"]
