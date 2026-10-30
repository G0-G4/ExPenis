# Disposable native acceptance

These are helpers for an explicitly authorized cloud acceptance run, not production
startup or release CI. They use fixed run ID `20261030`, separate ports/units and
synthetic data. Inspect them and choose a fresh consistent ID before a later run.

Lifecycle used for this acceptance:

1. Check capacity, service health and free ports. Create a new, empty
   `/var/tmp/expenis-obs-acceptance-20261030/app`; refuse an existing stage.
2. Transfer only current `src/`, `migrations/`, `pyproject.toml`, `uv.lock`,
   `README.md` and these helpers. Never copy `.env`, real SQLite or signing keys.
3. Run `install.py` using existing Python 3.13 and the unprivileged deployment
   user. Downloads are pinned; dependencies/uv cache and plugin files are isolated.
4. Copy the private infra `collector.yml`, `tempo.yml` and `budget_guard.py` into
   the staged helper directory. Infra remains their source of truth.
5. Run `control.py prepare` as root. It moves execution into a separate `/var/lib`
   root (compatible with PrivateTmp), creates only new fixed-size images and
   runtime units, validates and starts them. Zero baselines count full copied
   venv/plugin sizes, conservatively exceeding their production incremental cost.
6. Run `check.py` in a bounded transient unit: User/Group gog4, auxiliary slice,
   MemoryMax 128M, CPUQuota 25%, RuntimeMaxSec 600. It checks workload/compaction,
   retention, quotas and continuously probes production health and host reserves.
   `--resume` continues retained blocks; preserve the interrupted report.
7. Run `recover.py` as root. It stops the test trace writer before clearing only
   its WAL/blocks, validates unchanged synthetic SQLite, storage/DB/Collector
   recovery, final aggregate guard and a fresh correlated trace/log.
8. Save only `artifacts.json`, `state/*report*.json`, `unit-validation.txt` and
   `unit-properties.txt`; then run `control.py cleanup --remove-data` as root.
   Check test listeners/loop devices are gone and production still responds.

Core: Tempo 640M, Collector 160M, guard 32M in a 1,000,000,000-byte slice.
Auxiliary backend/logs/metrics/generator have a separate capped slice. Ports:
28000 backend; 24318 Collector; 23200/24319/29095/27946 Tempo; 29428 logs;
28428 metrics; 8888 Collector internal metrics — all loopback-only.

ENOSPC is deliberate: a diagnostic writer may exit; recovery frees only the test
pressure file, restarts that writer and checks an already flushed event survived.
This bounded profile is not an arbitrary-throughput guarantee or multi-day soak.
Production provisioning, real databases, backups and shared stores are untouched.
