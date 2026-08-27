from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class ParsedPage(BaseModel):
    page_number: int | None
    text: str


class ParsedDocument(BaseModel):
    source_filename: str
    file_type: Literal["pdf", "docx"]
    matter_id: int | None = None
    pages: list[ParsedPage]
    full_text: str
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


RiskLevel = Literal["HIGH", "MEDIUM", "INFORMATIONAL"]
ConfidenceBand = Literal["HIGH", "MEDIUM", "LOW"]


class ClauseMatch(BaseModel):
    category: str
    text: str
    confidence: float
    char_start: int | None
    char_end: int | None
    risk_level: RiskLevel | None = None
    confidence_band: ConfidenceBand | None = None
    possible_negation: bool = False


class RiskSummary(BaseModel):
    highest_risk_level: RiskLevel | None
    counts_by_level: dict[RiskLevel, int]


class ClauseExtractionResult(BaseModel):
    document: ParsedDocument
    clauses: list[ClauseMatch]
    risk_summary: RiskSummary


DocumentType = Literal["Contract", "Email", "Other"]


class DocumentClassification(BaseModel):
    predicted_type: DocumentType
    confidence: float
    probabilities: dict[DocumentType, float]


class DocumentClassificationResult(BaseModel):
    document: ParsedDocument
    classification: DocumentClassification
