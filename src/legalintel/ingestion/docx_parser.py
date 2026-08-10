from pathlib import Path

import docx

from legalintel.models.document import ParsedPage


def parse_docx(path: Path) -> list[ParsedPage]:
    document = docx.Document(str(path))
    text = "\n".join(p.text for p in document.paragraphs)
    return [ParsedPage(page_number=None, text=text)]
