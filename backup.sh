#!/bin/bash
cd "$(dirname "$0")"

LOG=backup-log.txt
# ~2–3 months of nightly runs (rclone --verbose is ~20–50 lines each).
MAX_LINES=4000
KEEP_LINES=3000

# Snap rclone cannot run from cron: "/system.slice/cron.service is not a snap cgroup".
RCLONE="${HOME}/.local/bin/rclone"
if [ ! -x "$RCLONE" ]; then
  RCLONE=/usr/local/bin/rclone
fi

{
  echo "=== $(date -Is) start pid=$$ user=$(id -un) pwd=$(pwd) ==="
  if ! source .venv/bin/activate; then
    echo "ERROR: failed to activate .venv"
    py_rc=1
    yandex_rc=skipped
    gdrive_rc=skipped
  else
    python3 src/expenis/core/backup.py
    py_rc=$?
    if [ "$py_rc" -eq 0 ]; then
      if [ ! -x "$RCLONE" ]; then
        echo "ERROR: rclone not found (expected ${HOME}/.local/bin/rclone)"
        yandex_rc=1
        gdrive_rc=1
      else
        echo "rclone=$RCLONE"
        # Each remote is synced independently so one being down doesn't block the other.
        "$RCLONE" sync data/backups/ yandex:backup/expenis --verbose
        yandex_rc=$?
        "$RCLONE" sync data/backups/ gdrive:backup/expenis --verbose
        gdrive_rc=$?
      fi
    else
      echo "ERROR: sqlite backup failed, skipping rclone"
      yandex_rc=skipped
      gdrive_rc=skipped
    fi
  fi
  echo "=== $(date -Is) done python=${py_rc} yandex=${yandex_rc} gdrive=${gdrive_rc} ==="
} >>"$LOG" 2>&1

if [ -f "$LOG" ]; then
  lines=$(wc -l <"$LOG")
  if [ "$lines" -gt "$MAX_LINES" ]; then
    tail -n "$KEEP_LINES" "$LOG" >"${LOG}.tmp" && mv "${LOG}.tmp" "$LOG"
  fi
fi

# Non-zero exit if the snapshot or any upload failed, so the failure isn't silent.
[ "$py_rc" = 0 ] && [ "$yandex_rc" = 0 ] && [ "$gdrive_rc" = 0 ]
