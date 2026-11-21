from datetime import UTC, datetime

from peewee import DateTimeField, ForeignKeyField, Model, TextField

from .database import db
from .user import User


class UTCDateTimeField(DateTimeField):
    """SQLite stores naive UTC; callers always receive timezone-aware values."""

    def db_value(self, value: datetime | None) -> datetime | None:
        if value is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return super().db_value(value)

    def python_value(self, value: object) -> datetime | None:
        parsed = super().python_value(value)
        return parsed.replace(tzinfo=UTC) if parsed is not None else None


class PersonalGreeting(Model):
    user = ForeignKeyField(User, primary_key=True, on_delete="CASCADE")
    assignment_id = TextField(unique=True)
    text = TextField()
    expires_at = UTCDateTimeField(null=True)
    dismissed_at = UTCDateTimeField(null=True)
    created_at = UTCDateTimeField()

    class Meta:
        database = db
        table_name = "personal_greetings"
