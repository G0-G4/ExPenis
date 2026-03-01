from datetime import UTC, datetime
from functools import wraps
from typing import Any


class Ttl:
    def __init__(self, ttl_seconds: int):
        self._creation_time = datetime.now(UTC)
        self._ttl_seconds = ttl_seconds

    @property
    def creation_time(self):
        return self._creation_time

    @property
    def ttl_seconds(self):
        return self._ttl_seconds


class Cache:
    _cache: dict[str, tuple[Any, Ttl]] = dict()

    def _reset_if_needed(self, key: str):
        if self._key_expired(key):
            del self._cache[key]

    def _key_expired(self, key):
        if key in self._cache:
            value, ttl = self._cache[key]
            if ttl.ttl_seconds is None:
                return False
            return (datetime.now(UTC) - ttl.creation_time).total_seconds() >= ttl.ttl_seconds
        return False

    def cached(self, ttl_seconds: int | None = None):
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
                key = ":".join(key_parts)

                self._reset_if_needed(key)

                if key in self._cache:
                    value, ttl = self._cache[key]
                    return value

                result = await func(*args, **kwargs)
                self._cache[key] = (result, Ttl(ttl_seconds))
                return result

            return wrapper

        return decorator
