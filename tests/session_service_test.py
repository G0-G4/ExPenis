import pytest
from uuid import UUID
from datetime import datetime, UTC
import time

from src.expenis.core.errors import NotFoundException
from src.expenis.core.models import db, Session
from src.expenis.core.service.session_service import create_session, confirm_session


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
async def test_confirm_session():
    async with db:
        # Create test session
        session_id = await create_session()
        test_user_id = 123
        
        # Confirm the session
        confirmed_session = await confirm_session(test_user_id, session_id)
        
        # Verify changes
        assert confirmed_session.status == 'confirmed'
        assert confirmed_session.user_id == test_user_id

        # Verify in DB
        db_session = await db.run(lambda: Session.get(Session.id == session_id))
        assert db_session.status == 'confirmed'
        assert db_session.user_id == test_user_id


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
