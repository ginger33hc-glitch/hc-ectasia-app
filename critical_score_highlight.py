"""Runtime composition for CER-AI score/report presentation policy.

Frontend assets are committed under ``static/`` and are never rewritten during
module import. Version ownership remains exclusively in canonical_engine.py.
"""
import bootstrap
import reports

bootstrap.core.build_pdf = reports.build_pdf
bootstrap.core.build_docx = reports.build_docx
app = bootstrap.app
