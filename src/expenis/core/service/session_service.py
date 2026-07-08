import logging
import uuid
from datetime import UTC, datetime, timedelta

from ..errors import NotFoundException
from ..models import db, Session

logger = logging.getLogger(__name__)

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
