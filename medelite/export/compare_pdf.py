"""Comparison PDF export (reportlab) for the compare-facilities mode.

Renders a landscape table -- one row per metric, one column per facility -- so several
facilities can be evaluated side by side on a single page.
"""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from medelite import config, presentation

_COMPARE_LABELS = [
    "Location",
    "Census Capacity",
    "Overall Star Rating",
    "Health Inspection",
    "Staffing",
    "Quality of Resident Care",
    "Short Term Hospitalization",
    "STR ED Visit",
    "LT Hospitalization",
    "ED Visit",
]


def build_comparison_pdf(reports) -> bytes:
    """Render a side-by-side facility comparison to PDF bytes (landscape)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(letter),
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title="Facility Comparison",
    )

    styles = getSampleStyleSheet()
    brand_style = ParagraphStyle(
        "BrandTitle", parent=styles["Title"], fontSize=18, alignment=TA_CENTER,
        textColor=colors.HexColor(config.BRAND_COLOR),
    )
    sub_style = ParagraphStyle(
        "Sub", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, textColor=colors.grey,
    )
    cell_style = ParagraphStyle("Cell", parent=styles["Normal"], fontSize=8, leading=10)
    label_style = ParagraphStyle("Label", parent=cell_style, fontName="Helvetica-Bold")
    head_style = ParagraphStyle(
        "Head", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white,
    )

    rowmaps = [dict(presentation.all_rows(rep)) for rep in reports]

    header = [Paragraph("Metric", head_style)]
    for rep in reports:
        header.append(Paragraph(f"{rep.facility_name}<br/>({rep.ccn})", head_style))
    table_data = [header]
    for label in _COMPARE_LABELS:
        row = [Paragraph(label, label_style)]
        for rowmap in rowmaps:
            row.append(Paragraph(str(rowmap.get(label, "N/A")), cell_style))
        table_data.append(row)

    page_width = landscape(letter)[0] - inch  # usable width after L+R margins
    label_w = 1.7 * inch
    fac_w = (page_width - label_w) / max(1, len(reports))
    col_widths = [label_w] + [fac_w] * len(reports)

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(config.BRAND_COLOR)),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#F5F6FA")),
            ("ROWBACKGROUNDS", (1, 1), (-1, -1), [colors.white, colors.HexColor("#FAFAFC")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D9D9E3")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])
    )

    elements = [
        Paragraph(f"{config.BRAND_PLATFORM} &mdash; Facility Comparison", brand_style),
        Paragraph(config.BRAND_TAGLINE, sub_style),
        Spacer(1, 14),
        table,
    ]
    doc.build(elements)
    return buf.getvalue()
