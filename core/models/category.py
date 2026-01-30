from datetime import UTC, datetime

from peewee import AutoField, Check, DateTimeField, IntegerField, Model, TextField

from core.models.database import db


class Category(Model):
    id = AutoField(primary_key=True)
    user_id = IntegerField(null=False)
    type = TextField(constraints=[Check("type IN ('income', 'expense')")])
    name = TextField(null=False)
    created_at = DateTimeField(null=False, default=lambda: datetime.now(UTC))
    updated_at = DateTimeField(null=False, default=lambda: datetime.now(UTC))
    class Meta:
        database = db
        table_name = "categories"

