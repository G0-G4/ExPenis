from datetime import UTC, datetime

from peewee import AutoField, DateTimeField, FloatField, IntegerField, Model, TextField

from .database import db


class Account(Model):
    id = AutoField(primary_key=True)
    user_id = IntegerField(null=False)
    name = TextField(null=False)
    adjustment_amount = FloatField(null=False, default=0.0)
    created_at = DateTimeField(null=False)
    updated_at = DateTimeField(null=False, default=lambda: datetime.now(UTC))
    class Meta:
        database = db
        table_name = "accounts"
