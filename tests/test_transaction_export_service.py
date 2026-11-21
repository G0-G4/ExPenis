from datetime import date, datetime

import pytest

from src.expenis.core.errors import NotFoundException
from src.expenis.core.models import Account, Category, Transaction, db
from src.expenis.core.service.transaction_export_service import (
    ExportFilter, ExportValidationError, get_export_accounts, get_export_rows,
)
from src.expenis.core.service.transaction_service import set_transaction_tags


@pytest.fixture
async def export_history():
    async with db:
        account = await db.run(lambda: Account.create(user_id=1, name="Кошелёк 💰", currency_code="EUR"))
        deleted = await db.run(lambda: Account.create(user_id=1, name="Старый", is_deleted=True))
        foreign = await db.run(lambda: Account.create(user_id=2, name="Чужой"))
        category = await db.run(lambda: Category.create(user_id=1, name="Еда 🍕", type="expense"))
        items = []
        for owner, acc, when, amount in [
            (1, account, "2000-01-01T12:00:00", 5),
            (1, account, "2026-11-01T00:00:00+14:00", 12.5),
            (1, deleted, "2026-11-21T23:59:59.999999-12:00", -12.5),
            (1, account, "2026-11-21T23:59:59.999999-12:00", 20),
            (1, account, "2026-11-22T00:00:00", 1),
            (2, foreign, "2026-11-10T12:00:00", 99),
        ]:
            tx = await db.run(lambda: Transaction.create(
                user_id=owner, account=acc, category=category, amount=amount,
                created_at=datetime.fromisoformat(when), exchange_rate=100,
                description=None,
            ))
            items.append(tx)
        await set_transaction_tags(1, items[1].id, ['еда,дом', 'Отпуск "лето"'])
        yield account, deleted, foreign, items


@pytest.mark.asyncio
async def test_full_history_and_inclusive_wall_clock_period(export_history):
    rows = await get_export_rows(1, ExportFilter())
    assert len(rows) == 5
    assert rows[0].created_at.year == 2000
    rows = await get_export_rows(1, ExportFilter(date(2026, 11, 1), date(2026, 11, 21)))
    assert [row.amount for row in rows] == [12.5, -12.5, 20]
    assert rows[0].created_at.isoformat() == "2026-11-01T00:00:00+14:00"
    assert rows[1].created_at.day == 21


@pytest.mark.asyncio
async def test_accounts_selection_ownership_and_no_writes(export_history):
    account, deleted, foreign, _ = export_history
    before = await db.run(lambda: list(Transaction.select().dicts()))
    accounts = await get_export_accounts(1)
    assert {a.id for a in accounts} == {account.id, deleted.id}
    rows = await get_export_rows(1, ExportFilter(account_ids=(deleted.id, deleted.id)))
    assert len(rows) == 1
    assert rows[0].account == "Старый (удалён)"
    for ids in [(foreign.id,), (99999,), (account.id, foreign.id)]:
        with pytest.raises(NotFoundException, match="Счёт не найден"):
            await get_export_rows(1, ExportFilter(account_ids=ids))
    assert before == await db.run(lambda: list(Transaction.select().dicts()))


@pytest.mark.asyncio
async def test_rows_preserve_values_and_tags(export_history, monkeypatch):
    def unexpected(*args, **kwargs):
        raise AssertionError("Export must not request current exchange rates")
    monkeypatch.setattr(
        "src.expenis.core.service.exchage_rate_service.get_currency_exchange_rate", unexpected,
    )
    rows = await get_export_rows(1, ExportFilter())
    row = rows[1]
    assert row.type == "expense"
    assert row.amount == 12.5 and row.exchange_rate == 100 and row.amount_rubles == 1250
    assert row.account == "Кошелёк 💰" and row.category == "Еда 🍕"
    assert row.description == "" and set(row.tags) == {'еда,дом', 'Отпуск "лето"'}
    assert rows[2].amount == -12.5 and rows[2].amount_rubles == -1250
    assert rows[2].tags == ()
    assert await get_export_rows(99, ExportFilter()) == []


@pytest.mark.parametrize("kwargs", [
    {"date_from": date(2026, 11, 1)}, {"date_to": date(2026, 11, 1)},
    {"date_from": date(2026, 11, 2), "date_to": date(2026, 11, 1)},
    {"account_ids": ()}, {"account_ids": (0,)},
])
def test_invalid_filter(kwargs):
    with pytest.raises(ExportValidationError):
        ExportFilter(**kwargs)
