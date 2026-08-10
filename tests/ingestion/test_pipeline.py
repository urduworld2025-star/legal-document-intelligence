from pathlib import Path

import pytest

from legalintel.ingestion.pipeline import parse_document
from tests.conftest import SAMPLE_DOCX_TEXT, SAMPLE_PDF_TEXT


def test_parse_document_dispatches_pdf(sample_pdf_path: Path) -> None:
    doc = parse_document(sample_pdf_path, matter_id="matter-123")

    assert doc.file_type == "pdf"
    assert doc.matter_id == "matter-123"
    assert SAMPLE_PDF_TEXT in doc.full_text


def test_parse_document_dispatches_docx(sample_docx_path: Path) -> None:
    doc = parse_document(sample_docx_path)

    assert doc.file_type == "docx"
    assert doc.matter_id is None
    assert SAMPLE_DOCX_TEXT in doc.full_text


def test_parse_document_rejects_unsupported_type(tmp_path: Path) -> None:
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("plain text")

    with pytest.raises(ValueError):
        parse_document(unsupported)
