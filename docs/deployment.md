# Production deployment

How this project is deployed and operated. Only ExPenis's own setup lives
here; the host itself (its address, other services on it, the rest of the
shared Caddyfile, DNS) is documented in a separate private infra repo —
update that, not this file, when the box changes.

## Where

- Host: SSH alias `cloud` (user `gog4`). **Shared box** — other projects run
  there too, so be careful with anything system-wide (`ufw`, the shared
  Caddy).
- Repo checkout on the server: `/home/gog4/ExPenis` (backend code, `.env`,
  `deploy.sh`, backups).
- Web bundle served from: `/var/www/expenis` (owned by `gog4`).
- Public URL: `https://expenis.g0g4.ru`.

## How it's wired

```
client ─HTTPS─► Caddy (box, ports 80/443, its own Let's Encrypt cert)
                 ├─ /api/*  → reverse_proxy 127.0.0.1:8000 → expenis-server (systemd, uv)
                 └─ else    → file_server /var/www/expenis (Flutter web, SPA fallback to index.html)
```

- **Caddy site block**: `deploy/Caddyfile.snippet` is the source of truth —
  copy it into the box's `/etc/caddy/Caddyfile`, then
  `sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy`.
  It also carries the cache rules (entry points `no-cache`, hashed assets
  immutable) and security headers that nginx used to set.
- **Backend**: systemd unit `expenis-server` runs `uv run -m src.expenis.server`
  from the checkout with `EXPENIS_ENV=production`, which binds `127.0.0.1:8000`
  (only Caddy can reach it). Without `EXPENIS_ENV=production` it binds
  `0.0.0.0` for LAN debugging.
- **TLS**: only Caddy. There is no project-owned certificate, nginx or docker
  anymore.

## Deploying

- Web (after a GitHub Release is published): `./deploy.sh` (or
  `just flutter-fetch-deploy`) from the checkout. It downloads
  `ExPenis-web.zip` and rsyncs it into `/var/www/expenis`; Caddy serves the
  new files immediately, no restart.
- Backend: `git pull`, `uv sync`, `sudo systemctl restart expenis-server`.
- One-time setup on a new box: `sudo install -d -o gog4 -g gog4 -m 755 /var/www/expenis`,
  add the Caddy block, install the systemd unit.
