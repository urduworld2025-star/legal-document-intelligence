from pathlib import Path

import pdfplumber

from legalintel.models.document import ParsedPage


def parse_pdf(path: Path) -> list[ParsedPage]:
    pages: list[ParsedPage] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages.append(ParsedPage(page_number=i, text=page.extract_text() or ""))
    return pages
