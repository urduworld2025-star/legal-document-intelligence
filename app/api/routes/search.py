from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.security import get_current_user
from legalintel.docket import db as docket_db
from legalintel.matters import db as matters_db
from legalintel.models.search import SearchResult
from legalintel.search import search_all

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=list[SearchResult], dependencies=[Depends(get_current_user)])
def search(q: str = "") -> list[SearchResult]:
    matters = matters_db.list_matters(settings.db_path)
    documents = matters_db.list_all_matter_documents(settings.db_path)
    dockets = docket_db.list_tracked_dockets(settings.db_path)
    return search_all(matters, documents, dockets, q)
