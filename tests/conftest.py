import pytest

from src.expenis.core.models import Account, Category, Session, Transaction, db


@pytest.fixture(autouse=True)
async def run_before_each_test():
    async with db:
        await db.run(Transaction.truncate_table)
        await db.run(Account.truncate_table)
        await db.run(Category.truncate_table)
        await db.run(Session.truncate_table)
    yield
    await db.close_pool()