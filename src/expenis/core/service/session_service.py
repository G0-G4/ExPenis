import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from ..errors import NotFoundException
from ..models import db, Session
from .auth_service import get_or_create_user_by_telegram_id

logger = logging.getLogger(__name__)

SessionStatus = Literal['pending', 'confirmed']

async def create_session() -> str:
    now = datetime.now(UTC)
    session_id = str(uuid.uuid4())
    session = Session(
        id=session_id,
        status='pending',
        created_at=now,
        updated_at=now
    )
    await db.run(lambda: session.save(force_insert=True))
    logger.info("session created: %s", session_id)
    return session_id

async def confirm_session(telegram_id: int, session_id: str) -> Session:
    now = datetime.now(UTC)
    session = await db.run(lambda:
                     Session.get_or_none(Session.id == session_id))
    if session is None:
        logger.warning("session not found for confirmation: %s", session_id)
        raise NotFoundException(f"session {session_id} not found")
    user = await get_or_create_user_by_telegram_id(telegram_id)
    session.status = 'confirmed'
    session.user_id = user.id
    session.updated_at = now
    await db.run(session.save)
    logger.info("session confirmed: %s user_id=%d (telegram_id=%d)", session_id, user.id, telegram_id)
    return session

async def get_session(session_id: str) -> Session:
    session = await db.run(lambda:
                           Session.get_or_none(Session.id == session_id))
    if session is None:
        logger.warning("session not found: %s", session_id)
        raise NotFoundException(f"session {session_id} not found")
    return session

async def clear_old_sessions():
    now = datetime.now(UTC)
    old_time = now - timedelta(minutes=5)
    deleted = await db.run(lambda: Session.delete().where(Session.created_at <= old_time).execute())
    logger.info("cleared %d old sessions", deleted)
