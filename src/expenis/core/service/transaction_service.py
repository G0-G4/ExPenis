from datetime import UTC, date, datetime

from ..models import Account, Category, Transaction, db


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


async def get_transaction_by_id(transaction_id: int) -> Transaction | None:
    """Get a transaction by its ID"""
    transaction = await db.run(lambda: Transaction
                               .select()
                               .where(Transaction.id == transaction_id)
                               .prefetch(Account, Category))
    return transaction[0] if len(transaction) > 0 else None


async def save_transaction(transaction: Transaction):
    """Update an existing transaction"""
    now = datetime.now(UTC)
    transaction.created_at = now if transaction.created_at is None else transaction.created_at
    transaction.updated_at = now if transaction.updated_at is None else transaction.updated_at
    await db.run(transaction.save)

async def update_transaction(transaction: Transaction):
    """Update an existing transaction"""
    await db.run(transaction.save)

async def delete_transaction(transaction: Transaction):
    """Delete a transaction"""
    await db.run(transaction.delete_instance)

async def delete_transaction_by_id(transaction_id: int):
    """Delete a transaction"""
    await db.run(lambda: Transaction.delete_by_id(transaction_id))

