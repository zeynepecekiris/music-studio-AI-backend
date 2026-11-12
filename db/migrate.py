"""
Apply db/migrations/*.sql in filename order, each exactly once.

Runs in Heroku's release phase (see Procfile) before new code goes live.
If a migration fails, its transaction is rolled back and the release is
aborted, so the previous version keeps serving traffic.

Local SQLite dev databases are built from the models by create_all instead.
"""
import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from db.base import engine, Base
import db.models  # noqa: register all models

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Tables that existed before SQL migrations; everything newer is created by SQL.
BASE_TABLES = ["users", "verification_codes", "songs", "friendships", "conversations", "messages"]


def main():
    if engine.dialect.name != "postgresql":
        print(f"[migrate] {engine.dialect.name}: skipping SQL migrations")
        return

    # Fresh databases: create base tables first so migrations can ALTER them.
    # The models declare the enum with create_type=False, so create it here.
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "DO $$ BEGIN"
            " CREATE TYPE friendshipstatus AS ENUM ('pending', 'accepted', 'blocked');"
            " EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        )
    Base.metadata.create_all(
        bind=engine, tables=[Base.metadata.tables[t] for t in BASE_TABLES]
    )

    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " filename VARCHAR PRIMARY KEY,"
            " applied_at TIMESTAMP NOT NULL DEFAULT now())"
        ))
        applied = {r[0] for r in conn.execute(text("SELECT filename FROM schema_migrations"))}

    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in applied:
            continue
        print(f"[migrate] applying {path.name}")
        with engine.begin() as conn:
            conn.exec_driver_sql(path.read_text())
            conn.execute(
                text("INSERT INTO schema_migrations (filename) VALUES (:f)"),
                {"f": path.name},
            )
    print("[migrate] up to date")


if __name__ == "__main__":
    main()
