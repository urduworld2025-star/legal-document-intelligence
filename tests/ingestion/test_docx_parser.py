from pathlib import Path

from legalintel.ingestion.docx_parser import parse_docx
from tests.conftest import SAMPLE_DOCX_TEXT


def test_parse_docx_extracts_text(sample_docx_path: Path) -> None:
    pages = parse_docx(sample_docx_path)

    assert len(pages) == 1
    assert pages[0].page_number is None
    assert SAMPLE_DOCX_TEXT in pages[0].text
