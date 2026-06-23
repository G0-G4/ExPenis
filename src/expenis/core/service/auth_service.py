import logging
from datetime import UTC, datetime

import bcrypt

from ..errors import NotFoundException
from ..models import User, db

logger = logging.getLogger(__name__)

# bcrypt truncates passwords at 72 bytes; long passwords are rejected rather
# than silently truncated to avoid surprising weak-prefix collisions.
_BCRYPT_MAX_PASSWORD_BYTES = 72


def _hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("password must be at most 72 bytes")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    encoded = password.encode("utf-8")
    if len(encoded) > _BCRYPT_MAX_PASSWORD_BYTES:
        return False
    return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))


class UsernameTakenError(Exception):
    pass


class InvalidPasswordError(Exception):
    pass


_PASSWORD_MIN_LENGTH = 6


def _validate_new_password(password: str) -> None:
    if len(password) < _PASSWORD_MIN_LENGTH:
        raise ValueError(f"password must be at least {_PASSWORD_MIN_LENGTH} characters")
    if len(password.encode("utf-8")) > _BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("password must be at most 72 bytes")


async def register_user(username: str, password: str) -> User:
    existing = await db.run(lambda: User.get_or_none(User.username == username))
    if existing is not None:
        logger.warning("registration rejected, username taken: %s", username)
        raise UsernameTakenError(f"username '{username}' is already taken")
    now = datetime.now(UTC)
    user = User(
        username=username,
        password_hash=_hash_password(password),
        telegram_id=None,
        created_at=now,
        updated_at=now,
    )
    await db.run(lambda: user.save(force_insert=True))
    logger.info("user registered: id=%d username=%s", user.id, username)
    return user


async def authenticate_user(username: str, password: str) -> User | None:
    user = await db.run(lambda: User.get_or_none(User.username == username))
    if user is None:
        logger.warning("auth failed, no such username: %s", username)
        return None
    if not _verify_password(password, user.password_hash):
        logger.warning("auth failed, bad password: username=%s", username)
        return None
    return user


async def get_or_create_user_by_telegram_id(telegram_id: int) -> User:
    user = await db.run(lambda: User.get_or_none(User.telegram_id == telegram_id))
    if user is not None:
        return user
    now = datetime.now(UTC)
    user = User(
        username=None,
        password_hash=None,
        telegram_id=telegram_id,
        created_at=now,
        updated_at=now,
    )
    await db.run(lambda: user.save(force_insert=True))
    logger.info("telegram-linked user created: id=%d telegram_id=%d", user.id, telegram_id)
    return user


async def get_user_by_id(user_id: int) -> User:
    user = await db.run(lambda: User.get_or_none(User.id == user_id))
    if user is None:
        raise NotFoundException(f"user {user_id} not found")
    return user


async def change_password(user_id: int, old_password: str, new_password: str) -> User:
    user = await get_user_by_id(user_id)
    if not _verify_password(old_password, user.password_hash):
        logger.warning("change_password rejected, bad old password: user_id=%d", user_id)
        raise InvalidPasswordError("invalid current password")
    _validate_new_password(new_password)
    user.password_hash = _hash_password(new_password)
    user.updated_at = datetime.now(UTC)
    await db.run(user.save)
    logger.info("password changed: user_id=%d", user_id)
    return user