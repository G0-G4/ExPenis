from playhouse.pwasyncio import AsyncSqliteDatabase

db = AsyncSqliteDatabase('./data/expenis.db', pragmas={'foreign_keys': 1})
