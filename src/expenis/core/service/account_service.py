import logging
from cmath import acos
from datetime import UTC, datetime

from peewee import JOIN, fn

from ..models import Account, Category, Transaction, db
from ..utils.currency_codes import CODES
from fastapi import HTTPException

logger = logging.getLogger(__name__)


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


async def create_account(user_id: int, name: str, adjustment_amount: float, currency_code="RUB"):
    if currency_code not in CODES:
        logger.warning("unknown currency code: %s", currency_code)
        raise HTTPException(status_code=400, detail="Unknown currency code")
    now = datetime.now(UTC)
    account = Account(user_id=user_id, name=name, adjustment_amount=adjustment_amount, currency_code=currency_code,
                      created_at=now, updated_at=now)
    await db.run(account.save)
    logger.info("account created: id=%d user_id=%d name=%s currency=%s", account.id, user_id, name, currency_code)
    return account


async def update_account(user_id: int, account: Account, new_balance: float | None = None):
    now = datetime.now(UTC)
    async with db.atomic():
        if new_balance is not None:
            _, balance = await get_user_account_with_balance(user_id, account.id)
            account.adjustment_amount = new_balance - balance + account.adjustment_amount
        account.updated_at = now
        await db.run(account.save)
    logger.info("account updated: id=%d user_id=%d", account.id, user_id)
    return account

async def delete_account_by_id(account_id: int):
    """Delete a category"""
    await db.run(lambda: Account.delete_by_id(account_id))

async def delete_account_by_id_and_user_id(user_id: int, account_id: int):
    account = await get_account_by_id(user_id, account_id)
    logger.info("account deleted: id=%d user_id=%d", account_id, user_id)
    await db.run(account.delete_instance)
