"""PDF export (reportlab).

Render a ReportModel as a downloadable Facility Assessment Snapshot that mirrors the on-screen
layout: branded header, the 2-column table (shared rows via presentation.mvp_rows), and a clickable
Medicare Care Compare link. Output is vector text (selectable, print-ready), not a rasterized image.
"""
from __future__ import annotations

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from medelite import config, presentation
from medelite.models import ReportModel

_LABEL_BG = colors.HexColor("#F5F6FA")
_BORDER = colors.HexColor("#D9D9E3")
_INK = colors.HexColor("#1A1A2E")
_GREY = colors.HexColor("#666666")
_LINK = colors.HexColor("#1A73E8")


def build_pdf(rep: ReportModel) -> bytes:
    """Render the report to PDF bytes (clickable Medicare link, vector text)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
        title="Facility Assessment Snapshot",
        author="Medelite",
    )
    ss = getSampleStyleSheet()
    brand = ParagraphStyle("brand", parent=ss["Title"], alignment=TA_CENTER, fontSize=22, spaceAfter=2)
    rep_title = ParagraphStyle(
        "rep_title", parent=ss["Normal"], alignment=TA_CENTER,
        fontName="Helvetica-Bold", fontSize=12, textColor=_INK, spaceAfter=12,
    )
    facility = ParagraphStyle("facility", parent=ss["Heading2"], fontSize=13, textColor=_INK, spaceBefore=2, spaceAfter=8)
    cell = ParagraphStyle("cell", parent=ss["Normal"], fontSize=9, leading=12)
    label = ParagraphStyle("label", parent=cell, fontName="Helvetica-Bold")
    link = ParagraphStyle("link", parent=ss["Normal"], fontSize=10)
    note = ParagraphStyle("note", parent=ss["Normal"], fontSize=8, textColor=colors.HexColor("#999999"), spaceBefore=10)

    story = [
        Paragraph(
            f'<font color="{config.BRAND_COLOR}"><b>{escape(config.BRAND_PLATFORM)}</b></font>'
            f'  <font size="10" color="#666666">{escape(config.BRAND_TAGLINE)}</font>',
            brand,
        ),
        Paragraph(escape(config.REPORT_TITLE), rep_title),
        Paragraph(escape(rep.facility_name), facility),
    ]

    data = [
        [Paragraph(escape(lbl), label), Paragraph(escape(val), cell)]
        for lbl, val in presentation.mvp_rows(rep)
    ]
    table = Table(data, colWidths=[3.1 * inch, 3.6 * inch])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
                ("BACKGROUND", (0, 0), (0, -1), _LABEL_BG),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            f'<a href="{escape(rep.medicare_url)}" color="#1A73E8">View on Medicare Care Compare</a>',
            link,
        )
    )
    if not rep.cms_record_found:
        story.append(
            Paragraph("No CMS record found for this CCN; values shown are from manual inputs.", note)
        )

    doc.build(story)
    return buf.getvalue()
