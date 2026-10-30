"""Backend entrypoint for the disposable native acceptance installation only."""

import asyncio
import os
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path("/var/lib/expenis-obs-acceptance-20261030")
sys.path.insert(0, str(ROOT / "app"))
DB = ROOT / "state/database.sqlite"
DB.parent.mkdir(exist_ok=True)
fresh = not DB.exists()
if fresh:
    with sqlite3.connect(DB) as connection:
        for migration in sorted((ROOT / "app/migrations").glob("*.sql")):
            connection.executescript(migration.read_text())
os.environ.update(
    {
        "EXPENIS_DB_PATH": str(DB),
        "EXPENIS_ENV": "test",
        "EXPENIS_TELEMETRY_ENABLED": "true",
        "EXPENIS_OTLP_ENDPOINT": "http://127.0.0.1:24318",
        "EXPENIS_TELEMETRY_SOURCE_RATE": "300",
        "EXPENIS_TELEMETRY_GLOBAL_RATE": "3000",
        "secret": "synthetic-native-acceptance-secret-never-production",
        "expiration_time_seconds": "3600",
        "refresh_time_seconds": "7200",
    }
)

from src.expenis.core import logging_config
from src.expenis.core.models import db
from src.expenis.core.service import register_user
from src.expenis.observability import runtime
from src.expenis.observability.runtime import operation
from src.expenis.server.application import app
import uvicorn

logging_config.LOG_DIR = ROOT / "state/local-logs"
logging_config.LOG_FILE = logging_config.LOG_DIR / "technical.log"
runtime.telemetry.settings = replace(
    runtime.telemetry.settings, paused_file=str(ROOT / "state/paused")
)
original_execute = db.execute_sql


def faultable_execute(sql, params=None):
    if (ROOT / "state/db-unavailable").exists():
        with operation("sqlite.read"):
            raise RuntimeError("synthetic native acceptance fault")
    return original_execute(sql, params)


db.execute_sql = faultable_execute


async def seed():
    async with db:
        await register_user("native-acceptance", "synthetic-testpass123")
    await db.close_pool()


if fresh:
    asyncio.run(seed())
uvicorn.run(
    app, host="127.0.0.1", port=28000, log_config=logging_config.setup_logging()
)
