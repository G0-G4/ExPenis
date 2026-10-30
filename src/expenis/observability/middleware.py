import secrets
import time

from opentelemetry import context, trace
from opentelemetry.trace import SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import runtime
from .safety import log_unhandled_error, request_id, request_scope, route_name

EXCLUDED = {"/api/telemetry", "/api/health/ready", "/metrics"}
METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}


class ObservabilityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        owner = runtime.telemetry
        if (
            scope["type"] != "http"
            or scope["path"] in EXCLUDED
            or not owner.settings.enabled
        ):
            await self.app(scope, receive, send)
            return
        req_id = secrets.token_hex(16)
        token = request_id.set(req_id)
        scope_token = request_scope.set(scope)
        route_token = route_name.set("unknown")
        parent = None
        for key, value in scope.get("headers", []):
            if key.lower() == b"traceparent":
                extracted = TraceContextTextMapPropagator().extract(
                    {
                        "traceparent": value.decode("ascii", errors="replace"),
                    },
                    context=context.Context(),
                )
                if trace.get_current_span(extracted).get_span_context().is_valid:
                    parent = extracted
                break
        method = scope["method"] if scope["method"] in METHODS else "OTHER"
        status = 500
        started = False
        start = time.monotonic()
        owner.inflight.inc()
        with owner.tracer.start_as_current_span(
            "api",
            context=parent or context.Context(),
            kind=SpanKind.SERVER,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            span.set_attribute("request_id", req_id)

            async def tracked_send(message: Message) -> None:
                nonlocal status, started
                if message["type"] == "http.response.start":
                    started = True
                    status = message["status"]
                    message["headers"] = [
                        *message.get("headers", []),
                        (b"x-request-id", req_id.encode()),
                    ]
                await send(message)

            try:
                await self.app(scope, receive, tracked_send)
            except Exception as exc:
                span.set_status(trace.Status(trace.StatusCode.ERROR))
                log_unhandled_error(scope, exc)
                if started:
                    raise
                await JSONResponse(
                    {"detail": "Internal server error"}, status_code=500
                )(scope, receive, tracked_send)
            finally:
                route = getattr(scope.get("route"), "path", "unknown")
                route_name.set(route)
                span.update_name(f"{method} {route}")
                span.set_attributes(
                    {"route": route, "method": method, "status": status}
                )
                if status >= 500:
                    span.set_status(trace.Status(trace.StatusCode.ERROR))
                owner.requests.labels(
                    owner.settings.environment, route, method, f"{status // 100}xx"
                ).inc()
                owner.latency.labels(owner.settings.environment, route, method).observe(
                    time.monotonic() - start
                )
                owner.inflight.dec()
                request_id.reset(token)
                request_scope.reset(scope_token)
                route_name.reset(route_token)
