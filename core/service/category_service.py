from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.models.database import session_maker

from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.database import session_maker
from core.models.category import Category


class CategoryService:
    @staticmethod
    async def get_user_categories(user_id: int) -> Tuple[List[Category], List[Category]]:
        """Get all categories grouped by type"""
        async with session_maker() as session:
            income = await session.execute(
                select(Category)
                .where(Category.user_id == user_id, Category.type == "income")
                .order_by(Category.name)
            )
            expense = await session.execute(
                select(Category)
                .where(Category.user_id == user_id, Category.type == "expense")
                .order_by(Category.name)
            )
            return list(income.scalars().all()), list(expense.scalars().all())

    @staticmethod
    async def get_category_by_id(category_id: int, user_id: int) -> Optional[Category]:
        """Get a specific category by ID"""
        async with session_maker() as session:
            result = await session.execute(
                select(Category)
                .where(Category.id == category_id, Category.user_id == user_id)
            )
            return result.scalar_one_or_none()

    @staticmethod
    async def create_category(user_id: int, name: str, category_type: str) -> Category:
        """Create a new category"""
        if category_type not in ("income", "expense"):
            raise ValueError("Category type must be 'income' or 'expense'")

        async with session_maker() as session:
            category = Category(
                user_id=user_id,
                name=name,
                type=category_type
            )
            session.add(category)
            await session.commit()
            await session.refresh(category)
            return category

    @staticmethod
    async def update_category(category_id: int, user_id: int, **kwargs) -> Optional[Category]:
        """Update category properties"""
        async with session_maker() as session:
            category = await CategoryService.get_category_by_id(category_id, user_id)
            if not category:
                return None

            for key, value in kwargs.items():
                if hasattr(category, key):
                    setattr(category, key, value)

            await session.commit()
            await session.refresh(category)
            return category

    @staticmethod
    async def delete_category(category_id: int, user_id: int) -> bool:
        """Delete a category"""
        async with session_maker() as session:
            category = await CategoryService.get_category_by_id(category_id, user_id)
            if not category:
                return False

            await session.delete(category)
            await session.commit()
            return True

    @staticmethod
    async def ensure_default_categories(user_id: int) -> Tuple[List[Category], List[Category]]:
        """Ensure user has default categories"""
        income_cats, expense_cats = await CategoryService.get_user_categories(user_id)
        
        if not income_cats and not expense_cats:
            default_income = [
                '💰 Salary', 
                '📈 Investment', 
                '🎁 Gift', 
                '💸 Other Income'
            ]
            default_expense = [
                '☕ Cafe', 
                '🍔 Food', 
                '👪 Family', 
                '🎁 Presents', 
                '🎭 Entertainment', 
                '📚 Learning', 
                '🚕 Transport', 
                '🏠 Rent', 
                '🏥 Health', 
                '💳 Monthly fee'
            ]

            async with session_maker() as session:
                for name in default_income:
                    session.add(Category(user_id=user_id, name=name, type="income"))
                for name in default_expense:
                    session.add(Category(user_id=user_id, name=name, type="expense"))
                await session.commit()

            income_cats, expense_cats = await CategoryService.get_user_categories(user_id)

        return income_cats, expense_cats
