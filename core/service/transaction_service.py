from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date

from core.database import  get_session_async, session_maker
from core.models.transaction import Transaction

class TransactionService:

    async def create_transaction(
        self, 
        user_id: int, 
        amount: float, 
        category: str, 
        transaction_type: str, 
    ) -> Transaction:
        """Create a new transaction"""
        async with session_maker() as session, session.begin():
            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                category=category,
                type=transaction_type
            )
            session.add(transaction)
        return transaction
    
    async def get_user_transactions(
        self, 
        user_id: int, 
        limit: int = 100, 
        offset: int = 0
    ) -> List[Transaction]:
        """Get transactions for a specific user"""
        result = await session_maker().execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Get a transaction by its ID"""
        async with session_maker() as session:
            result = await session.execute(