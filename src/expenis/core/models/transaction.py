from datetime import UTC, datetime

from peewee import AutoField, DateTimeField, FloatField, ForeignKeyField, IntegerField, Model, TextField

from .account import Account
from .category import Category
from .database import db


class Transaction(Model):
    id = AutoField(primary_key=True)
    user_id = IntegerField(null=False)
    account = ForeignKeyField(Account, backref="transactions")
    category = ForeignKeyField(Category, backref="transactions")
    amount = FloatField(null=False, default=0.0)
    description = TextField(null=True)
    created_at = DateTimeField(null=False, default=lambda: datetime.now(UTC))
    updated_at = DateTimeField(null=False, default=lambda: datetime.now(UTC))

    class Meta:
        database = db
        table_name = "transactions"
