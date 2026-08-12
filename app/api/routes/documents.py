import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile

from app.core.config import settings
from legalintel.extraction.clause_extractor import ModelNotFoundError, extract_clauses
from legalintel.ingestion.pipeline import parse_document
from legalintel.models.document import ClauseExtractionResult, ParsedDocument

router = APIRouter(prefix="/documents", tags=["documents"])


async def _parse_uploaded_file(file: UploadFile, matter_id: str | None) -> ParsedDocument:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {sorted(settings.allowed_extensions)}",
        )

    contents = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb}MB limit")

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        parsed = parse_document(Path(tmp_path), matter_id=matter_id)
        parsed.source_filename = file.filename or parsed.source_filename
        return parsed
    finally:
        if tmp_path is not None:
            os.unlink(tmp_path)


@router.post("/parse", response_model=ParsedDocument)
async def parse_uploaded_document(
    file: UploadFile,
    matter_id: str | None = Form(default=None),
) -> ParsedDocument:
    return await _parse_uploaded_file(file, matter_id)


@router.post("/extract-clauses", response_model=ClauseExtractionResult)
async def extract_clauses_from_upload(
    file: UploadFile,
    matter_id: str | None = Form(default=None),
) -> ClauseExtractionResult:
    parsed = await _parse_uploaded_file(file, matter_id)

    try:
        clauses = extract_clauses(parsed.full_text, model_dir=settings.clause_model_dir)
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return ClauseExtractionResult(document=parsed, clauses=clauses)
