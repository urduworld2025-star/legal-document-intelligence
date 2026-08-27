from datetime import date, datetime

from pydantic import BaseModel


class TrackDocketRequest(BaseModel):
    courtlistener_docket_id: int
    matter_id: int | None = None


class TrackedDocket(BaseModel):
    id: int
    courtlistener_docket_id: int
    court: str | None
    docket_number: str | None
    case_name: str | None
    matter_id: int | None
    created_at: datetime
    last_checked_at: datetime | None


class DocketEntry(BaseModel):
    courtlistener_entry_id: int
    entry_number: int | None
    description: str
    date_filed: date | None


class DocketAlert(BaseModel):
    id: int
    tracked_docket_id: int
    created_at: datetime
    new_entry_count: int
    new_entry_ids: list[int]


class DocketCheckResult(BaseModel):
    tracked_docket_id: int
    checked_at: datetime
    new_entries: list[DocketEntry]
    alert_created: bool
    alert: DocketAlert | None = None
