"""Cross-cutting search over matters, their analyzed documents, and tracked dockets. A pure
function over already-fetched data (mirrors risk/flagging.py and reporting/report_generator.py's
convention) - the route layer does the DB fetching, this just filters/ranks what it's given."""

from legalintel.models.docket import TrackedDocket
from legalintel.models.document import ClauseExtractionResult, DocumentClassificationResult, ParsedDocument
from legalintel.models.matter import Matter, MatterDocument
from legalintel.models.search import SearchResult

MIN_QUERY_LENGTH = 2
SNIPPET_RADIUS = 60


def _document_full_text(document: MatterDocument) -> str:
    if document.analysis_type == "parse":
        return ParsedDocument.model_validate(document.result).full_text
    if document.analysis_type == "extract_clauses":
        return ClauseExtractionResult.model_validate(document.result).document.full_text
    if document.analysis_type == "classify":
        return DocumentClassificationResult.model_validate(document.result).document.full_text
    return ""


def _snippet_around(text: str, query: str) -> str | None:
    idx = text.lower().find(query.lower())
    if idx == -1:
        return None
    start = max(0, idx - SNIPPET_RADIUS)
    end = min(len(text), idx + len(query) + SNIPPET_RADIUS)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


def search_all(
    matters: list[Matter],
    documents: list[MatterDocument],
    dockets: list[TrackedDocket],
    query: str,
) -> list[SearchResult]:
    query = query.strip()
    if len(query) < MIN_QUERY_LENGTH:
        return []

    matters_by_id = {matter.id: matter for matter in matters}
    results: list[SearchResult] = []

    for matter in matters:
        haystack = f"{matter.name} {matter.description or ''}"
        snippet = _snippet_around(haystack, query)
        if snippet is not None:
            results.append(
                SearchResult(type="matter", matter_id=matter.id, matter_name=matter.name, title=matter.name)
            )

    for document in documents:
        matter = matters_by_id.get(document.matter_id)
        if matter is None:
            continue

        filename_snippet = _snippet_around(document.source_filename, query)
        if filename_snippet is not None:
            results.append(
                SearchResult(
                    type="document",
                    matter_id=matter.id,
                    matter_name=matter.name,
                    title=document.source_filename,
                    document_id=document.id,
                )
            )
            continue

        content_snippet = _snippet_around(_document_full_text(document), query)
        if content_snippet is not None:
            results.append(
                SearchResult(
                    type="document",
                    matter_id=matter.id,
                    matter_name=matter.name,
                    title=document.source_filename,
                    snippet=content_snippet,
                    document_id=document.id,
                )
            )

    for docket in dockets:
        if docket.matter_id is None:
            continue
        matter = matters_by_id.get(docket.matter_id)
        if matter is None:
            continue

        haystack = f"{docket.case_name or ''} {docket.docket_number or ''}"
        snippet = _snippet_around(haystack, query)
        if snippet is not None:
            results.append(
                SearchResult(
                    type="docket",
                    matter_id=matter.id,
                    matter_name=matter.name,
                    title=docket.case_name or f"Docket {docket.courtlistener_docket_id}",
                    docket_id=docket.id,
                )
            )

    return results
