---
description: Logging, error handling & tracing audit — error boundaries, structured logs, no secrets in logs, silent failures
argument-hint: "[--scope <path>] [--fix]"
id: audit-observability
applies_to: [next, node, any]
modes: [discovery, fix]
output_dir: docs/audit/observability/
depends_on: []
related: [audit-integrations, audit-completeness]
---

# /audit-observability — logging, error handling & tracing

Follow the shared flow in `_skeleton.md`. Can be merged with `/audit-docs` into
`/audit-code-quality` if you prefer one code-health command.

## Inventory
Error boundaries (`error.tsx`/`global-error.tsx` per route segment), logging
call sites and their transport/levels, try/catch coverage on async paths, and any
tracing/monitoring hooks.

## Checks
- **Error boundary coverage** — every route segment and async surface has a
  fallback; no white-screen-on-throw; `global-error.tsx` present.
- **Silent failures** — swallowed catches (`catch {}`), unawaited promises,
  unhandled rejections, errors logged but not surfaced/handled.
- **Log structure** — consistent structured logging (levels, context/correlation
  id); not a scatter of `console.log`; server vs client logging separated.
- **No secrets/PII in logs** — tokens, credentials, full PII never logged
  (cross-ref `/audit-security-nist` AU controls).
- **Actionability** — logs carry enough context to debug (request id, user id
  where allowed, operation) without over-collecting.
- **Analytics vs logs** — GA4/product events are not a substitute for error logs;
  both exist and are distinct.
- **Alerting hooks** — a path exists for critical errors to reach someone
  (even if just a channel); partial-dependency failures are observable.

## Evidence
Call site + level + sample (redacted) per finding; note where a real error would
currently go unnoticed.
