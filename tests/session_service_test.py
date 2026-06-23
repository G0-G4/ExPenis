import pytest
from uuid import UUID
from datetime import datetime, UTC, timedelta
import time

from src.expenis.core.errors import NotFoundException
from src.expenis.core.models import db, Session, User
from src.expenis.core.service.session_service import create_session, confirm_session, get_session, clear_old_sessions


@pytest.mark.asyncio
async def test_create_session():
    async with db:
        # Test session creation
        session_id = await create_session()

        # Verify ID is valid UUID
        UUID(session_id)  # Will raise ValueError if not valid

        # Verify session exists in DB
        session = await db.run(lambda: Session.get_or_none(Session.id == session_id))
        assert session is not None
        assert session.status == 'pending'
        assert session.user_id is None

@pytest.mark.asyncio
async def test_confirm_session_links_telegram_id_to_user():
    async with db:
        session_id = await create_session()
        telegram_id = 123

        confirmed_session = await confirm_session(telegram_id, session_id)

        assert confirmed_session.status == 'confirmed'
        # session.user_id is now a users.id, not the raw telegram id
        assert confirmed_session.user_id is not None
        assert confirmed_session.user_id != telegram_id

        user = await db.run(lambda: User.get(User.id == confirmed_session.user_id))
        assert user.telegram_id == telegram_id

        # Verify in DB
        db_session = await db.run(lambda: Session.get(Session.id == session_id))
        assert db_session.status == 'confirmed'
        assert db_session.user_id == confirmed_session.user_id


@pytest.mark.asyncio
async def test_confirm_session_reuses_existing_telegram_user():
    async with db:
        # First confirm creates a user
        sid1 = await create_session()
        await confirm_session(456, sid1)
        user1 = await db.run(lambda: User.get(User.telegram_id == 456))

        # Second confirm with same telegram_id must reuse, not create a new user
        sid2 = await create_session()
        confirmed = await confirm_session(456, sid2)
        assert confirmed.user_id == user1.id

        users_count = await db.run(lambda: User.select().where(User.telegram_id == 456).count())
        assert users_count == 1


@pytest.mark.asyncio
async def test_confirm_nonexistent_session():
    async with db:
        # Try to confirm non-existent session
        with pytest.raises(NotFoundException, match="session nonexistent-session-id not found"):
            await confirm_session(123, "nonexistent-session-id")


@pytest.mark.asyncio
async def test_session_timestamps():
    async with db:
        # Create and confirm session to test timestamps
        session_id = await create_session()
        initial_session = await db.run(lambda: Session.get(Session.id == session_id))

        # Small delay to ensure timestamps would differ
        time.sleep(0.01)

        # Confirm session
        await confirm_session(123, session_id)
        updated_session = await db.run(lambda: Session.get(Session.id == session_id))

        # Verify updated_at changed
        assert updated_session.updated_at > initial_session.updated_at
        # Verify created_at didn't change
        assert updated_session.created_at == initial_session.created_at

@pytest.mark.asyncio
async def test_get_session():
    async with db:
        # Create test session
        session_id = await create_session()

        # Get the session
        session = await get_session(session_id)

        # Verify returned session matches
        assert session.id == session_id
        assert session.status == 'pending'

@pytest.mark.asyncio
async def test_get_nonexistent_session():
    async with db:
        # Try to get non-existent session
        with pytest.raises(NotFoundException, match="session nonexistent-session-id not found"):
            await get_session("nonexistent-session-id")

@pytest.mark.asyncio
async def test_clear_old_sessions():
    async with db:
        # Create old session (more than 5 minutes old)
        old_session_id = await create_session()
        old_session = await db.run(lambda: Session.get(Session.id == old_session_id))
        old_session.created_at = datetime.now(UTC) - timedelta(minutes=6)
        await db.run(old_session.save)

        # Create new session
        new_session_id = await create_session()

        # Clear old sessions
        await clear_old_sessions()

        # Verify old session was deleted
        old_session = await db.run(lambda: Session.get_or_none(Session.id == old_session_id))
        assert old_session is None

        # Verify new session still exists
        new_session = await db.run(lambda: Session.get_or_none(Session.id == new_session_id))
        assert new_session is not None
