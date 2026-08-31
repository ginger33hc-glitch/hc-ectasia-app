"""Composition root for the canonical CERAI runtime.

Policy modules are imported explicitly by start.py/app runtime; this module only
exposes the canonical app module object to policy modules without creating a
second runtime instance.
"""
import app as core

__all__ = ["core"]
