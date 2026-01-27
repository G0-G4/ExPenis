from datetime import UTC, date, datetime

import pytest

from core.models import Account, Category, Transaction, db
from core.service.transaction_service import (create_transaction, delete_transaction,
                                              get_transaction_by_id, get_transactions_for_period,
                                              save_transaction)


@pytest.fixture
async def test_account():
    async with db:
        account = Account(user_id=1, name="Test Account")
        await db.run(account.save)
        return account


@pytest.fixture
async def test_category():
    async with db:
        category = Category(user_id=1, name="Test Category", type="income")
        await db.run(category.save)
        return category


@pytest.mark.asyncio
async def test_basic_crud(test_account, test_category):
    user_id = 1
    amount = 100.0
    description = "Test transaction"

    async with db:
        # Test create
        transaction = Transaction(
            user_id=user_id,
            account=test_account,
            category=test_category,
            amount=amount,
            description=description
        )
        await create_transaction(transaction)

        # Test read
        retrieved = await get_transaction_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.user_id == user_id
        assert retrieved.account.id == test_account.id
        assert retrieved.category.id == test_category.id
        assert retrieved.amount == amount
        assert retrieved.description == description
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None

        # Test update
        new_amount = 200.0
        new_description = "Updated transaction"
        transaction.amount = new_amount
        transaction.description = new_description
        await save_transaction(transaction)

        updated = await get_transaction_by_id(transaction.id)
        assert updated.amount == new_amount
        assert updated.description == new_description
        assert updated.updated_at > updated.created_at

        # Test delete
        await delete_transaction(transaction)
        deleted = await get_transaction_by_id(transaction.id)
        assert deleted is None


@pytest.mark.asyncio
async def test_get_transactions_for_period(test_account, test_category):
    user_id = 1
    today = date.today()
    yesterday = date(today.year, today.month, today.day - 1)
    tomorrow = date(today.year, today.month, today.day + 1)

    async with db:
        # Create transactions for different dates
        t1 = Transaction(
            user_id=user_id,
            account=test_account,
            category=test_category,
            amount=100.0,
            created_at=datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=UTC)
        )
        t2 = Transaction(
            user_id=user_id,
            account=test_account,
            category=test_category,
            amount=200.0,
            created_at=datetime(today.year, today.month, today.day, tzinfo=UTC)
        )
        await create_transaction(t1)
        await create_transaction(t2)

        # Test period query
        transactions = await get_transactions_for_period(user_id, yesterday, today)
        assert len(transactions) == 2

        transactions = await get_transactions_for_period(user_id, today, today)
        assert len(transactions) == 1
        assert transactions[0].id == t2.id

        transactions = await get_transactions_for_period(user_id, tomorrow, tomorrow)
        assert len(transactions) == 0
