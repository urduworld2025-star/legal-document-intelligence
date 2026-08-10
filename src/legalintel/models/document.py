from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ParsedPage(BaseModel):
    page_number: int | None
    text: str


class ParsedDocument(BaseModel):
    source_filename: str
    file_type: Literal["pdf", "docx"]
    matter_id: str | None = None
    pages: list[ParsedPage]
    full_text: str
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
