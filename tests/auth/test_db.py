from legalintel.auth import db
from legalintel.matters import db as matters_db


def _make_user(db_path: str, email: str = "attorney@example.com", role: str = "attorney"):
    return db.create_user(db_path, email=email, name="Test User", password_hash="hashed", role=role)


def test_create_and_get_user_by_email_round_trip(db_path: str) -> None:
    created = _make_user(db_path)

    fetched = db.get_user_by_email(db_path, "attorney@example.com")

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.role == "attorney"
    assert fetched.is_active is True


def test_get_user_by_email_returns_none_when_absent(db_path: str) -> None:
    assert db.get_user_by_email(db_path, "nobody@example.com") is None


def test_get_user_by_id_round_trip(db_path: str) -> None:
    created = _make_user(db_path)

    fetched = db.get_user_by_id(db_path, created.id)

    assert fetched is not None
    assert fetched.email == "attorney@example.com"


def test_list_users_orders_by_id(db_path: str) -> None:
    first = _make_user(db_path, email="a@example.com")
    second = _make_user(db_path, email="b@example.com")

    users = db.list_users(db_path)

    assert [u.id for u in users] == [first.id, second.id]


def test_log_action_and_list_audit_log_round_trip(db_path: str) -> None:
    user = _make_user(db_path)

    entry = db.log_action(db_path, user_id=user.id, action="login")
    entries = db.list_audit_log(db_path)

    assert entry.action == "login"
    assert entries == [entry]


def _make_matter_document(db_path: str) -> int:
    matter = matters_db.add_matter(db_path, name="Acme v. Beta", description=None)
    document = matters_db.add_matter_document(
        db_path,
        matter_id=matter.id,
        source_filename="contract.pdf",
        analysis_type="extract_clauses",
        result={"clauses": [{}, {}]},
    )
    return document.id


def test_set_clause_reviewed_then_list(db_path: str) -> None:
    user = _make_user(db_path)
    document_id = _make_matter_document(db_path)

    db.set_clause_reviewed(db_path, matter_document_id=document_id, clause_index=0, reviewed_by=user.id)
    reviews = db.list_clause_reviews(db_path, document_id)

    assert len(reviews) == 1
    assert reviews[0].clause_index == 0
    assert reviews[0].reviewed_by == user.id


def test_set_clause_reviewed_upsert_overwrites_reviewer(db_path: str) -> None:
    first_user = _make_user(db_path, email="first@example.com")
    second_user = _make_user(db_path, email="second@example.com")
    document_id = _make_matter_document(db_path)

    db.set_clause_reviewed(db_path, matter_document_id=document_id, clause_index=0, reviewed_by=first_user.id)
    db.set_clause_reviewed(db_path, matter_document_id=document_id, clause_index=0, reviewed_by=second_user.id)
    reviews = db.list_clause_reviews(db_path, document_id)

    assert len(reviews) == 1
    assert reviews[0].reviewed_by == second_user.id


def test_unset_clause_reviewed_removes_it(db_path: str) -> None:
    user = _make_user(db_path)
    document_id = _make_matter_document(db_path)
    db.set_clause_reviewed(db_path, matter_document_id=document_id, clause_index=0, reviewed_by=user.id)

    db.unset_clause_reviewed(db_path, matter_document_id=document_id, clause_index=0)

    assert db.list_clause_reviews(db_path, document_id) == []
