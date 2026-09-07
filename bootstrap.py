"""Compatibility bootstrap for CER-AI.

All extraction schema, prompt, merge, and clinical ownership lives in canonical modules.
This module only preserves the historical import surface used by runtime composition.
"""

import app as core

app = core.app
