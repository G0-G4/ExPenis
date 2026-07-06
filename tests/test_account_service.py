import pytest

from src.expenis.core.errors import NotFoundException
from src.expenis.core.models import Account, Category, Transaction, db
from src.expenis.core.service import create_account, get_account_by_id, get_active_account_by_id, \
    delete_account_by_id, delete_account_by_id_and_user_id, get_user_account_with_balance, get_user_accounts, \
    get_user_accounts_with_balance
from src.expenis.core.service.transaction_service import save_transaction


@pytest.mark.asyncio
async def test_basic_crud():
    user_id = 1
    name = "name"
    adjustment_amount = 10.0
    async with db:
        await create_account(user_id=user_id, name=name, adjustment_amount=adjustment_amount)

        accounts = await get_user_accounts(user_id)
        assert len(accounts) > 0
        acc = accounts[0]
        retrieved_account = await get_account_by_id(user_id, acc.id)
        assert retrieved_account == acc
        assert acc.user_id == user_id
        assert acc.name == name
        assert acc.adjustment_amount == adjustment_amount

        accounts_with_balances = await get_user_accounts_with_balance(user_id)
        assert len(accounts_with_balances) > 0
        acc, blnc = accounts_with_balances[0]
        retrieved_account, balance = await get_user_account_with_balance(user_id, acc.id)
        assert acc == retrieved_account
        assert blnc == balance
        assert blnc == adjustment_amount


@pytest.mark.asyncio
async def test_delete_account_without_transactions_hard_deletes():
    user_id = 1
    async with db:
        account = await create_account(user_id=user_id, name="cash", adjustment_amount=0.0)
        delete_type = await delete_account_by_id_and_user_id(user_id, account.id)

        assert delete_type == "hard"
        assert await get_account_by_id(user_id, account.id) is None


@pytest.mark.asyncio
async def test_delete_account_with_transactions_soft_deletes():
    user_id = 1
    async with db:
        account = await create_account(user_id=user_id, name="cash", adjustment_amount=0.0)
        category = Category(user_id=user_id, name="income", type="income")
        await db.run(category.save)
        transaction = Transaction(user_id=user_id, account=account, category=category, amount=10.0)
        await save_transaction(transaction)

        delete_type = await delete_account_by_id_and_user_id(user_id, account.id)

        assert delete_type == "soft"
        soft_deleted = await get_account_by_id(user_id, account.id)
        assert soft_deleted is not None
        assert soft_deleted.is_deleted is True
        assert soft_deleted.deleted_at is not None


@pytest.mark.asyncio
async def test_get_user_accounts_excludes_soft_deleted():
    user_id = 1
    async with db:
        active = await create_account(user_id=user_id, name="active", adjustment_amount=0.0)
        deleted = await create_account(user_id=user_id, name="deleted", adjustment_amount=0.0)
        category = Category(user_id=user_id, name="income", type="income")
        await db.run(category.save)
        await save_transaction(
            Transaction(user_id=user_id, account=deleted, category=category, amount=5.0)
        )
        await delete_account_by_id_and_user_id(user_id, deleted.id)

        accounts = await get_user_accounts(user_id)
        assert {a.id for a in accounts} == {active.id}


@pytest.mark.asyncio
async def test_get_user_accounts_with_balance_excludes_soft_deleted():
    user_id = 1
    async with db:
        active = await create_account(user_id=user_id, name="active", adjustment_amount=1.0)
        deleted = await create_account(user_id=user_id, name="deleted", adjustment_amount=2.0)
        category = Category(user_id=user_id, name="income", type="income")
        await db.run(category.save)
        await save_transaction(
            Transaction(user_id=user_id, account=deleted, category=category, amount=3.0)
        )
        await delete_account_by_id_and_user_id(user_id, deleted.id)

        accounts = await get_user_accounts_with_balance(user_id)
        assert {a.id for a, _ in accounts} == {active.id}


@pytest.mark.asyncio
async def test_get_active_account_by_id_excludes_soft_deleted():
    user_id = 1
    async with db:
        account = await create_account(user_id=user_id, name="cash", adjustment_amount=0.0)
        category = Category(user_id=user_id, name="income", type="income")
        await db.run(category.save)
        await save_transaction(
            Transaction(user_id=user_id, account=account, category=category, amount=1.0)
        )
        await delete_account_by_id_and_user_id(user_id, account.id)

        assert await get_active_account_by_id(user_id, account.id) is None
        # get_account_by_id still returns it for historical lookup (e.g. transaction DTOs)
        assert await get_account_by_id(user_id, account.id) is not None


@pytest.mark.asyncio
async def test_delete_nonexistent_account_raises_not_found():
    async with db:
        with pytest.raises(NotFoundException):
            await delete_account_by_id_and_user_id(user_id=1, account_id=999)


@pytest.mark.asyncio
async def test_delete_account_of_other_user_raises_not_found():
    async with db:
        account = await create_account(user_id=1, name="mine", adjustment_amount=0.0)
        with pytest.raises(NotFoundException):
            await delete_account_by_id_and_user_id(user_id=2, account_id=account.id)


@pytest.mark.asyncio
async def test_delete_account_by_id_without_user_id_soft_deletes():
    async with db:
        account = await create_account(user_id=1, name="cash", adjustment_amount=0.0)
        category = Category(user_id=1, name="income", type="income")
        await db.run(category.save)
        await save_transaction(
            Transaction(user_id=1, account=account, category=category, amount=1.0)
        )

        delete_type = await delete_account_by_id(account.id)

        assert delete_type == "soft"
        soft_deleted = await get_account_by_id(1, account.id)
        assert soft_deleted is not None
        assert soft_deleted.is_deleted is True


@pytest.mark.asyncio
async def test_delete_account_by_id_without_user_id_hard_deletes_when_no_transactions():
    async with db:
        account = await create_account(user_id=1, name="cash", adjustment_amount=0.0)

        delete_type = await delete_account_by_id(account.id)

        assert delete_type == "hard"
        assert await get_account_by_id(1, account.id) is None


@pytest.mark.asyncio
async def test_delete_account_by_id_without_user_id_raises_when_missing():
    async with db:
        with pytest.raises(NotFoundException):
            await delete_account_by_id(999)
