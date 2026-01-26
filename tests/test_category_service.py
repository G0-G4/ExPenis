import pytest
from core.service.category_service import CategoryService
from core.models.category import Category
from core.database import session_maker

@pytest.mark.asyncio
async def test_category_crud():
    test_user_id = 10
    test_name = "Test Category"
    
    # Test creation
    category = await CategoryService.create_category(
        user_id=test_user_id,
        name=test_name,
        category_type="income"
    )
    assert category is not None
    assert category.name == test_name
    assert category.type == "income"

    # Test get by ID
    fetched = await CategoryService.get_category_by_id(category.id, test_user_id)
    assert fetched is not None
    assert fetched.id == category.id

    # Test get all categories
    income, expense = await CategoryService.get_user_categories(test_user_id)
    assert len(income) > 0
    assert any(c.id == category.id for c in income)

    # Test update
    updated = await CategoryService.update_category(
        category.id,
        test_user_id,
        name="Updated Name"
    )
    assert updated.name == "Updated Name"

    # Test delete
    deleted = await CategoryService.delete_category(category.id, test_user_id)
    assert deleted is True
    assert await CategoryService.get_category_by_id(category.id, test_user_id) is None

@pytest.mark.asyncio
async def test_default_categories():
    test_user_id = 20
    income, expense = await CategoryService.ensure_default_categories(test_user_id)
    
    assert len(income) >= 4  # Default income categories
    assert len(expense) >= 10  # Default expense categories

    # Second call should return same categories
    income2, expense2 = await CategoryService.ensure_default_categories(test_user_id)
    assert len(income) == len(income2)
    assert len(expense) == len(expense2)

    # Cleanup
    async with session_maker() as session:
        for cat in income + expense:
            await session.delete(cat)
        await session.commit()
