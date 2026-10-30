"""Run the actual infra guard with paths mapped only to the disposable staging."""

import importlib.util
import time
from pathlib import Path

ROOT = Path("/var/lib/expenis-obs-acceptance-20261030")
SOURCE = ROOT / "app/deploy/monitoring/native/budget_guard.py"
spec = importlib.util.spec_from_file_location("native_budget_guard", SOURCE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)
guard.ROOT = ROOT / "data"
guard.FLAG = ROOT / "state/paused"
original_disk_bytes = guard.disk_bytes
MAPPING = {
    Path("/var/lib/victoria-metrics-data"): ROOT / "state/metrics",
    Path("/opt/expenis-observability"): ROOT / "bin",
    Path("/home/gog4/ExPenis/logs"): ROOT / "state/local-logs",
    Path("/home/gog4/ExPenis/.venv"): ROOT / "app/.venv",
    Path("/var/lib/grafana/plugins"): ROOT / "plugins",
    Path("/var/log/journal"): ROOT / "state/journal",
}
guard.disk_bytes = lambda path: original_disk_bytes(MAPPING.get(path, path))
while True:
    guard.main()
    time.sleep(2)
