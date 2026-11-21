import pytest
from httpx import ASGITransport, AsyncClient

from src.expenis.core.models import Transaction, db
from src.expenis.core.service import create_account, create_category, save_transaction
from src.expenis.server.application import app, auth


@pytest.fixture
async def client():
    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            client.headers["Authorization"] = f"Bearer {auth.create_access_token(uid='1')}"
            yield client


@pytest.fixture
async def history():
    async with db:
        account = await create_account(1, "Cash", 0.0)
        category = await create_category(1, "Food", "expense")
        transaction = await save_transaction(Transaction(
            user_id=1, account=account, category=category, amount=10.0,
        ))
        foreign_account = await create_account(2, "Private", 0.0)
        foreign_category = await create_category(2, "Private", "expense")
        foreign_transaction = await save_transaction(Transaction(
            user_id=2, account=foreign_account, category=foreign_category, amount=20.0,
        ))
        return account, category, transaction, foreign_category, foreign_transaction


def transaction_request(account_id: int, category_id: int) -> dict:
    return {
        "account_id": account_id,
        "category_id": category_id,
        "amount": 99.0,
        "description": "Changed",
        "created_at": "2026-11-21T12:00:00Z",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("foreign", [False, True])
@pytest.mark.parametrize("method", ["GET", "PUT"])
async def test_missing_or_foreign_transaction_returns_404(client, history, foreign, method):
    account, category, _, _, foreign_transaction = history
    transaction_id = foreign_transaction.id if foreign else 99999
    kwargs = {"json": transaction_request(account.id, category.id)} if method == "PUT" else {}

    response = await client.request(method, f"/api/transactions/{transaction_id}", **kwargs)

    assert response.status_code == 404
    assert response.json()["detail"] == "transaction not found"
    async with db:
        stored = await db.run(lambda: Transaction.get_by_id(foreign_transaction.id))
        assert stored.amount == 20.0


@pytest.mark.asyncio
@pytest.mark.parametrize("foreign", [False, True])
@pytest.mark.parametrize("method", ["POST", "PUT"])
async def test_missing_or_foreign_category_rejected_without_writes(client, history, foreign, method):
    account, _, transaction, foreign_category, _ = history
    category_id = foreign_category.id if foreign else 99999
    path = "/api/transactions" if method == "POST" else f"/api/transactions/{transaction.id}"

    response = await client.request(
        method, path, json=transaction_request(account.id, category_id),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "category not found"
    async with db:
        assert await db.run(Transaction.select().count) == 2
        stored = await db.run(lambda: Transaction.get_by_id(transaction.id))
        assert stored.amount == 10.0
        assert stored.category_id == transaction.category_id
