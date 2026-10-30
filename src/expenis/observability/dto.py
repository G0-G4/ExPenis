from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


TraceId = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
SpanId = Annotated[str, Field(pattern=r"^[0-9a-f]{16}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Frame(StrictModel):
    file: str = Field(
        pattern=r"^(?:lib/[a-z0-9_/]+\.dart|main\.dart\.js)$", max_length=160
    )
    function: str = Field(pattern=r"^[A-Za-z_$][A-Za-z0-9_.$<>/-]{0,159}$")
    line: int = Field(ge=0, le=10_000_000)


class Record(StrictModel):
    event_id: UUID
    timestamp: datetime
    trace_id: TraceId | None = None
    span_id: SpanId | None = None
    request_id: Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")] | None = None

    @field_validator("timestamp")
    @classmethod
    def recent_timestamp(cls, value: datetime) -> datetime:
        now = datetime.now(UTC)
        if value.tzinfo is None or not now - timedelta(
            minutes=15
        ) <= value <= now + timedelta(minutes=5):
            raise ValueError("timestamp_out_of_range")
        return value

    @field_validator("trace_id", "span_id")
    @classmethod
    def nonzero_id(cls, value: str | None) -> str | None:
        if value is not None and int(value, 16) == 0:
            raise ValueError("invalid_id")
        return value

    @model_validator(mode="after")
    def bounded_record(self):
        if len(self.model_dump_json().encode()) > 8192:
            raise ValueError("record_too_large")
        return self


class ErrorRecord(Record):
    kind: Literal["error"]
    code: Literal[
        "client_unhandled",
        "client_framework",
        "client_operation",
        "client_network",
        "client_http",
        "client_update",
        "client_version",
    ]
    frames: list[Frame] = Field(default_factory=list, max_length=30)


class SpanLink(StrictModel):
    trace_id: TraceId
    span_id: SpanId

    @model_validator(mode="after")
    def valid_ids(self):
        if not int(self.trace_id, 16) or not int(self.span_id, 16):
            raise ValueError("invalid_link")
        return self


class SpanRecord(Record):
    kind: Literal["span"]
    trace_id: TraceId
    span_id: SpanId
    parent_span_id: SpanId | None = None
    links: list[SpanLink] = Field(default_factory=list, max_length=4)
    operation: Literal["api", "refresh", "update", "version"]
    start_ns: int = Field(gt=0)
    end_ns: int = Field(gt=0)
    status: int = Field(ge=0, le=599)
    outcome: Literal["ok", "error"]

    @model_validator(mode="after")
    def valid_duration(self):
        now = datetime.now(UTC).timestamp() * 1e9
        if (
            not self.start_ns <= self.end_ns
            or self.end_ns - self.start_ns > 15 * 60 * 1e9
        ):
            raise ValueError("invalid_duration")
        if self.start_ns < now - 15 * 60 * 1e9 or self.end_ns > now + 5 * 60 * 1e9:
            raise ValueError("invalid_span_time")
        if self.parent_span_id and (
            int(self.parent_span_id, 16) == 0 or self.parent_span_id == self.span_id
        ):
            raise ValueError("invalid_parent")
        return self


class TelemetryBatch(StrictModel):
    schema_version: Literal[1]
    platform: Literal["web", "android"]
    app_version: str = Field(
        pattern=r"^\d{1,5}\.\d{1,5}\.\d{1,5}(?:\+\d{1,10})?$", max_length=32
    )
    records: list[Annotated[ErrorRecord | SpanRecord, Field(discriminator="kind")]] = (
        Field(min_length=1, max_length=50)
    )


class TelemetryAcceptedResponse(StrictModel):
    accepted: int


class ReadinessResponse(StrictModel):
    status: Literal["ready", "not_ready"]
