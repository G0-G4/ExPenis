"""Explicitly isolated UI test server. Never points at the development database."""

import asyncio
import json
import os
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
STATE = Path("/private/tmp/expenis-observability-e2e")
STATE.mkdir(exist_ok=True)
DB = STATE / "database.sqlite"
fresh = not DB.exists()
if not fresh and "--reuse" not in sys.argv:
    raise RuntimeError("Test database exists; --reuse is only for restarting this owned lab")
if fresh:
    with sqlite3.connect(DB) as connection:
        for migration in sorted((ROOT / "migrations").glob("*.sql")):
            connection.executescript(migration.read_text())
os.environ.update(
    {
        "EXPENIS_DB_PATH": str(DB),
        "EXPENIS_ENV": "test",
        "EXPENIS_TELEMETRY_ENABLED": "true",
        "EXPENIS_OTLP_ENDPOINT": "http://127.0.0.1:14318",
        "secret": "synthetic-e2e-signing-key-not-production-12345",
        "expiration_time_seconds": "3",
        "refresh_time_seconds": "3600",
    }
)
from src.expenis.core import logging_config
from src.expenis.core.models import db
from src.expenis.core.service import register_user
from src.expenis.observability import runtime
from src.expenis.observability.runtime import operation
from src.expenis.server.application import app
import uvicorn

logging_config.LOG_DIR = STATE / "logs"
logging_config.LOG_FILE = logging_config.LOG_DIR / "technical.log"
runtime.telemetry.settings = replace(runtime.telemetry.settings, paused_file=str(STATE / "paused"))
original_execute = db.execute_sql


def faultable_execute(sql, params=None):
    if (STATE / "database-unavailable").exists():
        with operation("sqlite.read"):
            raise RuntimeError("synthetic database outage")
    return original_execute(sql, params)


db.execute_sql = faultable_execute


async def seed():
    async with db:
        await register_user("telemetrye2e", "testpass123")
    await db.close_pool()


if fresh:
    asyncio.run(seed())
(STATE / "context.json").write_text(
    json.dumps(
        {"username": "telemetrye2e", "password": "testpass123", "api": "http://127.0.0.1:18000"}
    )
)
uvicorn.run(app, host="127.0.0.1", port=18000, log_config=logging_config.setup_logging())
