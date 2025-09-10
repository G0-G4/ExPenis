from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date, timedelta
import calendar
from dateutil.relativedelta import relativedelta, MO, SU

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

    async def _calculate_period_dates(self, period_type: str, offset: int = 0) -> tuple[datetime, datetime, str]:
        """Helper method to calculate date ranges for relative periods"""
        base_date = date.today()
        start_date = None
        end_date = None
        period_label = ""

        if period_type == "day":
            target_date = base_date + relativedelta(days=offset)
            start_date = datetime.combine(target_date, datetime.min.time())
            end_date = datetime.combine(target_date, datetime.max.time())
            period_label = target_date.strftime("%Y-%m-%d")
        elif period_type == "week":
            # Find the Monday of the current week
            current_week_start = base_date + relativedelta(weekday=MO(-1))
            # Apply offset in weeks
            target_week_start = current_week_start + relativedelta(weeks=offset)
            target_week_end = target_week_start + relativedelta(weekday=SU)
            start_date = datetime.combine(target_week_start, datetime.min.time())
            end_date = datetime.combine(target_week_end, datetime.max.time())
            period_label = f"Week {target_week_start.isocalendar()[1]}, {target_week_start.year}"
        elif period_type == "month":
            # Get the first day of the current month
            current_month_start = base_date.replace(day=1)
            # Apply offset in months
            target_month_start = current_month_start + relativedelta(months=offset)
            # Get the last day of the target month
            target_month_end = target_month_start + relativedelta(months=1, days=-1)
            start_date = datetime.combine(target_month_start, datetime.min.time())
            end_date = datetime.combine(target_month_end, datetime.max.time())
            period_label = target_month_start.strftime("%B %Y")
        elif period_type == "year":
            target_year = base_date.year + offset
            start_date = datetime(target_year, 1, 1, 0, 0, 0)
            end_date = datetime(target_year, 12, 31, 23, 59, 59)
            period_label = str(target_year)
        else:
            raise ValueError("Invalid period type")
        
        return start_date, end_date, period_label

    async def _parse_custom_period_dates(self, period_type: str, date_input: str) -> tuple[datetime, datetime, str]:
        """Helper method to parse custom period dates"""
        try:
            if period_type == "day":
                # Parse YYYY-MM-DD
                target_date = datetime.strptime(date_input, "%Y-%m-%d").date()
                start_date = datetime.combine(target_date, datetime.min.time())
                end_date = datetime.combine(target_date, datetime.max.time())
                period_label = target_date.strftime("%Y-%m-%d")
            elif period_type == "week":
                # Parse YYYY-WW (ISO week number)
                year, week = map(int, date_input.split("-W"))
                target_week_start = datetime.strptime(f'{year}-{week}-1', '%Y-%U-%w').date()
                target_week_end = target_week_start + relativedelta(weekday=SU)
                start_date = datetime.combine(target_week_start, datetime.min.time())
                end_date = datetime.combine(target_week_end, datetime.max.time())
                period_label = f"Week {week}, {year}"
            elif period_type == "month":
                # Parse YYYY-MM
                target_date = datetime.strptime(date_input, "%Y-%m").date()
                target_month_start = target_date.replace(day=1)
                target_month_end = target_month_start + relativedelta(months=1, days=-1)
                start_date = datetime.combine(target_month_start, datetime.min.time())
                end_date = datetime.combine(target_month_end, datetime.max.time())
                period_label = target_month_start.strftime("%B %Y")
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
        
        return start_date, end_date, period_label

    async def get_period_statistics(self, user_id: int, period_type: str, offset: int = 0) -> dict:
        """Get statistics for a specific period (day, week, month, year) with offset"""
        start_date, end_date, period_label = await self._calculate_period_dates(period_type, offset)
        return await self._get_period_statistics_data(user_id, start_date, end_date, period_label)

    async def get_custom_period_statistics(self, user_id: int, period_type: str, date_input: str) -> dict:
        """Get statistics for a custom period based on user input"""
        start_date, end_date, period_label = await self._parse_custom_period_dates(period_type, date_input)
        return await self._get_period_statistics_data(user_id, start_date, end_date, period_label)
