import pytest
from playhouse.pwasyncio import AsyncSqliteDatabase

from core.models import Account, Transaction, db
from core.service import create_account, get_account_by_id, get_user_accounts

@pytest.mark.asyncio
async def test_create_and_get_account():
    async with db:
        test_user_id = 1
        test_name = "Test Account"
        test_amount = 100.0

        account = await create_account(
            user_id=test_user_id,
            name=test_name,
            adjustment_amount=test_amount
        )

        accounts = await get_user_accounts(test_user_id)
        assert len(accounts) > 0

