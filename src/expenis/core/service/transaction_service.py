import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal

from peewee import fn

from ..models import Account, Category, Tag, Transaction, TransactionTag, db

logger = logging.getLogger(__name__)


def normalize_tags(tags: list[str] | None) -> list[str]:
    if tags is None:
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        clean_tag = tag.strip()
        if clean_tag and clean_tag not in seen:
            normalized.append(clean_tag)
            seen.add(clean_tag)
    return normalized


async def get_transactions_for_period(user_id: int, start_date: date, end_date: date) -> list[Transaction]:
    """Get transactions for a specific period"""
    start_datetime = datetime.combine(start_date, datetime.min.time())
    end_datetime = datetime.combine(end_date, datetime.max.time())
    transactions = await db.run(lambda: Transaction
                                 .select()
                                 .where(
                                    (Transaction.user_id == user_id) &
                                    (Transaction.created_at >= start_datetime) &
                                    (Transaction.created_at <= end_datetime))
                                 .order_by(Transaction.created_at.desc())
                                 .prefetch(Account, Category)
                                )
    return transactions


# TODO deprecated use get_transaction_by_id_and_user_id
async def get_transaction_by_id(transaction_id: int) -> Transaction | None:
    """Get a transaction by its ID"""
    transaction = await db.run(lambda: Transaction
                               .select()
                               .where(Transaction.id == transaction_id)
                               .prefetch(Account, Category))
    return transaction[0] if len(transaction) > 0 else None

async def get_transaction_by_id_and_user_id(user_id: int, transaction_id: int) -> Transaction | None:
    """Get a transaction by its ID"""
    transaction = await db.run(lambda: Transaction
                               .select()
                               .where((Transaction.id == transaction_id) & (Transaction.user_id == user_id))
                               .prefetch(Account, Category))
    return transaction[0] if len(transaction) > 0 else None


async def save_transaction(transaction: Transaction) -> Transaction:
    now = datetime.now(UTC)
    transaction.created_at = now if transaction.created_at is None else transaction.created_at
    transaction.updated_at = now if transaction.updated_at is None else transaction.updated_at
    await db.run(transaction.save)
    logger.info("transaction_saved")
    return transaction

async def update_transaction(transaction: Transaction) -> Transaction:
    await db.run(transaction.save)
    logger.info("transaction_updated")
    return transaction

async def delete_transaction(transaction: Transaction):
    """Delete a transaction"""
    await db.run(transaction.delete_instance)

async def delete_transaction_by_id(transaction_id: int):
    """Delete a transaction"""
    await db.run(lambda: Transaction.delete_by_id(transaction_id))

async def delete_transaction_by_id_and_user_id(user_id: int, transaction_id: int):
    logger.info("transaction_deleted")
    await db.run(lambda: Transaction.delete().where((Transaction.id == transaction_id) & (Transaction.user_id == user_id)).execute())


async def set_transaction_tags(user_id: int, transaction_id: int, tags: list[str] | None) -> list[str]:
    normalized_tags = normalize_tags(tags)

    async with db.atomic():
        await db.run(
            lambda: TransactionTag.delete().where(TransactionTag.transaction_id == transaction_id).execute()
        )

        if not normalized_tags:
            return []

        existing_tags = await db.list(
            Tag.select().where((Tag.user_id == user_id) & (Tag.name.in_(normalized_tags)))
        )
        existing_names = {tag.name for tag in existing_tags}

        now = datetime.now(UTC)
        new_tags = [
            Tag(user_id=user_id, name=tag_name, created_at=now, updated_at=now)
            for tag_name in normalized_tags
            if tag_name not in existing_names
        ]
        if new_tags:
            await db.run(lambda: Tag.bulk_create(new_tags))

        all_tags = await db.list(
            Tag.select().where((Tag.user_id == user_id) & (Tag.name.in_(normalized_tags)))
        )
        tags_by_name = {tag.name: tag for tag in all_tags}

        await db.run(
            lambda: TransactionTag.bulk_create([
                TransactionTag(transaction=transaction_id, tag=tags_by_name[tag_name].id)
                for tag_name in normalized_tags
            ])
        )

    return normalized_tags


async def get_transaction_tags_by_transaction_ids(user_id: int, transaction_ids: list[int]) -> dict[int, list[str]]:
    if not transaction_ids:
        return {}

    transaction_tags = await db.list(
        TransactionTag.select(TransactionTag, Tag)
        .join(Tag)
        .where((Tag.user_id == user_id) & (TransactionTag.transaction_id.in_(transaction_ids)))
        .order_by(Tag.name)
    )

    tags_by_transaction_id: dict[int, list[str]] = {transaction_id: [] for transaction_id in transaction_ids}
    for transaction_tag in transaction_tags:
        tags_by_transaction_id[transaction_tag.transaction_id].append(transaction_tag.tag.name)
    return tags_by_transaction_id


async def get_user_tags(user_id: int) -> list[str]:
    tags = await db.list(
        Tag.select().where(Tag.user_id == user_id).order_by(Tag.name)
    )
    return [tag.name for tag in tags]


@dataclass(frozen=True)
class TagPeriod:
    name: str
    type: Literal["income", "expense"]
    first_at: datetime
    last_at: datetime


def _as_datetime(value: datetime | str) -> datetime:
    # Aggregates bypass the field converter, and tz-aware values are stored as ISO text.
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


async def get_user_tag_periods(user_id: int) -> list[TagPeriod]:
    """First and last transaction time per tag, split by income/expense."""
    first_at = fn.MIN(Transaction.created_at).alias("first_at")
    last_at = fn.MAX(Transaction.created_at).alias("last_at")
    rows = await db.list(
        TransactionTag
        .select(Tag.name, Category.type, first_at, last_at)
        .join(Tag)
        .switch(TransactionTag)
        .join(Transaction)
        .join(Category)
        .where((Tag.user_id == user_id) & (Transaction.user_id == user_id))
        .group_by(Tag.name, Category.type)
        .order_by(Tag.name, Category.type)
        .dicts()
    )
    return [
        TagPeriod(
            name=row["name"],
            type=row["type"],
            first_at=_as_datetime(row["first_at"]),
            last_at=_as_datetime(row["last_at"]),
        )
        for row in rows
    ]
