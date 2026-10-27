#!/usr/bin/env bash
set -euo pipefail

# Web release deploy. Run from the ExPenis repo root on the server.
# No Flutter SDK needed: pulls the latest GitHub Release zip and publishes it
# into the directory the box's Caddy serves (see deploy/Caddyfile.snippet).

cd "$(dirname "$0")"

WEB_ROOT="${EXPENIS_WEB_ROOT:-/var/www/expenis}"

if [ ! -w "$WEB_ROOT" ]; then
  echo "$WEB_ROOT is missing or not writable; create it once with:" >&2
  echo "  sudo install -d -o $(id -un) -g $(id -gn) -m 755 $WEB_ROOT" >&2
  exit 1
fi

tmp_zip="$(mktemp)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_zip" "$tmp_dir"' EXIT

echo "Downloading ExPenis-web.zip..."
curl -fsSL -o "$tmp_zip" \
  "https://github.com/G0-G4/ExPenis/releases/latest/download/ExPenis-web.zip"

echo "Unpacking..."
unzip -q "$tmp_zip" -d "$tmp_dir"
if [ ! -f "$tmp_dir/index.html" ]; then
  echo "No index.html at the zip root, refusing to publish" >&2
  exit 1
fi

echo "Publishing into $WEB_ROOT..."
rsync -a --delete "$tmp_dir/" "$WEB_ROOT/"
chmod -R a+rX "$WEB_ROOT"

echo "Deployment complete!"
