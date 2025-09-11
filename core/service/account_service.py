from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from core.database import session_maker
from core.models.account import Account
from core.models.transaction import Transaction


async def get_user_accounts(user_id: int) -> List[Account]:
    """Get all accounts for a specific user"""
    async with session_maker() as session:
        result = await session.execute(
            select(Account)
            .where(Account.user_id == user_id)
            .order_by(Account.name)
        )
        return list(result.scalars().all())


async def get_account_by_id(account_id: int, user_id: int, session=None) -> Optional[Account]:
    """Get a specific account by ID for a user"""
    if session is None:
        session = session_maker()
    result = await session.execute(
        select(Account)
        .where(Account.id == account_id, Account.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def calculate_account_balance(account_id: int, user_id: int) -> Optional[float]:
    """Calculate the current balance of an account based on all transactions"""
    async with session_maker() as session:
        # Get the base amount
        account = await get_account_by_id(account_id, user_id, session)
        if not account:
            return None

        base_amount = account.amount

        # Calculate sum of incomes for this account
        income_result = await session.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.account_id == account_id, Transaction.type == "income")
        )
        total_income = income_result.scalar() or 0.0

        # Calculate sum of expenses for this account
        expense_result = await session.execute(
            select(func.sum(Transaction.amount))
            .where(Transaction.account_id == account_id, Transaction.type == "expense")
        )
        total_expense = expense_result.scalar() or 0.0

        # Current balance = base_amount + total_income - total_expense
        current_balance = base_amount + total_income - total_expense
        return current_balance


async def create_account(user_id: int, name: str, initial_amount: float = 0.0) -> Account:
    """Create a new account for a user"""
    async with session_maker() as session:
        account = Account(
            user_id=user_id,
            name=name,
            amount=initial_amount
        )
        session.add(account)
        await session.commit()
        await session.refresh(account)
        return account


async def update_account_balance(account_id: int, user_id: int, new_balance: float) -> Optional[Account]:
    """Update an account's balance"""
    async with session_maker() as session:
        account = await get_account_by_id(account_id, user_id, session)
        if account:
            account.amount = new_balance
            await session.commit()
            await session.refresh(account)
            return account
        return None


class AccountService:
    pass
