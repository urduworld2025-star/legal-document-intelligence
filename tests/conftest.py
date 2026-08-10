from pathlib import Path

import docx
import pytest
from reportlab.pdfgen import canvas

SAMPLE_PDF_TEXT = "Hello from a generated test PDF."
SAMPLE_DOCX_TEXT = "Hello from a generated test DOCX."


@pytest.fixture
def sample_pdf_path(tmp_path: Path) -> Path:
    path = tmp_path / "sample.pdf"
    c = canvas.Canvas(str(path))
    c.drawString(72, 720, SAMPLE_PDF_TEXT)
    c.save()
    return path


@pytest.fixture
def sample_docx_path(tmp_path: Path) -> Path:
    path = tmp_path / "sample.docx"
    document = docx.Document()
    document.add_paragraph(SAMPLE_DOCX_TEXT)
    document.save(str(path))
    return path
