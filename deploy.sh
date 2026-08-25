#!/usr/bin/env bash
set -euo pipefail

# Web release deploy. Run from the ExPenis repo root on the server.
# No Flutter SDK needed: pulls the latest GitHub Release zip and rebuilds nginx.

cd "$(dirname "$0")"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

echo "Downloading ExPenis-web.zip..."
curl -fsSL -o "$tmp" \
  "https://github.com/G0-G4/ExPenis/releases/latest/download/ExPenis-web.zip"

echo "Unpacking into flutter_web/..."
rm -rf flutter_web
mkdir -p flutter_web
unzip -o "$tmp" -d flutter_web

echo "Rebuilding frontend container..."
if command -v docker-compose >/dev/null 2>&1; then
  docker-compose build frontend
  docker-compose up -d frontend
else
  docker compose build frontend
  docker compose up -d frontend
fi

echo "Deployment complete!"
