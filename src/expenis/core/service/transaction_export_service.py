from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from peewee import fn  # type: ignore[import-untyped]

from ..errors import NotFoundException
from ..models import Account, Category, Transaction, db
from .transaction_service import get_transaction_tags_by_transaction_ids


class ExportValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ExportFilter:
    date_from: date | None = None
    date_to: date | None = None
    account_ids: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if (self.date_from is None) != (self.date_to is None):
            raise ExportValidationError("Укажите обе границы периода")
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ExportValidationError("Начальная дата позже конечной")
        if self.account_ids is not None:
            if not self.account_ids or any(value <= 0 for value in self.account_ids):
                raise ExportValidationError("Выберите хотя бы один счёт")
            object.__setattr__(self, "account_ids", tuple(dict.fromkeys(self.account_ids)))


@dataclass(frozen=True)
class ExportRow:
    created_at: datetime
    type: Literal["income", "expense"]
    amount: float
    currency: str
    account: str
    category: str
    description: str
    exchange_rate: float
    amount_rubles: float
    tags: tuple[str, ...]


async def get_export_accounts(user_id: int) -> list[Account]:
    return await db.list(
        Account.select().where(Account.user_id == user_id).order_by(Account.name, Account.id)
    )


async def get_export_rows(user_id: int, filters: ExportFilter) -> list[ExportRow]:
    if filters.account_ids is not None:
        accounts = await db.list(Account.select(Account.id).where(
            (Account.user_id == user_id) & Account.id.in_(filters.account_ids)
        ))
        if len(accounts) != len(filters.account_ids):
            raise NotFoundException("Счёт не найден")

    query = (Transaction.select(Transaction, Account, Category)
             .join(Account).switch(Transaction).join(Category)
             .where(Transaction.user_id == user_id))
    if filters.account_ids is not None:
        query = query.where(Transaction.account.in_(filters.account_ids))
    if filters.date_from is not None and filters.date_to is not None:
        # SQLite DATE converts offsets to UTC; the stored calendar day must stay intact.
        calendar_day = fn.SUBSTR(Transaction.created_at, 1, 10)
        query = query.where(calendar_day.between(
            filters.date_from.isoformat(), filters.date_to.isoformat(),
        ))
    transactions = await db.list(query)
    dated = [
        (tx, tx.created_at if isinstance(tx.created_at, datetime)
         else datetime.fromisoformat(tx.created_at))
        for tx in transactions
    ]
    dated.sort(key=lambda item: (item[1].replace(tzinfo=None), item[0].id))
    tags: dict[int, list[str]] = {}
    # Stay below SQLite parameter limits for long histories.
    ids = [tx.id for tx, _ in dated]
    for start in range(0, len(ids), 500):
        tags.update(await get_transaction_tags_by_transaction_ids(user_id, ids[start:start + 500]))
    return [
        ExportRow(
            created_at=created_at,
            type=tx.category.type,
            amount=tx.amount,
            currency=tx.account.currency_code,
            account=tx.account.name + (" (удалён)" if tx.account.is_deleted else ""),
            category=tx.category.name,
            description=tx.description or "",
            exchange_rate=tx.exchange_rate,
            amount_rubles=tx.amount * tx.exchange_rate,
            tags=tuple(tags.get(tx.id, [])),
        )
        for tx, created_at in dated
    ]
