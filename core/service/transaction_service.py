from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date, timedelta
import calendar

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
    
    async def get_transaction_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Get a transaction by its ID"""
        async with session_maker() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.id == transaction_id)
            )
            return result.scalar_one_or_none()

    async def update_transaction_amount(self, transaction_id: int, user_id: int, amount: float) -> Transaction:
        """Get a transaction by its ID"""
        async with session_maker() as session, session.begin():
            transaction = (await session.execute(
                select(Transaction).where(Transaction.id == transaction_id, Transaction.user_id == user_id)
            )).scalar_one_or_none()
            if transaction is None:
                raise Exception(f"transaction {transaction_id} not found for user {user_id}")
            transaction.amount = amount
            session.add(transaction)
            session.flush()
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

    async def get_period_statistics(self, user_id: int, period_type: str, offset: int = 0) -> dict:
        """Get statistics for a specific period (day, week, month, year) with offset"""
        async with session_maker() as session:
            # Calculate date range based on period type and offset
            if period_type == "day":
                target_date = date.today() + timedelta(days=offset)
                start_date = datetime.combine(target_date, datetime.min.time())
                end_date = datetime.combine(target_date, datetime.max.time())
                period_label = target_date.strftime("%Y-%m-%d")
            elif period_type == "week":
                # Calculate week start (Monday) with offset
                today = date.today()
                days_ahead = -today.weekday()  # Monday is 0
                week_start = today + timedelta(days=days_ahead, weeks=offset)
                week_end = week_start + timedelta(days=6)
                start_date = datetime.combine(week_start, datetime.min.time())
                end_date = datetime.combine(week_end, datetime.max.time())
                period_label = f"Week {week_start.isocalendar()[1]}, {week_start.year}"
            elif period_type == "month":
                # Calculate month with offset
                today = date.today()
                first_day = today.replace(day=1)
                # Apply offset in months
                if offset != 0:
                    if offset > 0:
                        for _ in range(offset):
                            if first_day.month == 12:
                                first_day = first_day.replace(year=first_day.year + 1, month=1)
                            else:
                                first_day = first_day.replace(month=first_day.month + 1)
                    else:
                        for _ in range(-offset):
                            if first_day.month == 1:
                                first_day = first_day.replace(year=first_day.year - 1, month=12)
                            else:
                                first_day = first_day.replace(month=first_day.month - 1)
                
                # Last day of month
                if first_day.month == 12:
                    last_day = first_day.replace(day=31)
                else:
                    last_day = first_day.replace(month=first_day.month + 1, day=1) - timedelta(days=1)
                
                start_date = datetime.combine(first_day, datetime.min.time())
                end_date = datetime.combine(last_day, datetime.max.time())
                period_label = first_day.strftime("%B %Y")
            elif period_type == "year":
                target_year = date.today().year + offset
                start_date = datetime(target_year, 1, 1, 0, 0, 0)
                end_date = datetime(target_year, 12, 31, 23, 59, 59)
                period_label = str(target_year)
            else:
                raise ValueError("Invalid period type")
            
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

    async def get_custom_period_statistics(self, user_id: int, period_type: str, date_input: str) -> dict:
        """Get statistics for a custom period based on user input"""
        async with session_maker() as session:
            try:
                if period_type == "day":
                    # Parse YYYY-MM-DD
                    target_date = datetime.strptime(date_input, "%Y-%m-%d").date()
                    start_date = datetime.combine(target_date, datetime.min.time())
                    end_date = datetime.combine(target_date, datetime.max.time())
                    period_label = target_date.strftime("%Y-%m-%d")
                elif period_type == "week":
                    # Parse YYYY-WW (ISO week)
                    if '-' in date_input:
                        year, week_str = date_input.split('-')
                        year = int(year)
                        week = int(week_str.replace('W', ''))
                    else:
                        parts = date_input.split('W')
                        year = int(parts[0])
                        week = int(parts[1])
                    
                    # Get first day of the week (Monday)
                    target_date = datetime.strptime(f'{year}-W{week:02d}-1', "%Y-W%W-%w").date()
                    start_date = datetime.combine(target_date, datetime.min.time())
                    end_date = datetime.combine(target_date + timedelta(days=6), datetime.max.time())
                    period_label = f"Week {week}, {year}"
                elif period_type == "month":
                    # Parse YYYY-MM
                    target_date = datetime.strptime(date_input, "%Y-%m").date()
                    first_day = target_date.replace(day=1)
                    # Last day of month
                    if first_day.month == 12:
                        last_day = first_day.replace(day=31)
                    else:
                        last_day = first_day.replace(month=first_day.month + 1, day=1) - timedelta(days=1)
                    start_date = datetime.combine(first_day, datetime.min.time())
                    end_date = datetime.combine(last_day, datetime.max.time())
                    period_label = first_day.strftime("%B %Y")
                elif period_type == "year":
                    # Parse YYYY
                    year = int(date_input)
                    start_date = datetime(year, 1, 1, 0, 0, 0)
                    end_date = datetime(year, 12, 31, 23, 59, 59)
                    period_label = str(year)
                else:
                    raise ValueError("Invalid period type")
            except ValueError as e:
                raise ValueError(f"Invalid date format for {period_type}")
            
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
