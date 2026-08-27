from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.security import get_current_user, require_role
from legalintel.docket import db
from legalintel.docket.courtlistener_client import (
    CourtListenerAPIError,
    CourtListenerClient,
    CourtListenerConfigError,
    CourtListenerNotFoundError,
)
from legalintel.docket.monitor import DocketNotTrackedError, check_docket_for_updates
from legalintel.matters import db as matters_db
from legalintel.models.docket import DocketAlert, DocketCheckResult, DocketEntry, TrackDocketRequest, TrackedDocket

router = APIRouter(prefix="/dockets", tags=["dockets"])


@router.post(
    "/track",
    response_model=TrackedDocket,
    status_code=201,
    dependencies=[Depends(require_role("attorney", "paralegal"))],
)
def track_docket(payload: TrackDocketRequest) -> TrackedDocket:
    existing = db.get_tracked_docket_by_courtlistener_id(settings.db_path, payload.courtlistener_docket_id)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Docket {payload.courtlistener_docket_id} is already tracked (id={existing.id}).",
        )

    if payload.matter_id is not None and matters_db.get_matter(settings.db_path, payload.matter_id) is None:
        raise HTTPException(status_code=404, detail=f"No matter with id {payload.matter_id}")

    try:
        with CourtListenerClient(
            api_token=settings.courtlistener_api_token, base_url=settings.courtlistener_base_url
        ) as client:
            docket_data = client.get_docket(payload.courtlistener_docket_id)
    except CourtListenerConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CourtListenerNotFoundError as exc:
        raise HTTPException(
            status_code=404, detail=f"CourtListener docket {payload.courtlistener_docket_id} not found."
        ) from exc
    except CourtListenerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return db.add_tracked_docket(
        settings.db_path,
        courtlistener_docket_id=payload.courtlistener_docket_id,
        court=docket_data.get("court"),
        docket_number=docket_data.get("docket_number"),
        case_name=docket_data.get("case_name"),
        matter_id=payload.matter_id,
    )


@router.get("", response_model=list[TrackedDocket], dependencies=[Depends(get_current_user)])
def list_dockets() -> list[TrackedDocket]:
    return db.list_tracked_dockets(settings.db_path)


@router.post(
    "/{tracked_docket_id}/check",
    response_model=DocketCheckResult,
    dependencies=[Depends(require_role("attorney", "paralegal"))],
)
def check_docket(tracked_docket_id: int) -> DocketCheckResult:
    try:
        return check_docket_for_updates(
            settings.db_path,
            tracked_docket_id,
            api_token=settings.courtlistener_api_token,
            base_url=settings.courtlistener_base_url,
        )
    except DocketNotTrackedError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CourtListenerConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except CourtListenerNotFoundError as exc:
        raise HTTPException(status_code=502, detail=f"CourtListener no longer has this docket: {exc}") from exc
    except CourtListenerAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{tracked_docket_id}/alerts", response_model=list[DocketAlert], dependencies=[Depends(get_current_user)])
def list_docket_alerts(tracked_docket_id: int) -> list[DocketAlert]:
    return db.list_alerts(settings.db_path, tracked_docket_id)


@router.get(
    "/{tracked_docket_id}/entries", response_model=list[DocketEntry], dependencies=[Depends(get_current_user)]
)
def list_docket_entries(tracked_docket_id: int) -> list[DocketEntry]:
    return db.list_seen_entries(settings.db_path, tracked_docket_id)
