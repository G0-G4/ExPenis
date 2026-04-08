from peewee import AutoField, ForeignKeyField, Model

from .database import db
from .tag import Tag
from .transaction import Transaction


class TransactionTag(Model):
    id = AutoField(primary_key=True)
    transaction = ForeignKeyField(Transaction, backref="transaction_tags", on_delete="CASCADE")
    tag = ForeignKeyField(Tag, backref="transaction_tags", on_delete="CASCADE")

    class Meta:
        database = db
        table_name = "transaction_tags"
        indexes = ((('transaction', 'tag'), True),)
