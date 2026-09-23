---
description: Infrastructure & deployment audit — Vercel, Google Cloud, Cloudflare, AWS; env/secrets, regions, DNS
argument-hint: "[--target <provider>] [--fix]"
id: audit-infra
applies_to: [next, node, any]
modes: [discovery, fix]
output_dir: docs/audit/infra/
depends_on: []
related: [audit-security-nist, audit-data]
---

# /audit-infra — infrastructure & deployment audit

Follow the shared flow in `_skeleton.md`. Reviews hosting, deployment, and
platform config. Secret-management findings hand to `/audit-security-nist`.

## Inventory
Providers and their roles: **Vercel** (Next hosting), **Google Cloud**
(GCS/CDN for media), **Cloudflare** (Workers back the GH/Parkville repo readers),
**AWS** where used. For each: what it hosts, config location (dashboard/IaC),
env/secret store, regions, and domains/DNS.

## Checks
- **Deploy config** — build settings, output/runtime target, Node version pinned;
  preview vs production parity; no broken/stale deploys.
- **Env & secrets** — required vars set per environment; no secrets in client
  bundles or committed config; server-only vars not `NEXT_PUBLIC_`; rotation path.
- **Regions / edge** — functions/db/CDN co-located sensibly; no cross-region
  latency traps; edge vs node runtime chosen correctly per route.
- **DNS / TLS** — records correct, TLS/HSTS enforced, no dangling subdomains,
  redirects (www/apex, http→https) correct.
- **CDN / caching** — cache rules and TTLs correct; no caching of authenticated
  or dynamic responses; purge path exists.
- **IaC drift** — if infra-as-code exists, deployed state matches it; if not,
  flag undocumented manual config as a risk.
- **Cost / rightsizing** — obvious overprovisioning, always-on when on-demand
  would do, unbounded function concurrency.
- **Resilience** — health checks, failover, and what happens when one provider
  (e.g. the CDN) is unavailable.

## Evidence
Provider + resource + config value/screenshot (redacted) per finding. Much of
this is `examine`/`interview` (dashboard access) — mark Suspected where not
directly verifiable.
