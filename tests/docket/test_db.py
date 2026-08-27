from legalintel.docket import db
from legalintel.matters import db as matters_db
from legalintel.models.docket import DocketEntry


def _track(db_path: str, courtlistener_docket_id: int = 111, matter_id: int | None = None) -> int:
    tracked = db.add_tracked_docket(
        db_path,
        courtlistener_docket_id=courtlistener_docket_id,
        court="scotus",
        docket_number="23-1234",
        case_name="Example v. Example",
        matter_id=matter_id,
    )
    return tracked.id


def test_add_and_get_tracked_docket_round_trip(db_path: str) -> None:
    tracked_id = _track(db_path)

    fetched = db.get_tracked_docket(db_path, tracked_id)

    assert fetched is not None
    assert fetched.courtlistener_docket_id == 111
    assert fetched.case_name == "Example v. Example"
    assert fetched.matter_id is None
    assert fetched.last_checked_at is None


def test_add_tracked_docket_with_real_matter_id_round_trips(db_path: str) -> None:
    matter = matters_db.add_matter(db_path, name="Acme v. Beta", description=None)

    tracked_id = _track(db_path, matter_id=matter.id)

    fetched = db.get_tracked_docket(db_path, tracked_id)
    assert fetched is not None
    assert fetched.matter_id == matter.id


def test_list_tracked_dockets_for_matter(db_path: str) -> None:
    matter = matters_db.add_matter(db_path, name="Acme v. Beta", description=None)
    in_matter_id = _track(db_path, courtlistener_docket_id=1, matter_id=matter.id)
    _track(db_path, courtlistener_docket_id=2)  # unrelated, no matter

    dockets = db.list_tracked_dockets_for_matter(db_path, matter.id)

    assert [d.id for d in dockets] == [in_matter_id]


def test_get_tracked_docket_returns_none_when_absent(db_path: str) -> None:
    assert db.get_tracked_docket(db_path, 9999) is None


def test_get_tracked_docket_by_courtlistener_id_returns_none_when_absent(db_path: str) -> None:
    assert db.get_tracked_docket_by_courtlistener_id(db_path, 9999) is None


def test_get_tracked_docket_by_courtlistener_id_finds_match(db_path: str) -> None:
    tracked_id = _track(db_path, courtlistener_docket_id=222)

    found = db.get_tracked_docket_by_courtlistener_id(db_path, 222)

    assert found is not None
    assert found.id == tracked_id


def test_list_tracked_dockets_orders_by_id(db_path: str) -> None:
    first_id = _track(db_path, courtlistener_docket_id=1)
    second_id = _track(db_path, courtlistener_docket_id=2)

    dockets = db.list_tracked_dockets(db_path)

    assert [d.id for d in dockets] == [first_id, second_id]


def test_get_seen_entry_ids_starts_empty(db_path: str) -> None:
    tracked_id = _track(db_path)

    assert db.get_seen_entry_ids(db_path, tracked_id) == set()


def test_record_new_entries_reflected_in_seen_entry_ids(db_path: str) -> None:
    tracked_id = _track(db_path)
    entries = [
        DocketEntry(courtlistener_entry_id=1, entry_number=1, description="Complaint filed", date_filed=None),
        DocketEntry(courtlistener_entry_id=2, entry_number=2, description="Answer filed", date_filed=None),
    ]

    db.record_new_entries(db_path, tracked_id, entries)

    assert db.get_seen_entry_ids(db_path, tracked_id) == {1, 2}


def test_list_seen_entries_starts_empty(db_path: str) -> None:
    tracked_id = _track(db_path)

    assert db.list_seen_entries(db_path, tracked_id) == []


def test_list_seen_entries_returns_full_entry_details(db_path: str) -> None:
    tracked_id = _track(db_path)
    entries = [
        DocketEntry(courtlistener_entry_id=1, entry_number=1, description="Complaint filed", date_filed=None),
        DocketEntry(courtlistener_entry_id=2, entry_number=2, description="Answer filed", date_filed=None),
    ]

    db.record_new_entries(db_path, tracked_id, entries)
    seen = db.list_seen_entries(db_path, tracked_id)

    assert {e.courtlistener_entry_id for e in seen} == {1, 2}
    assert {e.description for e in seen} == {"Complaint filed", "Answer filed"}


def test_record_new_entries_is_safe_to_call_twice(db_path: str) -> None:
    tracked_id = _track(db_path)
    entry = DocketEntry(courtlistener_entry_id=1, entry_number=1, description="Complaint filed", date_filed=None)

    db.record_new_entries(db_path, tracked_id, [entry])
    db.record_new_entries(db_path, tracked_id, [entry])

    assert db.get_seen_entry_ids(db_path, tracked_id) == {1}


def test_create_and_list_alerts_round_trip(db_path: str) -> None:
    tracked_id = _track(db_path)

    created = db.create_alert(db_path, tracked_id, [1, 2, 3])
    alerts = db.list_alerts(db_path, tracked_id)

    assert created.new_entry_count == 3
    assert created.new_entry_ids == [1, 2, 3]
    assert alerts == [created]
