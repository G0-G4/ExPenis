from playhouse.pwasyncio import AsyncSqliteDatabase

db = AsyncSqliteDatabase('./expenis.db', pragmas={'foreign_keys': 1})

