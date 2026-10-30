import math
import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class TelemetrySettings:
    enabled: bool = False
    environment: str = "development"
    endpoint: str = "http://127.0.0.1:4318"
    sample_rate: float = 1.0
    queue_bytes: int = 8 * 1024 * 1024
    queue_records: int = 4096
    body_bytes: int = 65536
    source_per_minute: int = 30
    global_per_minute: int = 300
    source_burst: int = 5
    global_burst: int = 20
    cache_records: int = 10000
    timeout: float = 2.0
    paused_file: str = "/run/expenis-observability/paused"
    configuration_invalid: bool = False

    @classmethod
    def from_env(cls) -> "TelemetrySettings":
        try:
            return cls._validated_env()
        except ValueError:
            environment = os.getenv("EXPENIS_ENV", "development")
            if environment not in {"production", "development", "test"}:
                environment = "development"
            return cls(environment=environment, configuration_invalid=True)

    @classmethod
    def _validated_env(cls) -> "TelemetrySettings":
        environment = os.getenv("EXPENIS_ENV", "development")
        if environment not in {"production", "development", "test"}:
            environment = "development"
        endpoint = os.getenv("EXPENIS_OTLP_ENDPOINT", "http://127.0.0.1:4318").rstrip(
            "/"
        )
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "Telemetry exporter must use loopback HTTP without credentials"
            )
        # Validate malformed/out-of-range ports before starting a worker.
        _ = parsed.port
        sample_rate = float(os.getenv("EXPENIS_TRACE_SAMPLE_RATE", "1"))
        if not math.isfinite(sample_rate) or not 0 <= sample_rate <= 1:
            raise ValueError("Trace sampling rate must be between zero and one")
        return cls(
            enabled=os.getenv(
                "EXPENIS_TELEMETRY_ENABLED", str(environment == "production")
            ).lower()
            == "true",
            environment=environment,
            endpoint=endpoint,
            sample_rate=sample_rate,
            queue_bytes=min(
                8 * 1024 * 1024,
                max(1024, int(os.getenv("EXPENIS_TELEMETRY_QUEUE_BYTES", "8388608"))),
            ),
            source_per_minute=max(
                1, min(300, int(os.getenv("EXPENIS_TELEMETRY_SOURCE_RATE", "30")))
            ),
            global_per_minute=max(
                1, min(3000, int(os.getenv("EXPENIS_TELEMETRY_GLOBAL_RATE", "300")))
            ),
        )
