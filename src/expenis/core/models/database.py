import os
from contextvars import copy_context
from collections.abc import Callable, Sequence
from typing import ParamSpec, TypeVar

from playhouse.pwasyncio import AsyncSqliteDatabase, CursorAdapter

from ...observability.runtime import operation

DEFAULT_DB_PATH = "./data/expenis.db"
P = ParamSpec("P")
T = TypeVar("T")


class ObservedSqliteDatabase(AsyncSqliteDatabase):
    async def run(self, fn: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
        # pwasyncio creates a greenlet; explicitly carry request context into it.
        ctx = copy_context()
        return await super().run(ctx.run, fn, *args, **kwargs)

    def execute_sql(self, sql: str, params: Sequence[object] | None = None) -> CursorAdapter:
        command = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
        kind = (
            "read"
            if command == "SELECT"
            else "write"
            if command in {"INSERT", "UPDATE", "DELETE"}
            else "other"
        )
        with operation(f"sqlite.{kind}"):
            return super().execute_sql(sql, params)


db = ObservedSqliteDatabase(
    os.getenv("EXPENIS_DB_PATH", DEFAULT_DB_PATH),
    pragmas={"foreign_keys": 1},
)
