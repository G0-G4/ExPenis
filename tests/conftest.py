import pytest

from src.expenis.core.models import Account, Category, Session, Tag, Transaction, TransactionTag, db


@pytest.fixture(autouse=True)
async def run_before_each_test():
    async with db:
        await db.run(lambda: db.create_tables([Account, Category, Transaction, Session, Tag, TransactionTag], safe=True))
        await db.run(TransactionTag.truncate_table)
        await db.run(Tag.truncate_table)
        await db.run(Transaction.truncate_table)
        await db.run(Account.truncate_table)
        await db.run(Category.truncate_table)
        await db.run(Session.truncate_table)
    yield
    await db.close_pool()
