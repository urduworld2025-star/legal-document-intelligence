from pathlib import Path

from legalintel.ingestion.pdf_parser import parse_pdf
from tests.conftest import SAMPLE_PDF_TEXT


def test_parse_pdf_extracts_text(sample_pdf_path: Path) -> None:
    pages = parse_pdf(sample_pdf_path)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert SAMPLE_PDF_TEXT in pages[0].text
