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
PROGRAM_NAME = "Corneal Ectasia Risk Assessment Intelligence"

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
    "ml7_k1_d": "ML7 K1 (Four Maps Anterior Sagittal Curvature)",
    "ml7_k2_d": "ML7 K2 (Four Maps Anterior Sagittal Curvature)",
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


# Measurement values, original source evidence, filenames and version identifiers
# are audit data, not translation input. Both renderers use the same protection.
PATIENT_LITERAL_CELLS = frozenset({(0, 1), (0, 3), (1, 1), (1, 3), (2, 1)})
PROTECTED_COLUMNS = {
    "Canonical Pentacam values and provenance": (1, 2),
    "Surgeon-completed values": (1, 2),
    "Version provenance": (1,),
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
    safe_plan_rows = {
        "selected lasik plan",
        "ml7 preferred hinge location",
        "ml7 vacuum ring",
        "ml7 vacuum pressure",
    }
    if (
        label in safe_plan_rows
        and str(row[1]) not in {"", "Not documented"}
        and selected_plan_status in {"PASS", "PASS WITH CAUTION", "CAUTION"}
    ):
        return GREEN, GREEN_FILL
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
        bad = report.get("bad") or {}
        if bad.get("final_d") is None or bad.get("classification") == "UNAVAILABLE":
            errors.append(f"{eye}: Final BAD-D is incomplete")
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
    ps3_decision = ps3.get("decision") or {}
    ps3_disposition_detail = ps3_decision.get("detail") or _text(ps3.get("disposition"))
    ps3_rows.extend([
        ["Moderate / High", _text(ps3.get("moderate_count")), _text(ps3.get("high_count"))],
        ["Procedure disposition", _text(ps3.get("status")), ps3_disposition_detail],
    ])
    sections.append(("PS3", ps3_rows))

    disparity = report.get("astigmatic_disparity") or {}
    if disparity:
        disparity_rows = [
            ["Status", "Magnitude difference", "Axis difference"],
            [
                _text(disparity.get("status")),
                _text(disparity.get("magnitude_difference_d")),
                _text(disparity.get("axis_difference_deg")),
            ],
            ["Interpretation", _text(disparity.get("detail")), "Non-scoring; no independent procedure restriction"],
        ]
        sections.append(("Astigmatic disparity validation", disparity_rows))

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
    planning_rows = [["Planning item", "Canonical result"], ["Procedure", procedure]]
    for key, value in planning.items():
        if key == "selected_plan_definition":
            continue
        if key == "selected_plan":
            value = planning.get("selected_plan_definition") or value
            key = "Selected LASIK plan"
        elif key == "selection_rule":
            key = "Plan-selection priority"
        planning_rows.append([key, _text(value)])
    ml7_labels = {
        "hinge_location_preference": "Preferred hinge location",
        "vacuum_ring_mm": "Vacuum ring",
        "vacuum_pressure_mmhg": "Vacuum pressure",
    }
    planning_rows.extend([
        [f"ML7 {ml7_labels.get(key, key)}", _text(value)]
        for key, value in (report.get("microkeratome_planning") or {}).items()
    ])
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


TABLE_WIDTHS_IN = {2: [2.15, 4.0], 3: [1.35, 1.25, 3.55], 4: [1.25, 1.25, 1.7, 1.95]}


def _cell_text(value, locale, literal=False):
    text = _text(value, "")
    # Missing markers are presentation text even inside protected metadata.
    return text if literal and text != "Not documented" else translate_text(text, locale)


def _pdf_table(rows, styles, regular_font, bold_font, selected_plan_status=None, locale="en", protected_columns=(), protected_cells=()):
    width = len(rows[0])
    col_widths = [value * inch for value in TABLE_WIDTHS_IN[width]]
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
            cell_text = _cell_text(cell, locale, (row_index, column) in protected_cells or (row_index > 0 and column in protected_columns))
            cells.append(Paragraph(escape(cell_text), style))
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
    story = [Paragraph(tr("CER-AI PREOPERATIVE ECTASIA RISK ASSESSMENT"), styles["CERTitle"]), Paragraph(escape(tr(PROGRAM_NAME)), styles["Cell"]), Spacer(1, 6), Paragraph(escape(liability_notice(locale)), styles["Notice"])]
    story.append(Spacer(1, REPORT_BLANK_LINE_PT))
    patient = model["patient"]
    story.append(_pdf_table([
        [tr("Patient"), _text(patient.get("name"), tr("Not documented")), tr("Patient ID"), _text(patient.get("id"), tr("Not documented"))],
        [tr("Age"), _text(patient.get("age"), tr("Not documented")), tr("Assessment date"), _text(patient.get("report_date"), tr("Not documented"))],
        [tr("Reviewer"), _text(patient.get("reviewer"), tr("Not documented")), tr("Overall disposition"), _text(model.get("status"))],
    ], styles, regular, bold, locale=locale, protected_cells=PATIENT_LITERAL_CELLS))
    story.append(Spacer(1, REPORT_BLANK_LINE_PT))
    if model.get("action"):
        foreground, background = _status_palette(model.get("status")) or (GRAY, GRAY_FILL)
        action_style = ParagraphStyle(name="ResultNotice", parent=styles["Notice"], textColor=_rl(foreground), backColor=_rl(background))
        story.append(Paragraph(escape(tr(_text(model["action"]))), action_style))
    for warning in model["identity_warnings"] + model["source_quality_warnings"]:
        story.append(Paragraph(escape(tr(_text(warning))), styles["Warning"]))
    for eye in model["eyes"]:
        if eye["eye"] == "OD":
            story.append(Spacer(1, 2 * REPORT_BLANK_LINE_PT))
        if eye["eye"] == "OS":
            story.append(PageBreak())
        foreground, _ = _status_palette(eye.get("status")) or (GRAY, GRAY_FILL)
        eye_style = ParagraphStyle(name="EyeResult", parent=styles["CERSection"], fontSize=15.75, leading=19.5, textColor=_rl(foreground))
        story.append(Paragraph(f"{escape(_text(eye['eye']))} — {escape(tr(_text(eye['status'])))}", eye_style))
        for title, rows in eye["sections"]:
            section_content = [Paragraph(escape(tr(title)), styles["CERSection"]),
                               _pdf_table(rows, styles, regular, bold, eye["status"] if title == "Procedure planning" and eye.get("procedure") == "LASIK" else None,
                                          locale=locale, protected_columns=PROTECTED_COLUMNS.get(title, ()))]
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
    props = cell._tc.get_or_add_tcPr()
    for old in props.findall(qn("w:shd")):
        props.remove(old)
    node = OxmlElement("w:shd"); node.set(qn("w:fill"), fill); props.append(node)


def _docx_notice(document, text, foreground, background):
    paragraph = document.add_paragraph(text)
    paragraph.paragraph_format.line_spacing = Pt(11)
    paragraph.paragraph_format.space_after = Pt(8)
    node = OxmlElement("w:shd"); node.set(qn("w:fill"), background)
    paragraph._p.get_or_add_pPr().append(node)
    for run in paragraph.runs:
        run.bold = True; run.font.size = Pt(8.5); run.font.color.rgb = RGBColor.from_string(foreground)
    return paragraph


def _docx_table(document, rows, selected_plan_status=None, keep_together=False, locale="en", protected_columns=(), protected_cells=()):
    table = document.add_table(rows=1, cols=len(rows[0])); table.style = "Table Grid"; table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = False
    widths = TABLE_WIDTHS_IN[len(rows[0])]
    for column, width in zip(table.columns, widths):
        column.width = Inches(width)
    props = table._tbl.tblPr
    props.find(qn("w:tblW")).set(qn("w:w"), str(round(sum(widths) * 1440)))
    props.find(qn("w:tblW")).set(qn("w:type"), "dxa")
    margins = OxmlElement("w:tblCellMar")
    for side, points in (("top", 4), ("bottom", 4), ("left", 5), ("right", 5)):
        node = OxmlElement(f"w:{side}"); node.set(qn("w:w"), str(points * 20)); node.set(qn("w:type"), "dxa"); margins.append(node)
    props.append(margins)
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "bottom", "left", "right", "insideH", "insideV"):
        node = OxmlElement(f"w:{side}"); node.set(qn("w:val"), "single"); node.set(qn("w:sz"), "3"); node.set(qn("w:color"), LINE); borders.append(node)
    props.append(borders)
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    for index, value in enumerate(rows[0]):
        table.rows[0].cells[index].text = _cell_text(value, locale, (0, index) in protected_cells); _shade(table.rows[0].cells[index], NAVY)
        for run in table.rows[0].cells[index].paragraphs[0].runs:
            run.bold = True; run.font.color.rgb = RGBColor(255, 255, 255)
    for row_number, row in enumerate(rows[1:], 1):
        cells = table.add_row().cells
        for index, value in enumerate(row):
            cell_text = _cell_text(value, locale, (row_number, index) in protected_cells or index in protected_columns)
            cells[index].text = cell_text
            _shade(cells[index], "FFFFFF" if row_number % 2 else "F7F9FB")
            palette = _cell_palette(row, index, selected_plan_status)
            if palette:
                foreground, background = palette
                _shade(cells[index], background)
                for run in cells[index].paragraphs[0].runs:
                    run.font.color.rgb = RGBColor.from_string(foreground)
    for row_number, row in enumerate(table.rows):
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        for cell, width in zip(row.cells, widths):
            cell.width = Inches(width)
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.line_spacing = Pt(9)
                paragraph.paragraph_format.keep_with_next = row_number == 0 or (keep_together and row_number < len(table.rows) - 1)
                for run in paragraph.runs: run.font.name = "Arial"; run.font.size = Pt(7.3)
    return table


def build_docx(payload: Mapping[str, Any]) -> bytes:
    model = canonical_report_model(payload); locale = model["locale"]; tr = lambda value: translate_text(value, locale)
    document = Document(); document.core_properties.title = f"CER-AI — {PROGRAM_NAME}"; document.core_properties.language = "tr-TR" if locale == "tr" else "en-US"
    section = document.sections[0]
    section.page_width = Inches(8.5); section.page_height = Inches(11)
    section.left_margin = section.right_margin = section.top_margin = Inches(.65)
    section.bottom_margin = Inches(.75); section.footer_distance = Inches(.2)
    normal = document.styles["Normal"]
    language = OxmlElement("w:lang"); language.set(qn("w:val"), "tr-TR" if locale == "tr" else "en-US")
    normal.element.get_or_add_rPr().append(language)
    normal.font.name = "Arial"; normal.font.size = Pt(7.3); normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(0); normal.paragraph_format.line_spacing = Pt(9)
    for name in ("Heading 1", "Heading 2"):
        style = document.styles[name]; style.font.name = "Arial"; style.font.bold = True
        style.font.size = Pt(10.5); style.font.color.rgb = RGBColor.from_string(NAVY)
        style.paragraph_format.line_spacing = Pt(13)
        style.paragraph_format.space_before = Pt(9); style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.keep_with_next = True
    title = document.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.line_spacing = Pt(20); title.paragraph_format.space_after = Pt(4)
    run = title.add_run(tr("CER-AI PREOPERATIVE ECTASIA RISK ASSESSMENT")); run.bold = True; run.font.size = Pt(17); run.font.color.rgb = RGBColor.from_string(NAVY)
    subtitle = document.add_paragraph(tr(PROGRAM_NAME)); subtitle.paragraph_format.space_after = Pt(6)
    notice = _docx_notice(document, liability_notice(locale), GRAY, GRAY_FILL)
    notice.paragraph_format.space_after = Pt(8 + REPORT_BLANK_LINE_PT)
    patient = model["patient"]
    _docx_table(document, [
        [tr("Patient"), _text(patient.get("name"), tr("Not documented")), tr("Patient ID"), _text(patient.get("id"), tr("Not documented"))],
        [tr("Age"), _text(patient.get("age"), tr("Not documented")), tr("Assessment date"), _text(patient.get("report_date"), tr("Not documented"))],
        [tr("Reviewer"), _text(patient.get("reviewer"), tr("Not documented")), tr("Overall disposition"), _text(model.get("status"))],
    ], locale=locale, protected_cells=PATIENT_LITERAL_CELLS)
    gap = document.add_paragraph()
    gap.paragraph_format.line_spacing = Pt(REPORT_BLANK_LINE_PT)
    gap.paragraph_format.space_before = Pt(0)
    gap.paragraph_format.space_after = Pt(0)
    if model.get("action"):
        foreground, background = _status_palette(model.get("status")) or (GRAY, GRAY_FILL)
        _docx_notice(document, tr(_text(model["action"])), foreground, background)
    for warning in model["identity_warnings"] + model["source_quality_warnings"]:
        _docx_notice(document, tr(_text(warning)), AMBER, AMBER_FILL)
    for eye in model["eyes"]:
        paragraph = document.add_heading(f"{_text(eye['eye'])} — {tr(_text(eye['status']))}", level=1)
        paragraph.paragraph_format.line_spacing = Pt(19.5)
        if eye["eye"] == "OD":
            paragraph.paragraph_format.space_before = Pt(2 * REPORT_BLANK_LINE_PT)
        if eye["eye"] == "OS":
            paragraph.paragraph_format.page_break_before = True
        foreground, _ = _status_palette(eye.get("status")) or (GRAY, GRAY_FILL)
        for run in paragraph.runs:
            run.font.color.rgb = RGBColor.from_string(foreground)
            run.font.size = Pt(15.75)
        for heading, rows in eye["sections"]:
            document.add_heading(tr(heading), level=2)
            _docx_table(document, rows, eye["status"] if heading == "Procedure planning" and eye.get("procedure") == "LASIK" else None, keep_together=heading in {"Randleman / ERSS", "NICE", "PS3"}, locale=locale, protected_columns=PROTECTED_COLUMNS.get(heading, ()))
    footer = section.footer.paragraphs[0]; footer.alignment = WD_ALIGN_PARAGRAPH.CENTER; footer.add_run(authorship_notice(locale))
    for run in footer.runs: run.font.size = Pt(6.2); run.font.color.rgb = RGBColor.from_string(GRAY)
    page = section.footer.add_paragraph(tr("Page") + " "); page.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    field = OxmlElement("w:fldSimple"); field.set(qn("w:instr"), "PAGE"); page._p.append(field)
    for run in page.runs: run.font.size = Pt(6.2); run.font.color.rgb = RGBColor.from_string(GRAY)
    output = BytesIO(); document.save(output); return output.getvalue()
