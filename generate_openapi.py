#!/usr/bin/env python3
"""
Generate OpenAPI specification for ExPenis API.

The script imports the FastAPI app (no server start, no DB connection) and
writes docs/openapi.json.

All operationId, summary, description, tags etc. come from the route
decorators in src/expenis/server/application.py (see custom_openapi + explicit
operation_id / summary on each @app.xxx).

Run via: just openapi
"""
from __future__ import annotations

import json
from pathlib import Path

from src.expenis.server.application import app


def generate() -> Path:
    """Dump the OpenAPI spec.

    The version comes directly from the app (src.expenis.version),
    which reads pyproject.toml as the single source of truth.
    """
    output_dir = Path("docs")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "openapi.json"

    schema = app.openapi()

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return output_path


if __name__ == "__main__":
    out = generate()
    print(f"OpenAPI specification saved to {out}")
