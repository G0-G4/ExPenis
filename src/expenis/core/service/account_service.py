from datetime import UTC, datetime

from peewee import JOIN, fn

from ..models import Account, Category, Transaction, db


async def get_user_accounts(user_id: int) -> list[Account]:
    accounts = await db.list((Account.select()
                              .where(Account.user_id == user_id)
                              .order_by(Account.name)))
    return accounts


async def get_account_by_id(user_id: int, id: int) -> Account | None:
    account = await db.run(lambda: Account.get_or_none((Account.user_id == user_id) & (Account.id == id)))
    return account


def _accounts_with_balance_query(filterr):
    return Account.select(
        Account,
        (fn.COALESCE(fn.SUM(
            Transaction.amount *
            fn.IIF(Category.type == 'income', 1, -1)
        ), 0.0) + Account.adjustment_amount).alias('balance')
    ).join(
        Transaction, join_type=JOIN.LEFT_OUTER
    ).join(
        Category, join_type=JOIN.LEFT_OUTER
    ).where(filterr).group_by(Account.name).order_by(Account.name)


async def get_user_accounts_with_balance(user_id: int) -> list[tuple[Account, float]]:
    accounts = await db.list(_accounts_with_balance_query(Account.user_id == user_id))
    return [(a, a.balance) for a in accounts]


async def get_user_account_with_balance(user_id: int, account_id) -> tuple[Account, float] | tuple[None, None]:
    accounts = await db.list(_accounts_with_balance_query((Account.id == account_id) & (Account.user_id == user_id)))
    return (accounts[0], accounts[0].balance) if len(accounts) > 0 else (None, None)


async def create_account(user_id: int, name: str, adjustment_amount: float):
    now = datetime.now(UTC)
    account = Account(user_id=user_id, name=name, adjustment_amount=adjustment_amount, created_at=now, updated_at=now)
    await db.run(account.save)


async def set_balance(user_id: int, id: int, new_balance: float):
    async with db.atomic():
        account, balance = await get_user_account_with_balance(user_id, id)
        account.adjustment_amount = new_balance - balance + account.adjustment_amount
        await db.run(account.save)

async def update_account(user_id: int, account: Account, new_balance: float | None = None):
    now = datetime.now(UTC)
    async with db.atomic():
        if new_balance is not None:
            _, balance = await get_user_account_with_balance(user_id, account.id)
            account.adjustment_amount = new_balance - balance + account.adjustment_amount
        account.updated_at = now
        await db.run(account.save)

async def delete_account_by_id(account_id: int):
    """Delete a category"""
    await db.run(lambda: Account.delete_by_id(account_id))