import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def _create_test_database() -> str:
    path = Path(tempfile.mkdtemp(prefix="expenis-tests-")) / "test.db"
    with sqlite3.connect(path) as conn:
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            conn.executescript(migration.read_text())
    return str(path)


# Tests truncate every table, so they must never touch the dev database.
# Set before importing models: the db path is read at import time.
os.environ["EXPENIS_DB_PATH"] = _create_test_database()

from src.expenis.core.models import (  # noqa: E402
    Account, Category, Session, Tag, Transaction, TransactionTag, User, db,
)
from src.expenis.core.models.database import DEFAULT_DB_PATH  # noqa: E402

assert Path(db.database).resolve() != Path(DEFAULT_DB_PATH).resolve(), (
    "tests must not run against the dev database"
)


@pytest.fixture(autouse=True)
async def run_before_each_test():
    async with db:
        await db.run(lambda: db.create_tables(
            [User, Account, Category, Transaction, Session, Tag, TransactionTag],
            safe=True,
        ))
        await db.run(TransactionTag.truncate_table)
        await db.run(Tag.truncate_table)
        await db.run(Transaction.truncate_table)
        await db.run(Account.truncate_table)
        await db.run(Category.truncate_table)
        await db.run(Session.truncate_table)
        await db.run(User.truncate_table)
        def _reset_pk_sequence():
            try:
                db.execute_sql("DELETE FROM sqlite_sequence")
            except Exception:
                pass

        await db.run(_reset_pk_sequence)
    yield
    await db.close_pool()