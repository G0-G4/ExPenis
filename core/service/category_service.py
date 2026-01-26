from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from core.database import session_maker
from core.models.category import Category


from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import session_maker
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
            return (list(income.scalars().all()), list(expense.scalars().all()))

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


async def get_user_income_categories(user_id: int) -> List[Category]:
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


async def create_default_categories(user_id: int):
    """Create default categories for a new user"""
    default_income_categories = [
        '💰 Salary', 
        '📈 Investment', 
        '🎁 Gift', 
        '💸 Other Income'
    ]
    default_expense_categories = [
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
        # Check if user already has categories
        income_cats = await get_user_income_categories(user_id)
        expense_cats = await get_user_expense_categories(user_id)

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


async def ensure_user_has_categories(user_id: int):
    """Ensure user has categories, creating defaults if needed"""
    income_cats = await get_user_income_categories(user_id)
    expense_cats = await get_user_expense_categories(user_id)

    if not income_cats and not expense_cats:
        await create_default_categories(user_id)
        # Refresh the lists after creation
        income_cats = await get_user_income_categories(user_id)
        expense_cats = await get_user_expense_categories(user_id)

    return income_cats, expense_cats


async def get_user_categories_by_type(user_id: int, category_type: str) -> List[Category]:
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
