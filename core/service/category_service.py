from datetime import UTC, datetime
from typing import Literal

from core.models.category import Category
from core.models.database import db

CategoryType = Literal['income', 'expense']

DEFAULT_INCOME = [
    '💰 Salary',
    '📈 Investment',
    '🎁 Gift',
    '💸 Other Income'
]
DEFAULT_EXPENSE = [
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


async def get_user_categories(user_id: int) -> tuple[list[Category], list[Category]]:
    categories = await db.list(Category.select()
                               .where(Category.user_id == user_id))
    return [c for c in categories if c.type == 'income'], [c for c in categories if c.type == 'expense']


async def get_category_by_id(user_id: int, id: int) -> Category | None:
    category = await db.run(lambda:
                            Category.get_or_none(Category.id == id))
    return category


async def create_category(user_id: int, name: str, type: CategoryType):
    now = datetime.now(UTC)
    category = Category(user_id=user_id, name=name, type=type, created_at=now, updated_at=now)
    await db.run(category.save)


async def update_category(category: Category):
    now = datetime.now(UTC)
    category.updated_at = now
    await db.run(category.save)


async def delete_category(category: Category):
    await db.run(category.delete_instance)

async def delete_category_by_id(category_id: int):
    """Delete a category"""
    await db.run(lambda: Category.delete_by_id(category_id))


async def create_default_categories(user_id: int):
    now = datetime.now(UTC)
    async with db.atomic():
        income, expense = await get_user_categories(user_id)
        if not income and not expense:
            incomes = [
                Category(
                    user_id=user_id,
                    name=category,
                    type='income',
                    created_at=now,
                    updated_at=now
                )
                for category in DEFAULT_INCOME
            ]
            expenses = [
                Category(
                    user_id=user_id,
                    name=category,
                    type='expense',
                    created_at=now,
                    updated_at=now
                )
                for category in DEFAULT_EXPENSE
            ]
            await db.run(lambda: Category.bulk_create(incomes + expenses))
