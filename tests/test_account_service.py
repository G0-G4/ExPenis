import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from core.service.account_service import AccountService
from core.models.account import Account
from core.database import session_maker

@pytest.mark.asyncio
async def test_create_and_get_account():
    test_user_id = 1
    test_name = "Test Account"
    test_amount = 100.0
    
    # Test creation
    account = await AccountService.create_account(
        user_id=test_user_id,
        name=test_name,
        initial_amount=test_amount
    )
    assert account is not None
    assert account.name == test_name
    assert account.amount == test_amount

    # Test get by ID
    fetched = await AccountService.get_account_by_id(account.id, test_user_id)
    assert fetched is not None
    assert fetched.id == account.id

    # Test get all accounts
    accounts = await AccountService.get_user_accounts(test_user_id)
    assert len(accounts) > 0
    assert any(a.id == account.id for a in accounts)

    # Test balance calculation
    balance = await AccountService.calculate_account_balance(account.id, test_user_id)
    assert balance == test_amount

    # Test update
    updated = await AccountService.update_account(
        account.id, 
        test_user_id,
        name="Updated Name",
        amount=200.0
    )
    assert updated.name == "Updated Name"
    assert updated.amount == 200.0

    # Test delete
    deleted = await AccountService.delete_account(account.id, test_user_id)
    assert deleted is True
    assert await AccountService.get_account_by_id(account.id, test_user_id) is None

@pytest.mark.asyncio
async def test_account_with_balances():
    test_user_id = 2
    account = await AccountService.create_account(
        user_id=test_user_id,
        name="Balance Test",
        initial_amount=50.0
    )
    
    accounts_with_balances = await AccountService.get_accounts_with_balances(test_user_id)
    assert len(accounts_with_balances) > 0
    assert accounts_with_balances[0].amount == 50.0

    # Cleanup
    await AccountService.delete_account(account.id, test_user_id)
