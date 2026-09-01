"""Runtime composition for CER-AI score/report presentation policy.

Frontend assets are committed under ``static/`` and are never rewritten during
module import. Version ownership remains exclusively in canonical_engine.py.
"""


def install(core, report_builders) -> None:
    """Attach the active report builders explicitly and at most once."""
    if getattr(core, "_cerai_report_builders_installed", False):
        return
    core.build_pdf = report_builders.build_pdf
    core.build_docx = report_builders.build_docx
    core._cerai_report_builders_installed = True
