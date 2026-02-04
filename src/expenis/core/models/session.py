from datetime import UTC, datetime

from peewee import AutoField, Check, DateTimeField, FloatField, ForeignKeyField, IntegerField, Model, TextField

from .account import Account
from .category import Category
from .database import db


class Session(Model):
    id = TextField(primary_key=True)
    user_id = IntegerField(null=True)
    status = TextField(null=False, constraints=[Check("type IN ('pending', 'confirmed')")])
    created_at = DateTimeField(null=False)
    updated_at = DateTimeField(null=False, default=lambda: datetime.now(UTC))

    class Meta:
        database = db
        table_name = "sessions"
