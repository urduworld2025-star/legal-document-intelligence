from pathlib import Path

from legalintel.ingestion.docx_parser import parse_docx
from legalintel.ingestion.pdf_parser import parse_pdf
from legalintel.models.document import ParsedDocument

_PARSERS = {
    ".pdf": ("pdf", parse_pdf),
    ".docx": ("docx", parse_docx),
}


def parse_document(path: Path, matter_id: str | None = None) -> ParsedDocument:
    suffix = path.suffix.lower()
    if suffix not in _PARSERS:
        raise ValueError(f"Unsupported file type: {suffix or '(none)'}")

    file_type, parser = _PARSERS[suffix]
    pages = parser(path)
    full_text = "\n".join(page.text for page in pages)

    return ParsedDocument(
        source_filename=path.name,
        file_type=file_type,
        matter_id=matter_id,
        pages=pages,
        full_text=full_text,
    )
