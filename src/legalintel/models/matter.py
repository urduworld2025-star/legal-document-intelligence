from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from legalintel.models.docket import TrackedDocket

AnalysisType = Literal["parse", "extract_clauses", "classify"]


class Matter(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: int | None = None
    created_at: datetime


class MatterDocument(BaseModel):
    id: int
    matter_id: int
    source_filename: str
    analysis_type: AnalysisType
    result: dict
    created_at: datetime


class MatterDetail(BaseModel):
    matter: Matter
    documents: list[MatterDocument]
    tracked_dockets: list[TrackedDocket]
