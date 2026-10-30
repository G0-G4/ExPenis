import json
import logging
import logging.config
import os
import time
from pathlib import Path

from ..observability import runtime
from ..observability.safety import EVENT_CODES, safe_frames

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "expenis.log"


class SafeFormatter(logging.Formatter):
    """Build an allowlisted record without formatting arbitrary messages/arguments."""

    def format(self, record: logging.LogRecord) -> str:
        if not record.name.startswith(("src.expenis", "expenis", "uvicorn")):
            return json.dumps(
                {
                    "timestamp": time.time(),
                    "code": "dependency_event",
                    "severity": record.levelname.lower(),
                }
            )
        code = (
            record.msg
            if isinstance(record.msg, str) and record.msg in EVENT_CODES
            else ("server_event" if record.name.startswith("uvicorn") else "application_event")
        )
        frames = safe_frames(record.exc_info[2]) if record.exc_info else []
        # A record can reach two sinks; enqueue it once and reuse sanitized output.
        if not hasattr(record, "safe_output"):
            record.safe_output = runtime.telemetry.event(
                code,
                frames=frames,
                severity=min(21, max(5, (record.levelno // 10) * 4 + 1)),
            )
        return json.dumps(getattr(record, "safe_output"), ensure_ascii=False, separators=(",", ":"))


def setup_logging() -> dict:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        level = "INFO"
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {"safe": {"()": SafeFormatter}},
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": str(LOG_FILE),
                "maxBytes": 2_000_000,
                "backupCount": 2,
                "encoding": "utf-8",
                "formatter": "safe",
            },
            "console": {"class": "logging.StreamHandler", "formatter": "safe"},
        },
        "loggers": {
            "uvicorn": {"handlers": ["file", "console"], "level": level, "propagate": False},
            "uvicorn.error": {"handlers": ["file", "console"], "level": level, "propagate": False},
            "uvicorn.access": {"handlers": [], "level": "CRITICAL", "propagate": False},
            "httpx": {"handlers": [], "level": "CRITICAL", "propagate": False},
            "httpcore": {"handlers": [], "level": "CRITICAL", "propagate": False},
            "peewee": {"handlers": [], "level": "CRITICAL", "propagate": False},
        },
        "root": {"handlers": ["file", "console"], "level": level},
    }
    logging.config.dictConfig(config)
    return config
