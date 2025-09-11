from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date, timedelta
import calendar
from dateutil.relativedelta import relativedelta, MO, SU

from core.database import  get_session_async, session_maker
from core.helpers import calculate_period_dates, parse_custom_period_dates
from core.models.transaction import Transaction
from core.service.account_service import AccountService


class TransactionService:

    def __init__(self, account_service: AccountService):
        self.account_service = account_service

    async def create_transaction(
        self, 
        user_id: int, 
        amount: float, 
        category: str, 
        transaction_type: str,
        account_id: int
    ) -> Transaction:
        """Create a new transaction"""
        async with session_maker() as session, session.begin():
            # First, get the account to verify it exists and belongs to the user
            account = await self.account_service.get_account_by_id(account_id, user_id, session)
            
            if not account:
                raise Exception(f"Account {account_id} not found for user {user_id}")
            
            # Create the transaction
            transaction = Transaction(
                user_id=user_id,
                amount=amount,
                category=category,
                type=transaction_type,
                account_id=account_id
            )
            session.add(transaction)
        return transaction
    
    async def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Get a transaction by its ID"""
        async with session_maker() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.id == transaction_id)
            )
            return result.scalar_one_or_none()


    async def update_transaction(
        self, 
        transaction_id: int,
        user_id: int, 
        amount: float, 
        category: str, 
        transaction_type: str,
        account_id: int
    ) -> Transaction:
        """Update an existing transaction"""
        async with session_maker() as session, session.begin():
            # First, get the transaction to verify it exists and belongs to the user
            transaction = (await session.execute(
                select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
            )).scalar_one_or_none()
            
            if not transaction:
                raise Exception(f"Transaction {transaction_id} not found for user {user_id}")
            
            # Update the transaction
            transaction.amount = amount
            transaction.category = category
            transaction.type = transaction_type
            transaction.account_id = account_id
            
            session.add(transaction)
        return transaction

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

    async def get_todays_totals(self, user_id: int) -> dict:
        """Get today's total income and expenses for a specific user"""
        today = date.today()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())

        async with session_maker() as session:
            # Get total income
            income_result = await session.execute(
                select(func.sum(Transaction.amount))
                .where(
                    Transaction.user_id == user_id,
                    Transaction.type == "income",
                    Transaction.created_at >= start_of_day,
                    Transaction.created_at <= end_of_day
                )
            )
            total_income = income_result.scalar() or 0.0

            # Get total expenses
            expense_result = await session.execute(
                select(func.sum(Transaction.amount))
                .where(
                    Transaction.user_id == user_id,
                    Transaction.type == "expense",
                    Transaction.created_at >= start_of_day,
                    Transaction.created_at <= end_of_day
                )
            )
            total_expense = expense_result.scalar() or 0.0

            return {
                "total_income": total_income,
                "total_expense": total_expense,
                "net_total": total_income - total_expense
            }

    async def _get_period_statistics_data(self, user_id: int, start_date: datetime, end_date: datetime, period_label: str) -> dict:
        """Helper method to fetch statistics for a given period"""
        async with session_maker() as session:
            # Get income categories
            income_query = await session.execute(
                select(Transaction.category, func.sum(Transaction.amount).label('total'))
                .where(
                    Transaction.user_id == user_id,
                    Transaction.type == "income",
                    Transaction.created_at >= start_date,
                    Transaction.created_at <= end_date
                )
                .group_by(Transaction.category)
                .order_by(func.sum(Transaction.amount).desc())
            )
            income_categories = [
                {"category": row[0], "total": float(row[1])} 
                for row in income_query.fetchall()
            ]
            
            # Get expense categories
            expense_query = await session.execute(
                select(Transaction.category, func.sum(Transaction.amount).label('total'))
                .where(
                    Transaction.user_id == user_id,
                    Transaction.type == "expense",
                    Transaction.created_at >= start_date,
                    Transaction.created_at <= end_date
                )
                .group_by(Transaction.category)
                .order_by(func.sum(Transaction.amount).desc())
            )
            expense_categories = [
                {"category": row[0], "total": float(row[1])} 
                for row in expense_query.fetchall()
            ]
            
            # Calculate totals
            total_income = sum(cat["total"] for cat in income_categories)
            total_expense = sum(cat["total"] for cat in expense_categories)
            net_total = total_income - total_expense
            
            return {
                "period_label": period_label,
                "income_categories": income_categories,
                "expense_categories": expense_categories,
                "total_income": total_income,
                "total_expense": total_expense,
                "net_total": net_total
            }



    async def get_period_statistics(self, user_id: int, period_type: str, offset: int = 0) -> dict:
        """Get statistics for a specific period (day, week, month, year) with offset"""
        start_date, end_date, period_label = await calculate_period_dates(period_type, offset)
        return await self._get_period_statistics_data(user_id, start_date, end_date, period_label)

    async def get_custom_period_statistics(self, user_id: int, period_type: str, date_input: str) -> dict:
        """Get statistics for a custom period based on user input"""
        start_date, end_date, period_label = await parse_custom_period_dates(period_type, date_input)
        return await self._get_period_statistics_data(user_id, start_date, end_date, period_label)

