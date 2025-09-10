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
                select(Transaction).where(Transaction.id == transaction_id)
            )
            return result.scalar_one_or_none()
    
    async def get_todays_transactions(self, user_id: int) -> List[Transaction]:
        """Get today's transactions for a specific user"""
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        async with session_maker() as session:
            result = await session.execute(
                select(Transaction)
                .where(
                    Transaction.user_id == user_id,
                    Transaction.created_at >= start_of_day,
                    Transaction.created_at <= end_of_day
                )
                .order_by(Transaction.created_at.desc())
            )
            return list(result.scalars().all())
    
    async def delete_transaction(self, transaction_id: int, user_id: int) -> bool:
        """Delete a transaction"""
        async with session_maker() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
            )
            transaction = result.scalar_one_or_none()
            
            if transaction:
                await session.delete(transaction)
                await session.commit()
                return True
            return False

    async def get_user_balance(self, user_id: int) -> float:
        """Calculate user's current balance"""
        async with session_maker() as session, session.begin():
            income_result = await session.execute(
                select(func.sum(Transaction.amount))
                .where(Transaction.user_id == user_id, Transaction.type == 'income')
            )
            expense_result = await session.execute(
                select(func.sum(Transaction.amount))
                .where(Transaction.user_id == user_id, Transaction.type == 'expense')
            )
        
        total_income = income_result.scalar() or 0
        total_expense = expense_result.scalar() or 0
        
        return total_income - total_expense
    
    async def get_transactions_by_date_range(
        self, 
        user_id: int, 
        start_date: date, 
        end_date: date
    ) -> List[Transaction]:
        """Get transactions within a date range"""
        async with session_maker() as session, session.begin():
            result = await session.execute(
                select(Transaction).where(
                    Transaction.user_id == user_id,
                    Transaction.created_at >= start_date,
                    Transaction.created_at <= end_date
                )
                .order_by(Transaction.created_at.desc())
            )
        return list(result.scalars().all())
    
    async def get_category_summary(self, user_id: int) -> dict:
        """Get summary of transactions by category"""
        async with session_maker() as session, session.begin():
            result = await session.execute(
                select(
                    Transaction.category,
                    Transaction.type,
                    func.sum(Transaction.amount).label('total_amount')
                )
                .where(Transaction.user_id == user_id)
                .group_by(Transaction.category, Transaction.type)
            )
        
        summary = {}
        for row in result.all():
            category, trans_type, total_amount = row
            if category not in summary:
                summary[category] = {'income': 0, 'expense': 0}
            summary[category][trans_type] = total_amount
        
        return summary
