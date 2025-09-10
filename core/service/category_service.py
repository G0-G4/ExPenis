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
                .order_by(Category.id)
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
                .order_by(Category.id)
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
                .order_by(Category.id)
            )
            return list(result.scalars().all())

    async def create_default_categories(self, user_id: int):
        """Create default categories for a new user"""
        default_income_categories = ['Salary', 'Investment', 'Gift', 'Other Income']
        default_expense_categories = ['Food', 'Transport', 'Entertainment', 'Shopping', 'Learning', 'Cafe', 'Other Expense']
        
        async with session_maker() as session:
            # Check if user already has categories
            income_cats = await self.get_user_income_categories(user_id)
            expense_cats = await self.get_user_expense_categories(user_id)
            
            # Only create defaults if user has no categories of that type
            if not income_cats:
                for cat_name in default_income_categories:
                    category = Category(user_id=user_id, name=cat_name, type="income")
                    session.add(category)
            
            if not expense_cats:
                for cat_name in default_expense_categories:
                    category = Category(user_id=user_id, name=cat_name, type="expense")
                    session.add(category)
            
            await session.commit()

    async def ensure_user_has_categories(self, user_id: int):
        """Ensure user has categories, creating defaults if needed"""
        income_cats = await self.get_user_income_categories(user_id)
        expense_cats = await self.get_user_expense_categories(user_id)
        
        if not income_cats and not expense_cats:
            await self.create_default_categories(user_id)
            # Refresh the lists after creation
            income_cats = await self.get_user_income_categories(user_id)
            expense_cats = await self.get_user_expense_categories(user_id)
            
        return income_cats, expense_cats
