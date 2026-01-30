import pytest

from src.expenis.core.models import db
from src.expenis.core import create_account, get_account_by_id, get_user_account_with_balance, get_user_accounts, \
    get_user_accounts_with_balance


@pytest.mark.asyncio
async def test_basic_crud():
    user_id = 1
    name = "name"
    adjustment_amount = 10.0
    async with db:
        await create_account(
            user_id=user_id,
            name=name,
            adjustment_amount=adjustment_amount
        )

        accounts = await get_user_accounts(user_id)
        assert len(accounts) > 0
        acc = accounts[0]
        retrieved_account = await get_account_by_id(user_id, acc.id)
        assert retrieved_account == acc
        assert acc.user_id == user_id
        assert acc.name == name
        assert acc.adjustment_amount == adjustment_amount

        accounts_with_balances = await get_user_accounts_with_balance(user_id)
        assert len(accounts_with_balances) > 0
        acc, blnc = accounts_with_balances[0]
        retrieved_account, balance = await get_user_account_with_balance(user_id, acc.id)
        assert acc == retrieved_account
        assert blnc == balance
        assert blnc == adjustment_amount
