import io
from datetime import datetime, timezone

import pdfplumber
import pytest

from legalintel.models.docket import DocketAlert, TrackedDocket
from legalintel.models.document import (
    ClauseExtractionResult,
    ClauseMatch,
    DocumentClassification,
    DocumentClassificationResult,
    ParsedDocument,
    RiskSummary,
)
from legalintel.models.matter import Matter, MatterDetail, MatterDocument
from legalintel.reporting import generate_matter_report

NOW = datetime.now(timezone.utc)


def _parsed_document(text: str = "This is the full contract text.") -> ParsedDocument:
    return ParsedDocument(source_filename="sample.pdf", file_type="pdf", pages=[], full_text=text)


@pytest.fixture
def matter_detail() -> MatterDetail:
    matter = Matter(id=1, name="Acme v. Beta", description="Contract dispute", created_at=NOW)

    parse_doc = MatterDocument(
        id=1,
        matter_id=1,
        source_filename="notes.pdf",
        analysis_type="parse",
        result=_parsed_document().model_dump(mode="json"),
        created_at=NOW,
    )

    clause_result = ClauseExtractionResult(
        document=_parsed_document(),
        clauses=[
            ClauseMatch(
                category="Uncapped Liability",
                text="Liability shall be uncapped for breach of confidentiality.",
                confidence=0.97,
                char_start=0,
                char_end=10,
                risk_level="HIGH",
                confidence_band="HIGH",
            ),
            ClauseMatch(
                category="Governing Law",
                text="This Agreement is governed by the laws of Delaware.",
                confidence=0.6,
                char_start=20,
                char_end=30,
                risk_level="INFORMATIONAL",
                confidence_band="MEDIUM",
            ),
        ],
        risk_summary=RiskSummary(highest_risk_level="HIGH", counts_by_level={"HIGH": 1, "MEDIUM": 0, "INFORMATIONAL": 1}),
    )
    extract_doc = MatterDocument(
        id=2,
        matter_id=1,
        source_filename="contract.pdf",
        analysis_type="extract_clauses",
        result=clause_result.model_dump(mode="json"),
        created_at=NOW,
    )

    classify_result = DocumentClassificationResult(
        document=_parsed_document(),
        classification=DocumentClassification(
            predicted_type="Contract", confidence=0.95, probabilities={"Contract": 0.95, "Email": 0.03, "Other": 0.02}
        ),
    )
    classify_doc = MatterDocument(
        id=3,
        matter_id=1,
        source_filename="unknown.pdf",
        analysis_type="classify",
        result=classify_result.model_dump(mode="json"),
        created_at=NOW,
    )

    tracked_docket = TrackedDocket(
        id=1,
        courtlistener_docket_id=69510553,
        court="scotus",
        docket_number="23-1234",
        case_name="Acme Corp v. Beta LLC",
        matter_id=1,
        created_at=NOW,
        last_checked_at=NOW,
    )

    return MatterDetail(
        matter=matter,
        documents=[parse_doc, extract_doc, classify_doc],
        tracked_dockets=[tracked_docket],
    )


@pytest.fixture
def alerts_by_docket_id() -> dict[int, list[DocketAlert]]:
    return {1: [DocketAlert(id=1, tracked_docket_id=1, created_at=NOW, new_entry_count=3, new_entry_ids=[1, 2, 3])]}


def test_generate_matter_report_returns_pdf_bytes(matter_detail, alerts_by_docket_id) -> None:
    pdf_bytes = generate_matter_report(matter_detail, alerts_by_docket_id)

    assert pdf_bytes.startswith(b"%PDF")


def test_generate_matter_report_contains_expected_content(matter_detail, alerts_by_docket_id) -> None:
    pdf_bytes = generate_matter_report(matter_detail, alerts_by_docket_id)

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    assert "Acme v. Beta" in text
    assert "Uncapped Liability" in text
    assert "HIGH" in text
    assert "Acme Corp v. Beta LLC" in text
    assert "not legal advice" in text


def test_generate_matter_report_handles_empty_matter() -> None:
    matter = Matter(id=2, name="Empty Matter", description=None, created_at=NOW)
    detail = MatterDetail(matter=matter, documents=[], tracked_dockets=[])

    pdf_bytes = generate_matter_report(detail, {})

    assert pdf_bytes.startswith(b"%PDF")
