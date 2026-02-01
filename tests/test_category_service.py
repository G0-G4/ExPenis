import pytest

from src.expenis.core.models import db
from src.expenis.core.service.category_service import (CategoryType, DEFAULT_EXPENSE, DEFAULT_INCOME, create_category,
                                                       create_default_categories, delete_category, get_category_by_id,
                                                       get_user_categories, update_category)


@pytest.mark.asyncio
async def test_basic_crud():
    user_id = 1
    name = "Test Category"
    category_type: CategoryType = "income"

    async with db:
        # Test create and read
        await create_category(
            user_id=user_id,
            name=name,
            type=category_type
        )

        income_cats, expense_cats = await get_user_categories(user_id)
        assert len(income_cats) > 0
        cat = income_cats[0]

        retrieved_category = await get_category_by_id(user_id, cat.id)
        assert retrieved_category == cat
        assert cat.user_id == user_id
        assert cat.name == name
        assert cat.type == category_type

        # Test update
        new_name = "Updated Category"
        cat.name = new_name
        await update_category(cat)

        updated_category = await get_category_by_id(user_id, cat.id)
        assert updated_category.name == new_name

        # Test delete
        await delete_category(cat)
        deleted_category = await get_category_by_id(user_id, cat.id)
        assert deleted_category is None


@pytest.mark.asyncio
async def test_default_categories():
    user_id = 1

    async with db:
        await create_default_categories(user_id)

        income_cats, expense_cats = await get_user_categories(user_id)
        assert len(income_cats) == len(DEFAULT_INCOME)
        assert len(expense_cats) == len(DEFAULT_EXPENSE)

        # Verify types are correct
        for cat in income_cats:
            assert cat.type == 'income'
        for cat in expense_cats:
            assert cat.type == 'expense'
