from datetime import datetime, timezone

from legalintel.models.docket import TrackedDocket
from legalintel.models.matter import Matter, MatterDocument
from legalintel.search import search_all

NOW = datetime.now(timezone.utc)

MATTER = Matter(id=1, name="Acme v. Beta", description="Contract dispute over widgets", created_at=NOW)
OTHER_MATTER = Matter(id=2, name="Unrelated Case", description=None, created_at=NOW)


def test_matches_matter_by_name() -> None:
    results = search_all([MATTER, OTHER_MATTER], [], [], "Acme")

    assert len(results) == 1
    assert results[0].type == "matter"
    assert results[0].matter_id == 1


def test_matches_matter_by_description() -> None:
    results = search_all([MATTER], [], [], "widgets")

    assert len(results) == 1
    assert results[0].type == "matter"


def test_matches_document_by_filename() -> None:
    document = MatterDocument(
        id=10, matter_id=1, source_filename="master-agreement.pdf", analysis_type="parse",
        result={"source_filename": "master-agreement.pdf", "file_type": "pdf", "pages": [], "full_text": ""},
        created_at=NOW,
    )

    results = search_all([MATTER], [document], [], "master-agreement")

    assert len(results) == 1
    assert results[0].type == "document"
    assert results[0].document_id == 10
    assert results[0].matter_name == "Acme v. Beta"


def test_matches_document_by_content_and_returns_snippet() -> None:
    document = MatterDocument(
        id=10, matter_id=1, source_filename="contract.pdf", analysis_type="parse",
        result={
            "source_filename": "contract.pdf", "file_type": "pdf", "pages": [],
            "full_text": "This Agreement shall be governed by the laws of the State of Delaware.",
        },
        created_at=NOW,
    )

    results = search_all([MATTER], [document], [], "Delaware")

    assert len(results) == 1
    assert results[0].type == "document"
    assert results[0].snippet is not None
    assert "Delaware" in results[0].snippet


def test_document_search_is_case_insensitive() -> None:
    document = MatterDocument(
        id=10, matter_id=1, source_filename="contract.pdf", analysis_type="parse",
        result={"source_filename": "contract.pdf", "file_type": "pdf", "pages": [], "full_text": "Governed by DELAWARE law."},
        created_at=NOW,
    )

    results = search_all([MATTER], [document], [], "delaware")

    assert len(results) == 1


def test_document_with_missing_matter_is_skipped() -> None:
    document = MatterDocument(
        id=10, matter_id=999, source_filename="orphan.pdf", analysis_type="parse",
        result={"source_filename": "orphan.pdf", "file_type": "pdf", "pages": [], "full_text": ""},
        created_at=NOW,
    )

    results = search_all([MATTER], [document], [], "orphan")

    assert results == []


def test_matches_docket_by_case_name() -> None:
    docket = TrackedDocket(
        id=5, courtlistener_docket_id=123, court="scotus", docket_number="23-1234",
        case_name="Example v. Example", matter_id=1, created_at=NOW, last_checked_at=None,
    )

    results = search_all([MATTER], [], [docket], "Example v.")

    assert len(results) == 1
    assert results[0].type == "docket"
    assert results[0].docket_id == 5


def test_docket_without_matter_id_is_skipped() -> None:
    docket = TrackedDocket(
        id=5, courtlistener_docket_id=123, court=None, docket_number=None,
        case_name="Untracked Case", matter_id=None, created_at=NOW, last_checked_at=None,
    )

    results = search_all([MATTER], [], [docket], "Untracked")

    assert results == []


def test_short_query_returns_no_results() -> None:
    results = search_all([MATTER], [], [], "A")

    assert results == []


def test_empty_query_returns_no_results() -> None:
    results = search_all([MATTER], [], [], "")

    assert results == []


def test_no_match_returns_empty_list() -> None:
    results = search_all([MATTER], [], [], "nonexistent-term-xyz")

    assert results == []
