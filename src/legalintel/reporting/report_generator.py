"""Generates a downloadable PDF report summarizing one matter's analyzed
documents and tracked dockets, for handing to a client/partner without app
access. Pure function over already-fetched data — no DB access here; see
app/api/routes/matters.py for the composition."""

import io
from datetime import datetime
from xml.sax.saxutils import escape as _xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from legalintel.models.docket import DocketAlert, TrackedDocket
from legalintel.models.document import (
    ClauseExtractionResult,
    ClauseMatch,
    DocumentClassificationResult,
    ParsedDocument,
)
from legalintel.models.matter import MatterDetail, MatterDocument

DISCLAIMER = (
    "This report was generated automatically from AI-assisted document analysis "
    "(clause extraction, risk flagging, and document classification) and docket "
    "monitoring data. It is a first-pass summary only, not legal advice, and has "
    "not been independently verified by an attorney. All findings should be "
    "reviewed by qualified counsel before being relied upon."
)

_styles = getSampleStyleSheet()
_TITLE = ParagraphStyle("ReportTitle", parent=_styles["Title"], fontSize=20, spaceAfter=4)
_META = ParagraphStyle("ReportMeta", parent=_styles["Normal"], textColor=colors.grey, spaceAfter=12)
_H2 = ParagraphStyle("ReportH2", parent=_styles["Heading2"], spaceBefore=18, spaceAfter=8)
_H3 = ParagraphStyle("ReportH3", parent=_styles["Heading3"], spaceBefore=12, spaceAfter=4)
_BODY = _styles["Normal"]
_CELL = ParagraphStyle("TableCell", parent=_styles["Normal"], fontSize=8, leading=10)
_DISCLAIMER_STYLE = ParagraphStyle(
    "Disclaimer", parent=_styles["Italic"], fontSize=8, textColor=colors.grey, spaceBefore=24
)

_TABLE_STYLE = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
)


def _p(text: str, style: ParagraphStyle = _CELL) -> Paragraph:
    """Wrap plain text as a Paragraph flowable (escaping XML-special chars) so
    it wraps inside a fixed-width table cell instead of overflowing it — a
    raw string in a Table cell does not wrap in reportlab.platypus."""
    return Paragraph(_xml_escape(text), style)


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def generate_matter_report(detail: MatterDetail, alerts_by_docket_id: dict[int, list[DocketAlert]]) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f"Matter Report - {detail.matter.name}",
    )

    story: list[Flowable] = [Paragraph(_xml_escape(detail.matter.name), _TITLE)]
    if detail.matter.description:
        story.append(Paragraph(_xml_escape(detail.matter.description), _BODY))
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    story.append(Paragraph(f"Generated {generated_at}", _META))

    story.append(Paragraph("Analyzed Documents", _H2))
    if not detail.documents:
        story.append(Paragraph("No documents have been analyzed for this matter yet.", _BODY))
    for doc in detail.documents:
        story.extend(_document_section(doc))

    story.append(Paragraph("Tracked Dockets", _H2))
    if not detail.tracked_dockets:
        story.append(Paragraph("No dockets are tracked for this matter yet.", _BODY))
    for docket in detail.tracked_dockets:
        story.extend(_docket_section(docket, alerts_by_docket_id.get(docket.id, [])))

    story.append(Spacer(1, 24))
    story.append(Paragraph(DISCLAIMER, _DISCLAIMER_STYLE))

    document.build(story)
    return buffer.getvalue()


def _document_section(doc: MatterDocument) -> list[Flowable]:
    flowables: list[Flowable] = [
        Paragraph(_xml_escape(doc.source_filename), _H3),
        Paragraph(f"Analysis type: {doc.analysis_type}", _META),
    ]

    if doc.analysis_type == "parse":
        parsed = ParsedDocument.model_validate(doc.result)
        flowables.append(_p(_truncate(parsed.full_text, 800), _BODY))

    elif doc.analysis_type == "extract_clauses":
        result = ClauseExtractionResult.model_validate(doc.result)
        summary = result.risk_summary
        flowables.append(
            Paragraph(
                f"Highest risk: {summary.highest_risk_level or 'None'} — "
                f"HIGH: {summary.counts_by_level['HIGH']}, "
                f"MEDIUM: {summary.counts_by_level['MEDIUM']}, "
                f"INFORMATIONAL: {summary.counts_by_level['INFORMATIONAL']}",
                _BODY,
            )
        )
        flowables.append(Spacer(1, 6))
        flowables.append(_clause_table(result.clauses) if result.clauses else Paragraph("No clauses matched.", _BODY))

    elif doc.analysis_type == "classify":
        result = DocumentClassificationResult.model_validate(doc.result)
        c = result.classification
        flowables.append(Paragraph(f"Predicted type: {c.predicted_type} ({c.confidence:.0%})", _BODY))
        rows = [[_p("Type"), _p("Probability")]] + [
            [_p(t), _p(f"{c.probabilities.get(t, 0):.0%}")] for t in ("Contract", "Email", "Other")
        ]
        table = Table(rows, colWidths=[2 * inch, 2 * inch])
        table.setStyle(_TABLE_STYLE)
        flowables.append(table)

    flowables.append(Spacer(1, 10))
    return flowables


def _clause_table(clauses: list[ClauseMatch]) -> Table:
    rows = [[_p("Category"), _p("Risk"), _p("Confidence"), _p("Text")]]
    for clause in clauses:
        rows.append(
            [
                _p(clause.category),
                _p(clause.risk_level or "—"),
                _p(f"{clause.confidence:.0%} ({clause.confidence_band or '—'})"),
                _p(_truncate(clause.text, 300)),
            ]
        )
    # Column widths sum to 6.5in, within the 7.0in usable width (LETTER 8.5in - 1.5in margins).
    # Risk gets 1.1in since "INFORMATIONAL" is the longest possible value in that column.
    table = Table(rows, colWidths=[1.2 * inch, 1.1 * inch, 0.9 * inch, 3.3 * inch], repeatRows=1)
    table.setStyle(_TABLE_STYLE)
    return table


def _docket_section(docket: TrackedDocket, alerts: list[DocketAlert]) -> list[Flowable]:
    title = docket.case_name or f"Docket {docket.courtlistener_docket_id}"
    flowables: list[Flowable] = [Paragraph(_xml_escape(title), _H3)]

    meta_bits = []
    if docket.docket_number:
        meta_bits.append(f"Docket #: {docket.docket_number}")
    if docket.court:
        meta_bits.append(f"Court: {docket.court}")
    meta_bits.append(
        f"Last checked: {docket.last_checked_at.strftime('%Y-%m-%d %H:%M') if docket.last_checked_at else 'never'}"
    )
    flowables.append(Paragraph(_xml_escape(" | ".join(meta_bits)), _META))

    if alerts:
        rows = [[_p("Alert Date"), _p("New Entries")]] + [
            [_p(a.created_at.strftime("%Y-%m-%d %H:%M")), _p(str(a.new_entry_count))] for a in alerts
        ]
        table = Table(rows, colWidths=[2.5 * inch, 2 * inch])
        table.setStyle(_TABLE_STYLE)
        flowables.append(table)
    else:
        flowables.append(Paragraph("No alerts recorded.", _BODY))

    flowables.append(Spacer(1, 10))
    return flowables
