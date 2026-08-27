import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

_CREATE_TABLES = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('attorney', 'paralegal', 'support_staff')),
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS matter_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_id INTEGER NOT NULL REFERENCES matters(id),
    source_filename TEXT NOT NULL,
    analysis_type TEXT NOT NULL CHECK (analysis_type IN ('parse', 'extract_clauses', 'classify')),
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tracked_dockets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    courtlistener_docket_id INTEGER NOT NULL UNIQUE,
    court TEXT,
    docket_number TEXT,
    case_name TEXT,
    matter_id INTEGER REFERENCES matters(id),
    created_at TEXT NOT NULL,
    last_checked_at TEXT
);

CREATE TABLE IF NOT EXISTS seen_docket_entries (
    tracked_docket_id INTEGER NOT NULL REFERENCES tracked_dockets(id),
    courtlistener_entry_id INTEGER NOT NULL,
    entry_number INTEGER,
    description TEXT,
    date_filed TEXT,
    first_seen_at TEXT NOT NULL,
    PRIMARY KEY (tracked_docket_id, courtlistener_entry_id)
);

CREATE TABLE IF NOT EXISTS docket_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tracked_docket_id INTEGER NOT NULL REFERENCES tracked_dockets(id),
    created_at TEXT NOT NULL,
    new_entry_count INTEGER NOT NULL,
    new_entry_ids TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    action TEXT NOT NULL,
    detail TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clause_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_document_id INTEGER NOT NULL REFERENCES matter_documents(id),
    clause_index INTEGER NOT NULL,
    reviewed_by INTEGER NOT NULL REFERENCES users(id),
    reviewed_at TEXT NOT NULL,
    UNIQUE (matter_document_id, clause_index)
);
"""


@contextmanager
def connect(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_CREATE_TABLES)
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str) -> None:
    with connect(db_path):
        pass
