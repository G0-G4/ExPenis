from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from core.database import session_maker
from core.models.category import Category

class CategoryService:

    async def get_user_income_categories(self, user_id: int) -> List[Category]:
        """Get income categories for a specific user"""
        async with session_maker() as session:
            result = await session.execute(
                select(Category)
                .where(
                    Category.user_id == user_id,
                    Category.type == "income"
                )
                .order_by(Category.name)
            )
            return list(result.scalars().all())

    async def get_user_expense_categories(self, user_id: int) -> List[Category]:
        """Get expense categories for a specific user"""
        async with session_maker() as session:
            result = await session.execute(
                select(Category)
                .where(
                    Category.user_id == user_id,
                    Category.type == "expense"
                )
                .order_by(Category.name)
            )
            return list(result.scalars().all())

    async def get_user_categories_by_type(self, user_id: int, category_type: str) -> List[Category]:
        """Get categories of a specific type for a user"""
        async with session_maker() as session:
            result = await session.execute(
                select(Category)
                .where(
                    Category.user_id == user_id,
                    Category.type == category_type
                )
                .order_by(Category.name)
            )
            return list(result.scalars().all())
