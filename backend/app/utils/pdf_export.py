"""ReportLab based PDF exporters for checklists and formal reports."""

import io
from datetime import date

from reportlab.graphics.shapes import Drawing, Line, Rect
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

NAVY = colors.HexColor("#0f172a")
AMBER = colors.HexColor("#f59e0b")

CHECKLIST_SECTION_TITLES = {
    "equipment_calibration": "1. Equipment & Calibration",
    "safety_precautions": "2. Safety Precautions",
    "dut_preparation": "3. DUT Preparation Steps",
}

REPORT_SECTION_TITLES = {
    "test_amaci": "1. Test Purpose",
    "test_kosullari": "2. Test Conditions",
    "olcum_sonuclari": "3. Measurement Results",
    "gozlemler": "4. Observations",
    "kabul_degerlendirme": "5. Acceptance Criteria Evaluation",
    "sonuc": "6. Result and Decision",
    "sapma_analizi": "7. Deviation Analysis and Corrective Action",
}


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TFTitle", parent=styles["Title"], textColor=AMBER, fontSize=26))
    styles.add(
        ParagraphStyle(
            name="TFSubtitle",
            parent=styles["Normal"],
            textColor=NAVY,
            fontSize=13,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TFSection",
            parent=styles["Heading2"],
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=6,
        )
    )
    styles.add(ParagraphStyle(name="TFItem", parent=styles["Normal"], fontSize=10, leading=14))
    styles.add(
        ParagraphStyle(
            name="TFNote",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.grey,
            leftIndent=14,
        )
    )
    return styles


def _checkbox_drawing(checked=False, size=10):
    drawing = Drawing(size + 4, size + 4)
    drawing.add(Rect(2, 2, size, size, strokeColor=NAVY, fillColor=None, strokeWidth=1.2))
    if checked:
        drawing.add(Line(2, 2, size + 2, size + 2, strokeColor=AMBER, strokeWidth=1.6))
        drawing.add(Line(2, size + 2, size + 2, 2, strokeColor=AMBER, strokeWidth=1.6))
    return drawing


def _add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"TestForge - Page {doc.page}")
    canvas.restoreState()


def build_checklist_pdf(checklist_data):
    """Build a pre-test checklist PDF and return a BytesIO buffer."""
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    story = []
    story.append(Paragraph("TestForge", styles["TFTitle"]))
    story.append(Paragraph("Pre-Test Checklist", styles["TFSubtitle"]))

    header_table = Table(
        [
            ["DUT", checklist_data.get("dut_name", "")],
            ["Test", checklist_data.get("test_name", "")],
            ["Standard Reference", checklist_data.get("standard_reference", "")],
        ],
        colWidths=[4 * cm, 12 * cm],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 0.6 * cm))

    sections = checklist_data.get("sections", {})
    for key, title in CHECKLIST_SECTION_TITLES.items():
        items = sections.get(key, [])
        story.append(Paragraph(title, styles["TFSection"]))
        if not items:
            story.append(Paragraph("No items available.", styles["TFItem"]))
            continue

        for item in items:
            if isinstance(item, dict):
                text = item.get("text", "")
                checked = bool(item.get("checked"))
                notes = item.get("notes", "")
            else:
                text = str(item)
                checked = False
                notes = ""

            row = [_checkbox_drawing(checked), Paragraph(text, styles["TFItem"])]
            item_table = Table([row], colWidths=[1.2 * cm, 14.8 * cm])
            item_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (0, 0), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            story.append(item_table)
            if notes:
                story.append(Paragraph(f"Note: {notes}", styles["TFNote"]))

    story.append(Spacer(1, 1.5 * cm))
    story.append(Paragraph("Signature", styles["TFSection"]))

    signature_table = Table(
        [
            ["Engineer Name:", checklist_data.get("engineer_name", "")],
            ["Date:", checklist_data.get("date", date.today().isoformat())],
            ["Signature:", "_______________________"],
        ],
        colWidths=[4 * cm, 12 * cm],
    )
    signature_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(signature_table)

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    buffer.seek(0)
    return buffer


def build_report_pdf(dut, test, result, report):
    """Build the formal test report PDF and return a BytesIO buffer."""
    styles = _styles()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    story = []
    story.append(Paragraph("TestForge", styles["TFTitle"]))
    story.append(Paragraph("Laboratory Test Report", styles["TFSubtitle"]))

    info_table = Table(
        [
            ["DUT", dut.get("name", "")],
            ["Part Number", dut.get("part_number", "")],
            ["Test", test.get("test_name", "")],
            ["Standard Reference", test.get("standard_reference", "")],
            ["Result", result.get("result", "")],
            ["Engineer", result.get("engineer_name", "")],
            ["Date", date.today().isoformat()],
        ],
        colWidths=[4 * cm, 12 * cm],
    )
    info_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ]
        )
    )
    story.append(info_table)
    story.append(Spacer(1, 0.6 * cm))

    measured_values = result.get("measured_values") or {}
    if measured_values:
        story.append(Paragraph("Measured Values", styles["TFSection"]))
        rows = [["Parameter", "Value"]] + [[str(k), str(v)] for k, v in measured_values.items()]
        mv_table = Table(rows, colWidths=[8 * cm, 8 * cm])
        mv_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(mv_table)
        story.append(Spacer(1, 0.4 * cm))

    sections = report.get("sections", {})
    for key, title in REPORT_SECTION_TITLES.items():
        if key in sections:
            story.append(Paragraph(title, styles["TFSection"]))
            story.append(Paragraph(sections[key], styles["TFItem"]))

    story.append(PageBreak())
    story.append(Paragraph("Signature", styles["TFSection"]))
    signature_table = Table(
        [
            ["Engineer Name:", result.get("engineer_name", "")],
            ["Date:", date.today().isoformat()],
            ["Signature:", "_______________________"],
        ],
        colWidths=[4 * cm, 12 * cm],
    )
    signature_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(signature_table)

    doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    buffer.seek(0)
    return buffer
