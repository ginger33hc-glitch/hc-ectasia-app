"""Runtime composition for CERAI score/report presentation policy.

Frontend assets are committed under ``static/`` and are never rewritten during
module import. Version ownership remains exclusively in canonical_engine.py.
"""
import hc_age_policy  # noqa: F401
import hc_bad_final_policy  # noqa: F401
import bootstrap
import merge_policy_base  # noqa: F401
import extraction_guard  # noqa: F401
import erss_topography_guard  # noqa: F401
import report_export_guard  # noqa: F401
import reports

bootstrap.core.build_pdf = reports.build_pdf
bootstrap.core.build_docx = reports.build_docx
app = bootstrap.app
