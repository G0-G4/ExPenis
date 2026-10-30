"""Prepare only the explicitly named, disposable cloud acceptance directory."""

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path("/var/tmp/expenis-obs-acceptance-20261030")
ARTIFACTS = [
    (
        "otelcol-contrib",
        "https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v0.140.0/otelcol-contrib_0.140.0_linux_amd64.tar.gz",
        "4bacc689cadffd5b4d468a6ac67c7c3cb4ff07000533fe1cb8f5d8b5d557ac79",
    ),
    (
        "tempo",
        "https://github.com/grafana/tempo/releases/download/v2.9.0/tempo_2.9.0_linux_amd64.tar.gz",
        "659b101d9fcea150ebb90b0c1ecacfb6229c1146430780885c639fa8fc6392f6",
    ),
]


def download(url, target, limit=150_000_000):
    request = urllib.request.Request(
        url, headers={"User-Agent": "ExPenis-isolated-acceptance"}
    )
    size = 0
    with (
        urllib.request.urlopen(request, timeout=60) as response,
        target.open("wb") as output,
    ):
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > limit:
                raise RuntimeError("Artifact exceeds installation budget")
            output.write(chunk)


def main():
    assert ROOT.is_dir() and not ROOT.is_symlink()
    (ROOT / "bin").mkdir(exist_ok=True)
    manifest = {}
    for name, url, expected in ARTIFACTS:
        target = ROOT / "bin" / name
        if target.exists():
            raise RuntimeError("Refusing to overwrite an existing acceptance binary")
        archive = ROOT / (name + ".tar.gz")
        download(url, archive)
        assert hashlib.file_digest(archive.open("rb"), "sha256").hexdigest() == expected
        with tarfile.open(archive) as bundle:
            member = next(
                m
                for m in bundle.getmembers()
                if Path(m.name).name == name and m.isfile()
            )
            with bundle.extractfile(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
        target.chmod(0o755)
        manifest[name] = {
            "archive_sha256": expected,
            "binary_bytes": target.stat().st_size,
        }
        archive.unlink()
        print("Verified and extracted", name, target.stat().st_size, flush=True)
    archive = ROOT / "plugin.zip"
    download(
        "https://grafana.com/api/plugins/victoriametrics-logs-datasource/versions/0.33.1/download?os=linux&arch=amd64",
        archive,
    )
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert any(Path(n).name == "MANIFEST.txt" for n in bundle.namelist())
        for member in bundle.infolist():
            target = (ROOT / "plugins" / member.filename).resolve()
            if not target.is_relative_to(ROOT / "plugins"):
                raise RuntimeError("Invalid plugin archive path")
        bundle.extractall(ROOT / "plugins")
    archive.unlink()
    print("Prepared isolated plugin files (not installed in Grafana)", flush=True)
    env = {
        **os.environ,
        "UV_CACHE_DIR": str(ROOT / "uv-cache"),
        "UV_PYTHON_DOWNLOADS": "never",
    }
    subprocess.run(
        ["uv", "sync", "--frozen", "--no-dev", "--no-cache", "--python", "3.13"],
        cwd=ROOT / "app",
        env=env,
        check=True,
    )
    shutil.rmtree(ROOT / "uv-cache", ignore_errors=True)
    (ROOT / "artifacts.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("Acceptance artifacts/dependencies prepared", flush=True)


if __name__ == "__main__":
    main()
