import logging
from datetime import UTC, datetime
from typing import Literal

from peewee import SQL  # type: ignore[import-untyped]

from ..models import Category, db
from ..utils.category_colors import CATEGORY_COLORS

logger = logging.getLogger(__name__)

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
                            Category.get_or_none((Category.id == id) & (Category.user_id == user_id)))
    return category


async def create_category(user_id: int, name: str, type: CategoryType) -> Category:
    now = datetime.now(UTC)
    # Choosing and inserting in one SQLite statement also serializes competing writers.
    palette = " UNION ALL ".join(
        f"SELECT {index} AS position, ? AS color" for index in range(len(CATEGORY_COLORS))
    )
    color = SQL(
        "(SELECT p.color FROM (" + palette + ") AS p "
        "LEFT JOIN categories AS c ON c.color = p.color AND c.user_id = ? "
        "GROUP BY p.position, p.color ORDER BY COUNT(c.id), p.position LIMIT 1)",
        (*CATEGORY_COLORS, user_id),
    )
    category_id = await db.run(lambda: Category.insert(
        user_id=user_id, name=name, type=type, color=color,
        created_at=now, updated_at=now,
    ).execute())
    category = await get_category_by_id(user_id, category_id)
    assert category is not None
    logger.info("category_created")
    return category


async def update_category(
    category: Category, *, name: str | None = None,
    type: CategoryType | None = None, color: str | None = None,
) -> Category:
    if color is not None and color not in CATEGORY_COLORS:
        raise ValueError("Unsupported category color")
    if name is not None:
        category.name = name
    if type is not None:
        category.type = type
    fields = [Category.name, Category.type, Category.updated_at]
    if color is not None:
        category.color = color
        fields.append(Category.color)
    category.updated_at = datetime.now(UTC)
    # Omitted color must not overwrite a concurrently saved choice.
    await db.run(lambda: category.save(only=fields))
    logger.info("category_updated")
    stored_category = await get_category_by_id(category.user_id, category.id)
    assert stored_category is not None
    return stored_category


async def delete_category(category: Category):
    await db.run(category.delete_instance)

async def delete_category_by_id(category_id: int):
    """Delete a category"""
    await db.run(lambda: Category.delete_by_id(category_id))

async def delete_category_by_id_and_user_id(user_id: int, category_id: int):
    logger.info("category_deleted")
    await db.run(lambda: Category.delete().where((Category.id == category_id) & (Category.user_id == user_id)).execute())


async def create_default_categories(user_id: int):
    async with db.atomic():
        income, expense = await get_user_categories(user_id)
        if not income and not expense:
            logger.info("default_categories_created")
            for name in DEFAULT_INCOME:
                await create_category(user_id, name, 'income')
            for name in DEFAULT_EXPENSE:
                await create_category(user_id, name, 'expense')
