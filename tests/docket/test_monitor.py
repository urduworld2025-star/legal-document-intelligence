import pytest

from legalintel.docket import db
from legalintel.docket.monitor import DocketNotTrackedError, check_docket_for_updates

BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

ENTRY_1 = {"id": 1, "entry_number": 1, "description": "Complaint filed", "date_filed": "2026-01-01"}
ENTRY_2 = {"id": 2, "entry_number": 2, "description": "Answer filed", "date_filed": "2026-01-05"}
ENTRY_3 = {"id": 3, "entry_number": 3, "description": "Motion filed", "date_filed": "2026-01-10"}


def _track(db_path: str) -> int:
    tracked = db.add_tracked_docket(
        db_path,
        courtlistener_docket_id=69510553,
        court="scotus",
        docket_number="23-1234",
        case_name="Example v. Example",
        matter_id=None,
    )
    return tracked.id


def test_first_check_finds_all_entries_as_new_and_creates_alert(db_path, entries_transport_factory) -> None:
    tracked_id = _track(db_path)
    transport = entries_transport_factory([ENTRY_1, ENTRY_2])

    result = check_docket_for_updates(
        db_path, tracked_id, api_token="fake-token", base_url=BASE_URL, transport=transport
    )

    assert {e.courtlistener_entry_id for e in result.new_entries} == {1, 2}
    assert result.alert_created is True
    assert result.alert is not None
    assert set(result.alert.new_entry_ids) == {1, 2}


def test_second_check_with_same_entries_finds_nothing_new(db_path, entries_transport_factory) -> None:
    tracked_id = _track(db_path)
    check_docket_for_updates(
        db_path, tracked_id, api_token="fake-token", base_url=BASE_URL,
        transport=entries_transport_factory([ENTRY_1, ENTRY_2]),
    )

    result = check_docket_for_updates(
        db_path, tracked_id, api_token="fake-token", base_url=BASE_URL,
        transport=entries_transport_factory([ENTRY_1, ENTRY_2]),
    )

    assert result.new_entries == []
    assert result.alert_created is False
    assert result.alert is None


def test_third_check_with_one_added_entry_flags_only_that_one(db_path, entries_transport_factory) -> None:
    tracked_id = _track(db_path)
    for entries in ([ENTRY_1, ENTRY_2], [ENTRY_1, ENTRY_2]):
        check_docket_for_updates(
            db_path, tracked_id, api_token="fake-token", base_url=BASE_URL,
            transport=entries_transport_factory(entries),
        )

    result = check_docket_for_updates(
        db_path, tracked_id, api_token="fake-token", base_url=BASE_URL,
        transport=entries_transport_factory([ENTRY_1, ENTRY_2, ENTRY_3]),
    )

    assert [e.courtlistener_entry_id for e in result.new_entries] == [3]
    assert result.alert_created is True


def test_check_unknown_tracked_docket_raises(db_path, entries_transport_factory) -> None:
    with pytest.raises(DocketNotTrackedError):
        check_docket_for_updates(
            db_path, 9999, api_token="fake-token", base_url=BASE_URL,
            transport=entries_transport_factory([ENTRY_1]),
        )
