# Production deployment

How this project is deployed and operated. Only ExPenis's own setup lives
here; the host itself (its address, other services on it, the shared reverse
proxy config, DNS) is documented in a separate private infra repo — update
that, not this file, when the box changes.

## Where

- Host: SSH alias `cloud` (user `gog4`). **Shared box** — other projects run
  there too, so be careful with anything system-wide (`ufw`, `docker`, the
  reverse proxy). Only one process can hold host ports 80/443, which is the
  whole reason for the reverse-proxy setup below.
- Repo root on the server: `/home/gog4/ExPenis` (same layout as this repo;
  `deploy.sh` runs from there).
- Public URL: `https://expenis.g0g4.ru`.

## Current setup: reverse proxy in front, this project's nginx still does its own TLS

`docker-compose.yml`'s `frontend` service publishes only
`127.0.0.1:18443:443` (not host 80/443 directly). A shared Caddy instance on
the box (not part of this repo) owns host 80/443 and reverse-proxies
`expenis.g0g4.ru` to that loopback port **over HTTPS, verifying the
certificate** (`tls_server_name expenis.g0g4.ru`). What this project needs
from it is exactly:

```
expenis.g0g4.ru → https://127.0.0.1:18443 (tls_server_name expenis.g0g4.ru)
```

This means TLS is terminated **twice**: once by Caddy at the edge (its own
Let's Encrypt cert), and again by this project's own `nginx` inside the
`frontend` container (`nginx/nginx.conf`, using the cert mounted from
`${SSL_VOLUME}` / `/etc/letsencrypt`). The backend (`expenis-server`, plain
`uv run`) listens on port `8000` on the host, and nginx reaches it via
`host.docker.internal:8000`.

**Why it's like this**: a quick, minimal-risk migration when the shared
reverse proxy was introduced — the goal was "free up 80/443 without touching
this project's nginx config or its cert setup", not a proper migration.

**Known problem**: the box's certbot can no longer renew the
`/etc/letsencrypt` cert this nginx serves — it was issued with the
`standalone` authenticator, which needs port 80, now owned by Caddy. Since
Caddy verifies the upstream cert, an expired cert there takes the site down
even though Caddy's own edge cert is fine. Either switch renewal to a
webroot/DNS challenge, or do the TODO below before the cert expires.

## TODO: fully switch to the reverse proxy

To remove the double TLS termination and let Caddy be the single owner of
certs for this domain:

1. Drop TLS from this project's own nginx: in `nginx/nginx.conf`, delete
   the `listen 443 ssl` server block's `ssl_certificate`/
   `ssl_certificate_key`/`ssl_dhparam`/`include options-ssl-nginx.conf`
   lines and change `listen 443 ssl` to a plain `listen 80` (merge into the
   existing HTTP server block, or just repurpose it — the container no
   longer needs to speak TLS to anyone, only to the loopback proxy hop).
2. Update `Dockerfile.frontend` / `docker-compose.yml`: drop the
   `${SSL_VOLUME}:/etc/nginx/ssl:ro` mount entirely, and change `ports:` to
   publish a loopback **HTTP** port instead, e.g. `"127.0.0.1:18080:80"`
   (check the infra repo for free ports first).
3. Change the reverse-proxy route (owned by the infra repo) to
   `expenis.g0g4.ru → 127.0.0.1:18080` (plain HTTP upstream).
4. Once confirmed working, the certbot-managed cert for `expenis.g0g4.ru`
   under `/etc/letsencrypt` is unused — safe to remove after checking nothing
   else reads it.
5. Update this doc once done.

## Redeploying

Still just `./deploy.sh` (or `just flutter-fetch-deploy`) from the repo
root on the server — see `AGENTS.md`'s "Deploy web from GitHub Release"
section. It rebuilds/restarts the `frontend` container using whatever
`docker-compose.yml` is currently checked out, which is why the port
mapping above is committed here rather than left as a one-off hand edit on
the box: a stale `80:80`/`443:443` in this file would silently break (or
refuse to start, fighting the reverse proxy for the port) on the next deploy.
