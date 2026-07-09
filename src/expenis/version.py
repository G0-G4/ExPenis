"""Version handling for the ExPenis backend.

The single source of truth for the backend version is the `version` field
in `pyproject.toml`.

For now we keep it manually in sync with `frontend/pubspec.yaml`
(version without the +build suffix).
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

_PACKAGE_NAME = "expenis"


def get_version() -> str:
    """Return the current package version.

    Priority:
    1. importlib.metadata (when the package is properly installed, e.g. in prod/Docker).
    2. Parse pyproject.toml relative to the source tree (development + generator scripts).
    """
    # 1. Try installed package metadata
    try:
        return version(_PACKAGE_NAME)
    except PackageNotFoundError:
        pass

    # 2. Fallback: parse pyproject.toml
    # This file lives at src/expenis/version.py → go up 2 levels to repo root.
    try:
        root = Path(__file__).resolve().parents[2]
        pyproject = root / "pyproject.toml"
        if pyproject.exists():
            content = pyproject.read_text(encoding="utf-8")
            match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if match:
                return match.group(1)
    except Exception:
        pass

    return "0.0.0"


__version__ = get_version()
