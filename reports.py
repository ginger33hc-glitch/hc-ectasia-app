"""Canonical PDF and DOCX renderers for CER-AI.

Both formats consume the renderer-neutral payload created by
``clinical_core.report_payload``. This module formats already-computed values;
it contains no clinical threshold, score, formula, or disposition logic.
"""
from __future__ import annotations

from html import escape
from io import BytesIO
from pathlib import Path
from typing import Any, Mapping

import reportlab
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from cerai_i18n import authorship_notice, liability_notice, normalize_locale, translate_text


NAVY = "173B57"
GREEN = "176B3A"
GREEN_FILL = "E6F4EA"
AMBER = "B45309"
AMBER_FILL = "FFF2DB"
RED = "A31212"
RED_FILL = "FDE8E8"
GRAY = "52616D"
GRAY_FILL = "EEF2F5"
LINE = "D7E0E7"
INK = "17212B"
APP_VERSION = "0.7.71"
PROGRAM_NAME = "Cornea Ectasia Risk Assessment Intelligence"

PDF_UNICODE_REGULAR = "CER-AI-Vera"
PDF_UNICODE_BOLD = "CER-AI-Vera-Bold"
pdfmetrics.registerFont(TTFont(
    PDF_UNICODE_REGULAR,
    str(Path(reportlab.__file__).resolve().parent / "fonts" / "Vera.ttf"),
))
pdfmetrics.registerFont(TTFont(
    PDF_UNICODE_BOLD,
    str(Path(reportlab.__file__).resolve().parent / "fonts" / "VeraBd.ttf"),
))


class ReportContractError(ValueError):
    """The supplied assessment is not a complete canonical report snapshot."""


FIELD_LABELS = {
    "K1_D": "K1", "K1_axis_deg": "K1 axis", "K2_D": "K2",
    "K2_axis_deg": "K2 axis", "Kmean_D": "Km",
    "topographic_astig_D": "Astigmatism",
    "ml7_bad_k1_d": "ML7 K1 (BAD Display)",
    "ml7_bad_k2_d": "ML7 K2 (BAD Display)",
    "bad_flat_axis_deg": "PS3 BAD Axis (flat meridian, beside K1)",
    "topographic_steep_axis_deg": "Displayed steep/astigmatic axis",
    "Rmin_mm": "Posterior Rmin", "topometric_RMin": "Topometric RMin",
    "ISV": "ISV", "IVA": "IVA", "KI": "KI", "CKI": "CKI",
    "IHA": "IHA", "IHD": "IHD", "TKC": "TKC", "KISA": "KISA",
    "I_S": "Signed I-S", "central_pachy_um": "Pupil Center pachymetry",
    "pachy_thinnest_um": "Thinnest pachymetry", "Kmax_D": "Kmax (Front)",
    "corneal_diameter_mm": "HWTW", "F_Ele_Th_um": "F.Ele.Th",
    "B_Ele_Th_um": "B.Ele.Th", "PPI_min": "PPI Min",
    "PPI_avg": "PPI Avg", "PPI_max": "PPI Max", "ARTmax_um": "ARTmax",
    "Df": "Df", "Db": "Db", "Dp": "Dp", "Dt": "Dt", "Da": "Da",
    "BAD_D": "Final BAD-D", "srax_deg": "SRAX",
}
ERSS_LABELS = {
    "topography": "Topography", "RSB": "Residual stromal bed",
    "age": "Age", "pachymetry": "Preoperative pachymetry", "MRSE": "Manifest MRSE",
}


REPORT_BLANK_LINE_PT = 12


def _rl(value: str):
    return colors.HexColor(f"#{value}")


def _status_palette(value):
    """Presentation of an existing disposition; never infer or rescore risk."""
    return {
        "PASS": (GREEN, GREEN_FILL),
        "CAUTION": (AMBER, AMBER_FILL),
        "PASS WITH CAUTION": (AMBER, AMBER_FILL),
        "STOP-DEFER": (RED, RED_FILL),
    }.get(str(value).strip().upper().split(" / ")[-1])


def _cell_palette(row, index, selected_plan_status=None):
    label = str(row[0]).strip().lower()
    if label == "selected_plan" and str(row[1]) not in {"", "Not documented"} and selected_plan_status in {"PASS", "PASS WITH CAUTION"}:
        return _status_palette(selected_plan_status)
    if label in {"df", "db", "dp", "dt", "da", "ppi min", "ppi avg", "ppi max", "artmax"} and index > 0:
        classification = str(row[2]).split(" / ")[0]
        return {"NORMAL": (GREEN, GREEN_FILL),
                "SUSPICIOUS": (AMBER, AMBER_FILL),
                "ABNORMAL": (RED, RED_FILL)}.get(classification)
    if label == "procedure_transition":
        return AMBER, AMBER_FILL
    if "warning" in label and str(row[index]) not in {"", "Not documented"}:
        return AMBER, AMBER_FILL
    return _status_palette(row[index])


def _text(value: Any, fallback: str = "Not documented") -> str:
    if value is None or value == "":
        return fallback
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if isinstance(value, (list, tuple)):
        return "; ".join(_text(item) for item in value) or fallback
    if isinstance(value, Mapping):
        return "; ".join(f"{key}: {_text(item)}" for key, item in value.items()) or fallback
    return str(value)


def _provenance(entries: Any) -> str:
    if not entries:
        return "Not documented"
    rendered = []
    for item in entries if isinstance(entries, list) else [entries]:
        if isinstance(item, Mapping):
            parts = [str(item[key]) for key in ("source", "region", "file") if item.get(key)]
            rendered.append(" / ".join(parts) or _text(item))
        else:
            rendered.append(str(item))
    return "; ".join(rendered)


def _canonical_eyes(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    decision = payload.get("decision") or {}
    eyes = [eye for eye in decision.get("eyes") or [] if isinstance(eye, Mapping)]
    ordered = sorted(eyes, key=lambda item: {"OD": 0, "OS": 1}.get(str(item.get("eye")), 2))
    if not ordered:
        raise ReportContractError("A complete CER-AI report requires at least one assessed eye.")
    result = []
    for eye in ordered:
        report = eye.get("report_payload")
        if not isinstance(report, Mapping):
            raise ReportContractError(f"{eye.get('eye', 'Eye')}: canonical report payload is unavailable.")
        result.append(dict(report))
    return result


def assert_complete_report_payload(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Enforce the full-report gate without calculating clinical results."""
    reports = _canonical_eyes(payload)
    errors = []
    for report in reports:
        eye = report.get("eye") or "Eye"
        procedure = str(report.get("procedure") or "").upper()
        randleman = report.get("randleman")
        if procedure in {"LASIK", "PRK"} and (
            not isinstance(randleman, Mapping)
            or randleman.get("total") is None
            or any(value is None for value in (randleman.get("rows") or {}).values())
        ):
            errors.append(f"{eye}: Randleman/ERSS is incomplete")
        nice = report.get("nice") or {}
        if nice.get("total") is None or nice.get("missing"):
            errors.append(f"{eye}: NICE is incomplete")
        ps3 = report.get("ps3") or {}
        if not ps3.get("complete") or ps3.get("missing_keys"):
            errors.append(f"{eye}: PS3 is incomplete")
    if errors:
        raise ReportContractError("; ".join(errors))
    return reports


def _report_sections(report: Mapping[str, Any]) -> list[tuple[str, list[list[str]]]]:
    sections: list[tuple[str, list[list[str]]]] = []
    procedure = str(report.get("procedure") or "")
    randleman = report.get("randleman")
    if isinstance(randleman, Mapping):
        rows = [["Component", "Points"]]
        for key in ("topography", "RSB", "age", "pachymetry", "MRSE"):
            rows.append([ERSS_LABELS[key], _text((randleman.get("rows") or {}).get(key))])
        rows.extend([
            ["Total", _text(randleman.get("total"))],
            ["Topography category", _text(randleman.get("category"))],
            ["Disposition", _text(randleman.get("status"))],
        ])
    else:
        rows = [["Component", "Points"]] + [
            [ERSS_LABELS[key], "Not applicable to selected procedure"]
            for key in ("topography", "RSB", "age", "pachymetry", "MRSE")
        ]
        rows.append(["Disposition", "NOT APPLICABLE"])
    sections.append(("Randleman / ERSS", rows))

    nice = report.get("nice") or {}
    nice_rows = [["Component", "Input", "Points"]]
    value_keys = {"K2": "K2_D", "central_pachymetry": "central_pachy_um", "B_Ele_Th": "B_Ele_Th_um", "I_S": "I_S_D"}
    for key in ("K2", "central_pachymetry", "B_Ele_Th", "I_S"):
        nice_rows.append([key, _text((nice.get("values") or {}).get(value_keys[key])), _text((nice.get("rows") or {}).get(key))])
    nice_rows.extend([["Total", "", _text(nice.get("total"))], ["Classification", _text(nice.get("category")), _text(nice.get("status"))]])
    sections.append(("NICE", nice_rows))

    ps3 = report.get("ps3") or {}
    ps3_rows = [["Factor", "Status", "Exact finding"]]
    for finding in ps3.get("findings") or []:
        ps3_rows.append([_text(finding.get("key")), _text(finding.get("status")), _text(finding.get("detail"))])
    ps3_rows.extend([
        ["Moderate / High", _text(ps3.get("moderate_count")), _text(ps3.get("high_count"))],
        ["Procedure disposition", _text(ps3.get("status")), _text(ps3.get("disposition"))],
    ])
    sections.append(("PS3", ps3_rows))

    bad = report.get("bad") or {}
    context = bad.get("context") or {}
    bad_rows = [["Parameter", "Value", "Interpretation"], ["Final BAD-D", _text(bad.get("final_d")), f"{_text(bad.get('classification'))} / {_text(bad.get('status'))}"]]
    for label, key in (("Df", "df"), ("Db", "db"), ("Dp", "dp"), ("Dt", "dt"), ("Da", "da"),
                       ("PPI Min", "ppi_min"), ("PPI Avg", "ppi_avg"), ("PPI Max", "ppi_max"), ("ARTmax", "artmax_um")):
        interpretation = (bad.get("component_interpretations") or {}).get(key) or {}
        bad_rows.append([label, _text(context.get(key)),
                         f"{interpretation.get('classification', 'UNAVAILABLE')} / {interpretation.get('range', 'Not documented')}; information only"])
    sections.append(("Belin/Ambrósio BAD-D", bad_rows))

    safety = report.get("tissue_safety") or {}
    sections.append(("Procedural safety", [["Parameter", "Canonical result"]] + [[key, _text(value)] for key, value in safety.items()]))
    planning = report.get("planning") or {}
    planning_rows = [["Planning item", "Canonical result"], ["Procedure", procedure]] + [[key, _text(value)] for key, value in planning.items()]
    planning_rows.extend([[f"ML7 {key}", _text(value)] for key, value in (report.get("microkeratome_planning") or {}).items()])
    sections.append(("Procedure planning", planning_rows))

    drivers = report.get("decision_drivers") or {}
    driver_rows = [["Level", "Canonical decision driver"]]
    for level in ("stop", "caution", "incomplete"):
        driver_rows.extend([[level.upper(), _text(finding)] for finding in drivers.get(level) or []])
    sections.append(("Decision basis", driver_rows))

    values = report.get("source_values") or {}
    provenance = report.get("source_provenance") or {}
    source_rows = [["Canonical field", "Value", "Provenance"]] + [[FIELD_LABELS.get(key, key), _text(value), _provenance(provenance.get(key))] for key, value in values.items()]
    sections.append(("Canonical Pentacam values and provenance", source_rows))

    corrections = report.get("manual_corrections") or []
    if corrections:
        correction_rows = [["Field", "Original", "Surgeon-entered value", "Provenance"]]
        correction_rows.extend([[_text(item.get("field")), _text(item.get("original")), _text(item.get("value")), _text(item.get("label"))] for item in corrections])
        sections.append(("Surgeon-completed values", correction_rows))
    versions = report.get("versions") or {}
    sections.append(("Version provenance", [["Layer", "Version"]] + [[key, _text(value)] for key, value in versions.items()]))
    return sections


def canonical_report_model(payload: Mapping[str, Any]) -> dict[str, Any]:
    reports = assert_complete_report_payload(payload)
    decision = payload.get("decision") or {}
    return {
        "locale": normalize_locale(payload.get("locale")),
        "patient": dict(payload.get("patient") or {}),
        "status": decision.get("status"), "action": decision.get("action"),
        "identity_warnings": list(decision.get("identity_warnings") or []),
        "source_quality_warnings": list(decision.get("source_quality_warnings") or []),
        "eyes": [{"eye": report.get("eye"), "status": report.get("status"), "procedure": report.get("procedure"), "sections": _report_sections(report)} for report in reports],
    }


def _pdf_table(rows, styles, regular_font, bold_font, selected_plan_status=None):
    width = len(rows[0])
    col_widths = {2: [2.15 * inch, 4.0 * inch], 3: [1.35 * inch, 1.25 * inch, 3.55 * inch], 4: [1.25 * inch, 1.25 * inch, 1.7 * inch, 1.95 * inch]}[width]
    data = []
    highlights = []
    for row_index, row in enumerate(rows):
        cells = []
        for column, cell in enumerate(row):
            style = styles["Head"] if row_index == 0 else styles["Cell"]
            palette = _cell_palette(row, column, selected_plan_status) if row_index else None
            if palette:
                foreground, background = palette
                style = ParagraphStyle(name="StatusCell", parent=style, textColor=_rl(foreground))
                highlights.append(("BACKGROUND", (column, row_index), (column, row_index), _rl(background)))
            cells.append(Paragraph(escape(_text(cell, "")), style))
        data.append(cells)
    table = Table(data, colWidths=col_widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _rl(NAVY)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), bold_font), ("FONTNAME", (0, 1), (-1, -1), regular_font),
        ("GRID", (0, 0), (-1, -1), .35, _rl(LINE)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _rl("F7F9FB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ] + highlights))
    return table


def build_pdf(payload: Mapping[str, Any]) -> bytes:
    model = canonical_report_model(payload)
    locale = model["locale"]
    tr = lambda value: translate_text(value, locale)
    regular = PDF_UNICODE_REGULAR if locale == "tr" else "Helvetica"
    bold = PDF_UNICODE_BOLD if locale == "tr" else "Helvetica-Bold"
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CERTitle", parent=styles["Title"], fontName=bold, fontSize=17, leading=20, textColor=_rl(NAVY), spaceAfter=4))
    styles.add(ParagraphStyle(name="CERSection", parent=styles["Heading2"], fontName=bold, fontSize=10.5, leading=13, textColor=_rl(NAVY), spaceBefore=9, spaceAfter=4, keepWithNext=True))
    styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontName=regular, fontSize=7.3, leading=9, textColor=_rl(INK)))
    styles.add(ParagraphStyle(name="Head", parent=styles["BodyText"], fontName=bold, fontSize=7.3, leading=9, textColor=colors.white))
    styles.add(ParagraphStyle(name="Notice", parent=styles["BodyText"], fontName=bold, fontSize=8.5, leading=11, textColor=_rl(GRAY), backColor=_rl(GRAY_FILL), borderPadding=7, spaceAfter=8))
    styles.add(ParagraphStyle(name="Warning", parent=styles["Notice"], textColor=_rl(AMBER), backColor=_rl(AMBER_FILL)))
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, leftMargin=.65 * inch, rightMargin=.65 * inch, topMargin=.65 * inch, bottomMargin=.75 * inch)
    story = [Paragraph(tr("CER-AI PREOPERATIVE ECTASIA RISK ASSESSMENT"), styles["CERTitle"]), Paragraph(escape(PROGRAM_NAME), styles["Cell"]), Spacer(1, 6), Paragraph(escape(liability_notice(locale)), styles["Notice"])]
    story.append(Spacer(1, REPORT_BLANK_LINE_PT))
    patient = model["patient"]
    story.append(_pdf_table([
        [tr("Patient"), _text(patient.get("name")), tr("Patient ID"), _text(patient.get("id"))],
        [tr("Age"), _text(patient.get("age")), tr("Assessment date"), _text(patient.get("report_date"))],
        [tr("Reviewer"), _text(patient.get("reviewer")), tr("Overall disposition"), _text(model.get("status"))],
    ], styles, regular, bold))
    story.append(Spacer(1, REPORT_BLANK_LINE_PT))
    if model.get("action"):
        foreground, background = _status_palette(model.get("status")) or (GRAY, GRAY_FILL)
        action_style = ParagraphStyle(name="ResultNotice", parent=styles["Notice"], textColor=_rl(foreground), backColor=_rl(background))
        story.append(Paragraph(escape(_text(model["action"])), action_style))
    for warning in model["identity_warnings"] + model["source_quality_warnings"]:
        story.append(Paragraph(escape(_text(warning)), styles["Warning"]))
    for eye in model["eyes"]:
        if eye["eye"] == "OD":
            story.append(Spacer(1, 2 * REPORT_BLANK_LINE_PT))
        if eye["eye"] == "OS":
            story.append(PageBreak())
        foreground, _ = _status_palette(eye.get("status")) or (GRAY, GRAY_FILL)
        eye_style = ParagraphStyle(name="EyeResult", parent=styles["CERSection"], fontSize=15.75, leading=19.5, textColor=_rl(foreground))
        story.append(Paragraph(f"{escape(_text(eye['eye']))} — {escape(_text(eye['status']))}", eye_style))
        for title, rows in eye["sections"]:
            section_content = [Paragraph(escape(tr(title)), styles["CERSection"]),
                               _pdf_table(rows, styles, regular, bold, eye["status"] if title == "Procedure planning" and eye.get("procedure") == "LASIK" else None)]
            if title in {"Randleman / ERSS", "NICE", "PS3"}:
                story.append(KeepTogether(section_content))
            else:
                story.extend(section_content)

    def footer(canvas, pdf_doc):
        canvas.saveState(); canvas.setFont(regular, 6.2); canvas.setFillColor(_rl(GRAY))
        canvas.drawCentredString(4.25 * inch, .38 * inch, authorship_notice(locale))
        canvas.drawRightString(7.85 * inch, .2 * inch, f"{tr('Page')} {pdf_doc.page}"); canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()


def _shade(cell, fill):
    props = cell._tc.get_or_add_tcPr(); node = OxmlElement("w:shd"); node.set(qn("w:fill"), fill); props.append(node)


def _docx_table(document, rows, selected_plan_status=None):
    table = document.add_table(rows=1, cols=len(rows[0])); table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.LEFT
    for index, value in enumerate(rows[0]):
        table.rows[0].cells[index].text = _text(value, ""); _shade(table.rows[0].cells[index], NAVY)
        for run in table.rows[0].cells[index].paragraphs[0].runs:
            run.bold = True; run.font.color.rgb = RGBColor(255, 255, 255)
    for row in rows[1:]:
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cells[index].text = _text(value, "")
            palette = _cell_palette(row, index, selected_plan_status)
            if palette:
                foreground, background = palette
                _shade(cells[index], background)
                for run in cells[index].paragraphs[0].runs:
                    run.font.color.rgb = RGBColor.from_string(foreground)
    for row in table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                for run in paragraph.runs: run.font.name = "Arial"; run.font.size = Pt(8)
    return table


def build_docx(payload: Mapping[str, Any]) -> bytes:
    model = canonical_report_model(payload); locale = model["locale"]; tr = lambda value: translate_text(value, locale)
    document = Document(); document.core_properties.title = f"CER-AI — {PROGRAM_NAME}"
    section = document.sections[0]; section.left_margin = section.right_margin = Inches(.75)
    title = document.add_paragraph(); run = title.add_run(tr("CER-AI PREOPERATIVE ECTASIA RISK ASSESSMENT")); run.bold = True; run.font.size = Pt(18); run.font.color.rgb = RGBColor.from_string(NAVY)
    document.add_paragraph(PROGRAM_NAME)
    notice = document.add_paragraph(liability_notice(locale))
    for run in notice.runs: run.bold = True; run.font.color.rgb = RGBColor.from_string(GRAY)
    notice.paragraph_format.space_after = Pt(REPORT_BLANK_LINE_PT)
    patient = model["patient"]
    _docx_table(document, [
        [tr("Patient"), _text(patient.get("name")), tr("Patient ID"), _text(patient.get("id"))],
        [tr("Age"), _text(patient.get("age")), tr("Assessment date"), _text(patient.get("report_date"))],
        [tr("Reviewer"), _text(patient.get("reviewer")), tr("Overall disposition"), _text(model.get("status"))],
    ])
    gap = document.add_paragraph()
    gap.paragraph_format.line_spacing = Pt(REPORT_BLANK_LINE_PT)
    gap.paragraph_format.space_before = Pt(0)
    gap.paragraph_format.space_after = Pt(0)
    if model.get("action"):
        paragraph = document.add_paragraph(_text(model["action"]))
        foreground, _ = _status_palette(model.get("status")) or (GRAY, GRAY_FILL)
        for run in paragraph.runs:
            run.font.color.rgb = RGBColor.from_string(foreground)
    for warning in model["identity_warnings"] + model["source_quality_warnings"]:
        paragraph = document.add_paragraph(_text(warning))
        for run in paragraph.runs: run.bold = True; run.font.color.rgb = RGBColor.from_string(AMBER)
    for eye in model["eyes"]:
        paragraph = document.add_heading(f"{_text(eye['eye'])} — {_text(eye['status'])}", level=1)
        if eye["eye"] == "OD":
            paragraph.paragraph_format.space_before = Pt(2 * REPORT_BLANK_LINE_PT)
        if eye["eye"] == "OS":
            paragraph.paragraph_format.page_break_before = True
        foreground, _ = _status_palette(eye.get("status")) or (GRAY, GRAY_FILL)
        for run in paragraph.runs:
            run.font.color.rgb = RGBColor.from_string(foreground)
            run.font.size = Pt(document.styles["Heading 1"].font.size.pt * 1.5)
        for heading, rows in eye["sections"]:
            document.add_heading(tr(heading), level=2); _docx_table(document, rows, eye["status"] if heading == "Procedure planning" and eye.get("procedure") == "LASIK" else None)
    footer = section.footer.paragraphs[0]; footer.alignment = WD_ALIGN_PARAGRAPH.CENTER; footer.add_run(authorship_notice(locale))
    output = BytesIO(); document.save(output); return output.getvalue()
