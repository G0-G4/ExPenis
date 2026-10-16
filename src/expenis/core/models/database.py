import os

from playhouse.pwasyncio import AsyncSqliteDatabase

DEFAULT_DB_PATH = './data/expenis.db'

db = AsyncSqliteDatabase(
    os.getenv('EXPENIS_DB_PATH', DEFAULT_DB_PATH),
    pragmas={'foreign_keys': 1},
)
