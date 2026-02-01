import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from ..errors import NotFoundException
from ..models import db, Session

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
    return session_id

async def confirm_session(user_id: int, session_id: str) -> Session:
    now = datetime.now(UTC)
    session = await db.run(lambda:
                     Session.get_or_none(Session.id == session_id))
    if session is None:
        raise NotFoundException(f"session {session_id} not found")
    session.status = 'confirmed'
    session.user_id = user_id
    session.updated_at = now
    await db.run(session.save)
    return session

async def get_session(session_id: str) -> Session:
    session = await db.run(lambda:
                           Session.get_or_none(Session.id == session_id))
    if session is None:
        raise NotFoundException(f"session {session_id} not found")
    return session

async def clear_old_sessions():
    now = datetime.now(UTC)
    old_time = now - timedelta(minutes=5)
    await db.run(lambda: Session.delete().where(Session.created_at <= old_time).execute())
