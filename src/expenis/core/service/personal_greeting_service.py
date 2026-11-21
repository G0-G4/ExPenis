from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from ..errors import NotFoundException
from ..models import PersonalGreeting, User, db

MOSCOW = ZoneInfo("Europe/Moscow")


def validate_greeting(text: str, expires_on: date | None) -> datetime | None:
    if not text.strip() or len(text) > 1000:
        raise ValueError("Text must contain 1–1000 Unicode characters.")
    if expires_on is None:
        return None
    if expires_on < datetime.now(MOSCOW).date():
        raise ValueError("Expiration date must not be before today in Moscow.")
    try:
        return datetime.combine(expires_on + timedelta(days=1), time(), MOSCOW).astimezone(UTC)
    except OverflowError as exc:
        raise ValueError("Expiration date is out of range.") from exc


async def select_greeting_recipients(
    *, user_id: int | None = None, username: str | None = None, all_users: bool = False,
) -> list[User]:
    if sum((user_id is not None, username is not None, all_users)) != 1:
        raise ValueError("Select exactly one of user ID, username or all users.")
    query = User.select().order_by(User.id)
    if not all_users:
        query = query.where(User.id == user_id if user_id is not None else User.username == username)
    users = await db.list(query)
    if not all_users and not users:
        raise NotFoundException("User not found.")
    return users


async def inspect_greeting(user_id: int) -> PersonalGreeting | None:
    return await db.run(lambda: PersonalGreeting.get_or_none(PersonalGreeting.user == user_id))


async def assign_greetings(
    user_ids: list[int], text: str, expires_on: date | None = None,
) -> None:
    expires_at = validate_greeting(text, expires_on)
    async with db.atomic():
        for user_id in user_ids:
            if not await db.run(lambda: User.select().where(User.id == user_id).exists()):
                raise NotFoundException("A selected user no longer exists. Select recipients again.")
            values = {
                "assignment_id": str(uuid4()), "text": text, "expires_at": expires_at,
                "dismissed_at": None, "created_at": datetime.now(UTC),
            }
            await db.run(lambda: PersonalGreeting.insert(user=user_id, **values).on_conflict(
                conflict_target=[PersonalGreeting.user], update=values,
            ).execute())


async def delete_greetings(user_ids: list[int]) -> None:
    async with db.atomic():
        for user_id in user_ids:
            if not await db.run(lambda: User.select().where(User.id == user_id).exists()):
                raise NotFoundException("A selected user no longer exists. Select recipients again.")
            await db.run(lambda: PersonalGreeting.delete().where(
                PersonalGreeting.user == user_id,
            ).execute())


async def get_active_greeting(user_id: int) -> PersonalGreeting | None:
    now = datetime.now(UTC)
    return await db.run(lambda: PersonalGreeting.get_or_none(
        (PersonalGreeting.user == user_id)
        & PersonalGreeting.dismissed_at.is_null()
        & (PersonalGreeting.expires_at.is_null() | (PersonalGreeting.expires_at > now))
    ))


async def dismiss_greeting(user_id: int, assignment_id: str) -> None:
    await db.run(lambda: PersonalGreeting.update(dismissed_at=datetime.now(UTC)).where(
        (PersonalGreeting.user == user_id)
        & (PersonalGreeting.assignment_id == assignment_id)
        & PersonalGreeting.dismissed_at.is_null()
    ).execute())
