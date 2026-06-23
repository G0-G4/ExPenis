from datetime import UTC, datetime

from peewee import AutoField, BigIntegerField, DateTimeField, Model, TextField

from .database import db


class User(Model):
    id = AutoField(primary_key=True)
    username = TextField(null=True, unique=True)
    password_hash = TextField(null=True)
    telegram_id = BigIntegerField(null=True, unique=True)
    created_at = DateTimeField(null=False, default=lambda: datetime.now(UTC))
    updated_at = DateTimeField(null=True, default=lambda: datetime.now(UTC))

    class Meta:
        database = db
        table_name = "users"