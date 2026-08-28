import json
import struct
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from canonical_engine import core as app
import reports
from docx import Document
from docx.shared import Pt
from fastapi.testclient import TestClient
from pypdf import PdfReader

# NOTE: remainder of this regression module intentionally unchanged.
# It must execute against the canonical production core, never bare app.py.

