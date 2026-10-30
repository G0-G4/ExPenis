"""Root-only control for named disposable units/mounts; never production units."""

import json
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path("/var/lib/expenis-obs-acceptance-20261030")
PREP = Path("/var/tmp/expenis-obs-acceptance-20261030")
UNITS = ["guard", "backend", "collector", "tempo", "metrics", "logs"]
SLICES = ["expenisacceptance.slice", "expenisacceptanceaux.slice"]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def service(name, command, *, memory, core=False, environment=(), write=()):
    slice_name = SLICES[0 if core else 1]
    lines = [
        "[Unit]",
        "Description=Disposable ExPenis native acceptance " + name,
        "[Service]",
        "User=gog4",
        "Group=gog4",
        f"Slice={slice_name}",
        f"MemoryMax={memory}",
        f"WorkingDirectory={ROOT}/app",
        "ExecStart=" + command,
        "TimeoutStopSec=5",
        "RuntimeMaxSec=1800",
        "KillMode=control-group",
        "NoNewPrivileges=true",
        "ProtectSystem=strict",
        "ProtectHome=" + ("true" if name in ("tempo", "collector") else "read-only"),
        "PrivateTmp=true",
        "RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX",
        f"StandardOutput=append:{ROOT}/state/{name}.log",
        f"StandardError=append:{ROOT}/state/{name}.log",
    ]
    lines += ["Environment=" + item for item in environment]
    if name in ("tempo", "logs", "guard"):
        targets = (
            ["traces", "logs"]
            if name == "guard"
            else ["traces" if name == "tempo" else "logs"]
        )
        lines.insert(
            2,
            "RequiresMountsFor="
            + " ".join(str(ROOT / "data" / target) for target in targets),
        )
    lines += ["ReadWritePaths=" + str(path) for path in write]
    path = Path("/run/systemd/system") / f"expenis-acceptance-{name}.service"
    if path.exists():
        raise RuntimeError("Refusing to overwrite an existing unit: " + str(path))
    path.write_text("\n".join(lines) + "\n")


def prepare():
    assert os.geteuid() == 0
    for port in (28000, 28428, 29428, 24318, 24319, 23200, 29095, 27946, 8888):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", port))
    if ROOT.exists():
        raise RuntimeError("Acceptance root already exists; inspect it first")
    assert PREP.is_dir() and (PREP / "artifacts.json").is_file()
    PREP.rename(ROOT)
    for name in ("config", "state", "data"):
        (ROOT / name).mkdir(exist_ok=True)
    for name in ("traces", "logs"):
        image = ROOT / "data" / (name + ".ext4")
        target = ROOT / "data" / name
        target.mkdir()
        run("fallocate", "-l", "400000000", str(image))
        image.chmod(0o600)
        run("mkfs.ext4", "-q", "-m", "0", "-E", "nodiscard", "-F", str(image))
        run("mount", "-o", "loop,nosuid,nodev,noexec", str(image), str(target))
    for name, memory, cpu in [
        (SLICES[0], "1000000000", "50%"),
        (SLICES[1], "536870912", "25%"),
    ]:
        path = Path("/run/systemd/system") / name
        if path.exists():
            raise RuntimeError("Acceptance slice already exists")
        path.write_text(f"[Slice]\nMemoryMax={memory}\nCPUQuota={cpu}\n")
    config = ROOT / "config"
    source = ROOT / "app/deploy/monitoring/native"
    (ROOT / "data/baseline.json").write_text(
        json.dumps(
            {
                "metrics_bytes": 0,
                "venv_bytes": 0,
                "plugins_bytes": 0,
                "journal_bytes": 0,
            }
        )
    )
    collector = (
        (source / "collector.yml")
        .read_text()
        .replace("127.0.0.1:4318", "127.0.0.1:24318")
    )
    (config / "collector.yml").write_text(collector)
    tempo = (
        (source / "tempo.yml")
        .read_text()
        .replace("3200", "23200")
        .replace("4319", "24319")
    )
    tempo = tempo.replace(
        "/var/lib/expenis-observability/traces", str(ROOT / "data/traces")
    )
    tempo = tempo.replace(
        "grpc_listen_address: 127.0.0.1",
        "grpc_listen_address: 127.0.0.1\n  grpc_listen_port: 29095",
    )
    if "memberlist:" in tempo:
        tempo = tempo.replace("bind_port: 7946", "bind_port: 27946")
    else:
        tempo += "\nmemberlist:\n  bind_addr: [127.0.0.1]\n  bind_port: 27946\n"
    (config / "tempo.yml").write_text(tempo)
    (config / "metrics.yml").write_text(
        "scrape_configs:\n  - job_name: acceptance\n    scrape_interval: 5s\n    sample_limit: 5000\n    static_configs:\n      - targets: [127.0.0.1:28000]\n"
    )
    python = ROOT / "app/.venv/bin/python"
    service(
        "tempo",
        f"{ROOT}/bin/tempo -config.file={config}/tempo.yml",
        memory="640M",
        core=True,
        environment=["GOMEMLIMIT=512MiB"],
        write=[ROOT / "data/traces"],
    )
    service(
        "collector",
        f"{ROOT}/bin/otelcol-contrib --config={config}/collector.yml",
        memory="160M",
        core=True,
        environment=[
            "GOMEMLIMIT=112MiB",
            "VL_LOGS_ENDPOINT=http://127.0.0.1:29428/insert/opentelemetry/v1/logs",
            "TEMPO_TRACES_ENDPOINT=http://127.0.0.1:24319/v1/traces",
        ],
    )
    service(
        "logs",
        f"/usr/local/bin/victoria-logs -httpListenAddr=127.0.0.1:29428 -storageDataPath={ROOT}/data/logs -retentionPeriod=30d -retention.maxDiskSpaceUsageBytes=250MB",
        memory="128M",
        write=[ROOT / "data/logs"],
    )
    service(
        "metrics",
        f"/usr/local/bin/victoria-metrics -httpListenAddr=127.0.0.1:28428 -storageDataPath={ROOT}/state/metrics -retentionPeriod=3 -promscrape.config={config}/metrics.yml",
        memory="128M",
        write=[ROOT / "state"],
    )
    service(
        "backend",
        f"{python} {source}/backend.py",
        memory="192M",
        write=[ROOT / "state"],
    )
    service(
        "guard",
        f"{python} {source}/guard.py",
        memory="32M",
        core=True,
        write=[ROOT / "state"],
    )
    run("chown", "-R", "gog4:gog4", str(ROOT))
    run("systemctl", "daemon-reload")
    run(
        "systemd-analyze",
        "verify",
        *[f"/run/systemd/system/expenis-acceptance-{n}.service" for n in UNITS],
    )
    run(
        str(ROOT / "bin/otelcol-contrib"),
        "validate",
        "--config=" + str(config / "collector.yml"),
        env={
            **os.environ,
            "VL_LOGS_ENDPOINT": "http://127.0.0.1:29428/insert/opentelemetry/v1/logs",
            "TEMPO_TRACES_ENDPOINT": "http://127.0.0.1:24319/v1/traces",
        },
    )
    run(
        "systemctl",
        "start",
        *[
            f"expenis-acceptance-{n}.service"
            for n in ("logs", "metrics", "tempo", "collector", "backend", "guard")
        ],
    )
    print("Started only named acceptance units", flush=True)


def cleanup():
    assert os.geteuid() == 0
    for name in UNITS:
        subprocess.run(
            ["systemctl", "stop", f"expenis-acceptance-{name}.service"], check=False
        )
    for name in ("traces", "logs"):
        target = ROOT / "data" / name
        if os.path.ismount(target):
            run("umount", str(target))
    for name in UNITS:
        (Path("/run/systemd/system") / f"expenis-acceptance-{name}.service").unlink(
            missing_ok=True
        )
    for name in SLICES:
        subprocess.run(["systemctl", "stop", name], check=False)
        (Path("/run/systemd/system") / name).unlink(missing_ok=True)
    run("systemctl", "daemon-reload")
    subprocess.run(
        [
            "systemctl",
            "reset-failed",
            *[f"expenis-acceptance-{n}.service" for n in UNITS],
        ],
        check=False,
    )
    if "--remove-data" in sys.argv:
        assert ROOT.name == "expenis-obs-acceptance-20261030"
        assert not any(os.path.ismount(ROOT / "data" / n) for n in ("traces", "logs"))
        shutil.rmtree(ROOT)
    print("Acceptance units/mounts removed; production units untouched")


if __name__ == "__main__":
    {"prepare": prepare, "cleanup": cleanup}[sys.argv[1]]()
