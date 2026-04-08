import asyncio
from datetime import UTC, date, datetime, timedelta

import pytest

from src.expenis.core.models import Account, Category, Transaction, db
from src.expenis.core.service import update_transaction
from src.expenis.core.service.transaction_service import (delete_transaction,
                                                          delete_transaction_by_id, get_transaction_by_id,
                                                          get_transaction_tags_by_transaction_ids,
                                                          get_transactions_for_period,
                                                          get_user_tags,
                                                          set_transaction_tags,
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
        await save_transaction(transaction)

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
        # Test category update only with id
        new_category = Category(user_id=1, name="new category", type="income")
        await db.run(new_category.save)
        transaction.category = Category(id=new_category.id)
        await update_transaction(transaction)

        updated = await get_transaction_by_id(transaction.id)
        assert updated.amount == new_amount
        assert updated.description == new_description

        # Test delete
        await delete_transaction(transaction)
        deleted = await get_transaction_by_id(transaction.id)
        assert deleted is None
        # Test delete by id
        transaction = Transaction(
            user_id=user_id,
            account=test_account,
            category=test_category,
            amount=amount,
            description=description
        )
        await save_transaction(transaction)
        await delete_transaction_by_id(transaction.id)
        deleted = await get_transaction_by_id(transaction.id)
        assert deleted is None


@pytest.mark.asyncio
async def test_get_transactions_for_period(test_account, test_category):
    user_id = 1
    today = date.today()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)

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
        await save_transaction(t1)
        await save_transaction(t2)

        # Test period query
        transactions = await get_transactions_for_period(user_id, yesterday, today)
        assert len(transactions) == 2

        transactions = await get_transactions_for_period(user_id, today, today)
        assert len(transactions) == 1
        assert transactions[0].id == t2.id

        transactions = await get_transactions_for_period(user_id, tomorrow, tomorrow)
        assert len(transactions) == 0


@pytest.mark.asyncio
async def test_set_transaction_tags_creates_reuses_and_replaces(test_account, test_category):
    async with db:
        transaction = Transaction(
            user_id=1,
            account=test_account,
            category=test_category,
            amount=100.0,
            description="tx"
        )
        await save_transaction(transaction)

        tags = await set_transaction_tags(1, transaction.id, [" groceries ", "home", "home"])
        assert tags == ["groceries", "home"]

        by_tx = await get_transaction_tags_by_transaction_ids(1, [transaction.id])
        assert by_tx[transaction.id] == ["groceries", "home"]

        all_tags = await get_user_tags(1)
        assert all_tags == ["groceries", "home"]

        replaced = await set_transaction_tags(1, transaction.id, ["travel"])
        assert replaced == ["travel"]

        by_tx = await get_transaction_tags_by_transaction_ids(1, [transaction.id])
        assert by_tx[transaction.id] == ["travel"]

        all_tags = await get_user_tags(1)
        assert all_tags == ["groceries", "home", "travel"]


@pytest.mark.asyncio
async def test_get_user_tags_is_scoped_by_user(test_account, test_category):
    async with db:
        tx_user_1 = Transaction(
            user_id=1,
            account=test_account,
            category=test_category,
            amount=100.0,
            description="tx1"
        )
        await save_transaction(tx_user_1)

        account_user_2 = Account(user_id=2, name="User2")
        category_user_2 = Category(user_id=2, name="Other", type="expense")
        await db.run(account_user_2.save)
        await db.run(category_user_2.save)
        tx_user_2 = Transaction(
            user_id=2,
            account=account_user_2,
            category=category_user_2,
            amount=50.0,
            description="tx2"
        )
        await save_transaction(tx_user_2)

        await set_transaction_tags(1, tx_user_1.id, ["food"])
        await set_transaction_tags(2, tx_user_2.id, ["food", "transport"])

        assert await get_user_tags(1) == ["food"]
        assert await get_user_tags(2) == ["food", "transport"]
