import sqlite3

import pytest

from legalintel.matters import db


def test_add_and_get_matter_round_trip(db_path: str) -> None:
    created = db.add_matter(db_path, name="Acme v. Beta", description="Contract dispute")

    fetched = db.get_matter(db_path, created.id)

    assert fetched is not None
    assert fetched.name == "Acme v. Beta"
    assert fetched.description == "Contract dispute"


def test_get_matter_returns_none_when_absent(db_path: str) -> None:
    assert db.get_matter(db_path, 9999) is None


def test_list_matters_orders_by_id(db_path: str) -> None:
    first = db.add_matter(db_path, name="First", description=None)
    second = db.add_matter(db_path, name="Second", description=None)

    matters = db.list_matters(db_path)

    assert [m.id for m in matters] == [first.id, second.id]


def test_add_and_list_matter_documents_round_trip(db_path: str) -> None:
    matter = db.add_matter(db_path, name="Acme v. Beta", description=None)
    result = {"source_filename": "contract.pdf", "full_text": "hello world"}

    created = db.add_matter_document(
        db_path,
        matter_id=matter.id,
        source_filename="contract.pdf",
        analysis_type="parse",
        result=result,
    )
    documents = db.list_matter_documents(db_path, matter.id)

    assert created.result == result
    assert documents == [created]


def test_add_matter_document_with_unknown_matter_id_raises_integrity_error(db_path: str) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.add_matter_document(
            db_path,
            matter_id=9999,
            source_filename="contract.pdf",
            analysis_type="parse",
            result={},
        )
