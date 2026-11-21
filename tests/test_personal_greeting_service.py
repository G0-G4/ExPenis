from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from peewee import IntegrityError

from src.expenis.core.errors import NotFoundException
from src.expenis.core.models import PersonalGreeting, User, db
from src.expenis.core.service import personal_greeting_service as service


@pytest.fixture
async def users():
    async with db:
        return [await db.run(lambda: User.create(username=name)) for name in ("alice", "bob")]


@pytest.mark.asyncio
async def test_unique_recipient_and_assignment(users):
    async with db:
        await service.assign_greetings([users[0].id], "Hello")
        original = await service.inspect_greeting(users[0].id)
        with pytest.raises(IntegrityError):
            await db.run(lambda: PersonalGreeting.create(
                user=users[0].id, assignment_id=str(uuid4()), text="Duplicate",
                created_at=datetime.now(UTC),
            ))
        with pytest.raises(IntegrityError):
            await db.run(lambda: PersonalGreeting.create(
                user=users[1].id, assignment_id=original.assignment_id, text="Duplicate",
                created_at=datetime.now(UTC),
            ))


@pytest.mark.asyncio
async def test_lifecycle_and_user_isolation(users):
    a, b = [u.id for u in users]
    async with db:
        assert await service.get_active_greeting(a) is None
        text = "Поздравляю! 🎉\n" + "🎂" * 980
        await service.assign_greetings([a], text)
        first = await service.get_active_greeting(a)
        assert first.text == text
        assert first.created_at.tzinfo == UTC
        assert first.expires_at is None
        assert await service.get_active_greeting(b) is None
        await service.dismiss_greeting(b, first.assignment_id)
        assert await service.get_active_greeting(a) is not None
        await service.dismiss_greeting(a, first.assignment_id)
        dismissed = (await service.inspect_greeting(a)).dismissed_at
        await service.dismiss_greeting(a, first.assignment_id)
        assert (await service.inspect_greeting(a)).dismissed_at == dismissed
        assert await service.get_active_greeting(a) is None
        await service.assign_greetings([a], text)
        second = await service.get_active_greeting(a)
        assert second.assignment_id != first.assignment_id
        await service.dismiss_greeting(a, first.assignment_id)
        assert (await service.get_active_greeting(a)).assignment_id == second.assignment_id
        await service.delete_greetings([a])
        await service.delete_greetings([a])
        await service.assign_greetings([a], text)
        await service.dismiss_greeting(a, second.assignment_id)
        assert await service.get_active_greeting(a) is not None


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", " \n\t", "🎉" * 1001])
async def test_rejects_invalid_text_without_replacing(users, text):
    async with db:
        await service.assign_greetings([users[0].id], "Keep")
        with pytest.raises(ValueError):
            await service.assign_greetings([u.id for u in users], text)
        assert (await service.inspect_greeting(users[0].id)).text == "Keep"
        assert await service.inspect_greeting(users[1].id) is None
        await service.assign_greetings([users[0].id], "🎉" * 1000)
        assert len((await service.inspect_greeting(users[0].id)).text) == 1000


@pytest.mark.asyncio
async def test_moscow_expiration_boundary(users, monkeypatch):
    instant = datetime(2030, 12, 31, 20, 59, 59, tzinfo=UTC)
    class Clock:
        combine = staticmethod(datetime.combine)

        @classmethod
        def now(cls, tz=None):
            return instant.astimezone(tz)
    monkeypatch.setattr(service, "datetime", Clock)
    day = instant.astimezone(service.MOSCOW).date()
    async with db:
        await service.assign_greetings([users[0].id], "Today", day)
        item = await service.get_active_greeting(users[0].id)
        end = item.expires_at
        assert end.astimezone(service.MOSCOW).date() == day + timedelta(days=1)
        assert end.astimezone(service.MOSCOW).hour == 0
        with pytest.raises(ValueError):
            await service.assign_greetings([users[0].id], "Invalid", day - timedelta(days=1))
        for offset, active in [(-1, True), (0, False), (1, False)]:
            instant = end + timedelta(microseconds=offset)
            assert (await service.get_active_greeting(users[0].id) is not None) == active
        assert (await service.inspect_greeting(users[0].id)).text == "Today"


@pytest.mark.asyncio
async def test_selection_and_atomic_bulk_operations(users, monkeypatch):
    a, b = [u.id for u in users]
    async with db:
        selected = await service.select_greeting_recipients(all_users=True)
        late = await db.run(lambda: User.create(username="late"))
        assert [u.id for u in await service.select_greeting_recipients(username="alice")] == [a]
        assert [u.id for u in await service.select_greeting_recipients(user_id=b)] == [b]
        with pytest.raises(NotFoundException):
            await service.select_greeting_recipients(username="missing")
        with pytest.raises(ValueError):
            await service.select_greeting_recipients(user_id=a, all_users=True)
        await service.assign_greetings([a], "Old")
        await service.assign_greetings([b], "Closed")
        await service.dismiss_greeting(b, (await service.inspect_greeting(b)).assignment_id)
        await service.assign_greetings([u.id for u in selected], "All")
        assert (await service.get_active_greeting(a)).text == "All"
        assert (await service.get_active_greeting(b)).text == "All"
        assert await service.inspect_greeting(late.id) is None
        await service.assign_greetings([], "Empty")
        await service.delete_greetings([])
        with pytest.raises(NotFoundException):
            await service.assign_greetings([a, 999999], "Rollback")
        assert (await service.inspect_greeting(a)).text == "All"
        with pytest.raises(NotFoundException):
            await service.delete_greetings([a, 999999])
        assert await service.inspect_greeting(a) is not None
        original_uuid = service.uuid4
        calls = 0
        def fail_second_write():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise IntegrityError("simulated write failure")
            return original_uuid()
        monkeypatch.setattr(service, "uuid4", fail_second_write)
        with pytest.raises(IntegrityError):
            await service.assign_greetings([a, b], "Partial")
        assert (await service.inspect_greeting(a)).text == "All"
        assert (await service.inspect_greeting(b)).text == "All"
        await service.delete_greetings([a, b])
        assert await service.inspect_greeting(a) is None
