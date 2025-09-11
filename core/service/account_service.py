from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from core.database import session_maker
from core.models.account import Account

class AccountService:
    
    async def get_user_accounts(self, user_id: int) -> List[Account]:
        """Get all accounts for a specific user"""
        async with session_maker() as session:
            result = await session.execute(
                select(Account)
                .where(Account.user_id == user_id)
                .order_by(Account.name)
            )
            return list(result.scalars().all())
    
    async def get_account_by_id(self, account_id: int, user_id: int, session) -> Optional[Account]:
        """Get a specific account by ID for a user"""
        result = await session.execute(
            select(Account)
            .where(Account.id == account_id, Account.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_account(self, user_id: int, name: str, initial_amount: float = 0.0) -> Account:
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
    
    async def update_account_balance(self, account_id: int, user_id: int, new_balance: float) -> Optional[Account]:
        """Update an account's balance"""
        async with session_maker() as session:
            account = await self.get_account_by_id(account_id, user_id, session)
            if account:
                account.amount = new_balance
                await session.commit()
                await session.refresh(account)
                return account
            return None
