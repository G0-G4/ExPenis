import time

import pytest

from src.expenis.core.errors import NotFoundException
from src.expenis.core.models import User, db
from src.expenis.core.service import (
    authenticate_user,
    change_password,
    get_or_create_user_by_telegram_id,
    get_user_by_id,
    register_user,
)
from src.expenis.core.service.auth_service import InvalidPasswordError, UsernameTakenError


@pytest.mark.asyncio
async def test_register_user_creates_user_with_hashed_password():
    async with db:
        user = await register_user("alice", "s3cret-pw")

        assert user.id is not None
        assert user.username == "alice"
        assert user.telegram_id is None
        # password must not be stored in clear text
        assert user.password_hash is not None
        assert user.password_hash != "s3cret-pw"


@pytest.mark.asyncio
async def test_register_user_rejects_duplicate_username():
    async with db:
        await register_user("alice", "first-password")
        with pytest.raises(UsernameTakenError):
            await register_user("alice", "different-password")


@pytest.mark.asyncio
async def test_authenticate_user_happy_path():
    async with db:
        await register_user("bob", "the-builder")
        user = await authenticate_user("bob", "the-builder")
        assert user is not None
        assert user.username == "bob"


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password_returns_none():
    async with db:
        await register_user("bob", "the-builder")
        assert await authenticate_user("bob", "wrong-password") is None


@pytest.mark.asyncio
async def test_authenticate_user_missing_user_returns_none():
    async with db:
        assert await authenticate_user("nobody", "whatever") is None


@pytest.mark.asyncio
async def test_get_or_create_user_by_telegram_id_creates_then_reuses():
    async with db:
        created = await get_or_create_user_by_telegram_id(12345)
        assert created.id is not None
        assert created.telegram_id == 12345
        assert created.username is None
        assert created.password_hash is None

        again = await get_or_create_user_by_telegram_id(12345)
        assert again.id == created.id


@pytest.mark.asyncio
async def test_get_user_by_id_raises_when_missing():
    async with db:
        with pytest.raises(NotFoundException):
            await get_user_by_id(999999)


@pytest.mark.asyncio
async def test_registered_user_has_no_telegram_and_telegram_user_has_no_password():
    async with db:
        registered = await register_user("carol", "pw-12345")
        telegram = await get_or_create_user_by_telegram_id(987)

        assert registered.telegram_id is None
        assert registered.password_hash is not None
        assert telegram.username is None
        assert telegram.password_hash is None

        # ensure both stored
        assert await db.run(lambda: User.get_or_none(User.id == registered.id)) is not None
        assert await db.run(lambda: User.get_or_none(User.id == telegram.id)) is not None


@pytest.mark.asyncio
async def test_change_password_success():
    async with db:
        await register_user("dave", "old-pw-123")
        await change_password(1, "old-pw-123", "new-pw-456")

        assert await authenticate_user("dave", "new-pw-456") is not None
        assert await authenticate_user("dave", "old-pw-123") is None


@pytest.mark.asyncio
async def test_change_password_wrong_old_raises():
    async with db:
        await register_user("dave", "old-pw-123")
        with pytest.raises(InvalidPasswordError):
            await change_password(1, "wrong-old", "new-pw-456")
        # password must remain unchanged
        assert await authenticate_user("dave", "old-pw-123") is not None


@pytest.mark.asyncio
async def test_change_password_telegram_only_user_raises():
    async with db:
        tg_user = await get_or_create_user_by_telegram_id(424242)
        with pytest.raises(InvalidPasswordError):
            await change_password(tg_user.id, "anything", "new-pw-456")


@pytest.mark.asyncio
async def test_change_password_missing_user_raises():
    async with db:
        with pytest.raises(NotFoundException):
            await change_password(999999, "old-pw-123", "new-pw-456")


@pytest.mark.asyncio
async def test_change_password_too_short_raises():
    async with db:
        await register_user("dave", "old-pw-123")
        with pytest.raises(ValueError):
            await change_password(1, "old-pw-123", "short")


@pytest.mark.asyncio
async def test_change_password_updates_updated_at():
    async with db:
        await register_user("dave", "old-pw-123")
        before = await db.run(lambda: User.get(User.id == 1))
        assert before.updated_at is not None

        time.sleep(0.01)
        await change_password(1, "old-pw-123", "new-pw-456")
        after = await db.run(lambda: User.get(User.id == 1))

        assert after.updated_at > before.updated_at
        assert after.password_hash != before.password_hash