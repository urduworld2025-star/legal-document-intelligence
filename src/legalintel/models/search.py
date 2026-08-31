from typing import Literal

from pydantic import BaseModel

SearchResultType = Literal["matter", "document", "docket"]


class SearchResult(BaseModel):
    type: SearchResultType
    matter_id: int
    matter_name: str
    title: str
    snippet: str | None = None
    document_id: int | None = None
    docket_id: int | None = None
