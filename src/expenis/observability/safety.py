import hashlib
import logging
import re
from contextvars import ContextVar
from pathlib import Path
from types import TracebackType

from starlette.types import Scope

request_id: ContextVar[str] = ContextVar("request_id", default="")
request_scope: ContextVar[Scope | None] = ContextVar("request_scope", default=None)
route_name: ContextVar[str] = ContextVar("route_name", default="unknown")

# These codes, never interpolated messages, form the logging interface.
EVENT_CODES = frozenset(
    {
        "application_event",
        "server_event",
        "dependency_event",
        "token_lifetime_invalid",
        "auth_rejected",
        "validation_rejected",
        "resource_not_found",
        "unhandled_error",
        "telemetry_config_invalid",
        "registered",
        "logged_in",
        "tokens_refreshed",
        "password_changed",
        "registration_rejected",
        "user_registered",
        "auth_unknown_user",
        "auth_bad_password",
        "telegram_user_created",
        "password_change_rejected",
        "unknown_currency",
        "account_created",
        "account_updated",
        "account_soft_deleted",
        "account_deleted",
        "category_created",
        "category_updated",
        "category_deleted",
        "default_categories_created",
        "transaction_saved",
        "transaction_updated",
        "transaction_deleted",
        "rates_persist_failed",
        "rates_fallback",
        "provider_transport_error",
        "provider_http_error",
        "provider_payload_error",
        "provider_rate_limited",
        "rates_fetched",
        "provider_quote_missing",
        "client_unhandled",
        "client_framework",
        "client_operation",
        "client_network",
        "client_http",
        "client_update",
        "client_version",
    }
)
CLIENT_CODES = frozenset(c for c in EVENT_CODES if c.startswith("client_"))
SYMBOL = re.compile(r"^[A-Za-z_$][A-Za-z0-9_.$<>/-]{0,159}$")
ROOT = Path(__file__).resolve().parents[1]


def log_unhandled_error(scope: Scope, exc: Exception) -> None:
    if scope.get("expenis.unhandled_logged"):
        return
    scope["expenis.unhandled_logged"] = True
    token = request_scope.set(scope)
    try:
        logging.getLogger("src.expenis.server.errors").error(
            "unhandled_error", exc_info=(type(exc), exc, exc.__traceback__)
        )
    finally:
        request_scope.reset(token)


def safe_frames(tb: TracebackType | None) -> list[dict[str, str | int]]:
    frames: list[dict[str, str | int]] = []
    while tb is not None and len(frames) < 30:
        try:
            file = str(Path(tb.tb_frame.f_code.co_filename).resolve().relative_to(ROOT))
        except ValueError:
            tb = tb.tb_next
            continue
        function = tb.tb_frame.f_code.co_name
        frames.append({"file": file, "function": function, "line": tb.tb_lineno})
        tb = tb.tb_next
    return frames


def fingerprint(code: str, frames: list[dict[str, str | int]]) -> str:
    # No exception message, locals, account values or device identity.
    return hashlib.sha256(repr((code, frames)).encode()).hexdigest()[:32]
