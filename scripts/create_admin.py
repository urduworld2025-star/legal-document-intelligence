#!/usr/bin/env python
"""Creates the first attorney account directly against the DB. Run once, locally,
by a trusted operator - does NOT go through the API or issue a JWT.

Usage:
    python scripts/create_admin.py --email you@firm.com --name "Jane Attorney"
"""
import argparse
import getpass
import sys

from app.core.config import settings
from legalintel.auth import db as auth_db
from legalintel.auth import hash_password
from legalintel.storage import init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Create the first attorney user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()

    init_db(settings.db_path)

    if auth_db.get_user_by_email(settings.db_path, args.email) is not None:
        print(f"A user with email {args.email} already exists.", file=sys.stderr)
        raise SystemExit(1)

    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords did not match.", file=sys.stderr)
        raise SystemExit(1)
    if len(password) < 8:
        print("Password must be at least 8 characters.", file=sys.stderr)
        raise SystemExit(1)

    user = auth_db.create_user(
        settings.db_path,
        email=args.email,
        name=args.name,
        password_hash=hash_password(password),
        role="attorney",
    )
    print(f"Created attorney user #{user.id} ({user.email}).")


if __name__ == "__main__":
    main()
