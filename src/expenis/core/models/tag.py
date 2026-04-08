from datetime import UTC, datetime

from peewee import AutoField, DateTimeField, IntegerField, Model, TextField

from .database import db


class Tag(Model):
    id = AutoField(primary_key=True)
    user_id = IntegerField(null=False)
    name = TextField(null=False)
    created_at = DateTimeField(null=False)
    updated_at = DateTimeField(null=False, default=lambda: datetime.now(UTC))

    class Meta:
        database = db
        table_name = "tags"
        indexes = ((('user_id', 'name'), True),)
