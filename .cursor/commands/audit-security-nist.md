---
description: NIST-aligned application security review (CSF 2.0 / 800-53 / 800-63B / 800-218 / 800-30 + CVSS)
argument-hint: "[--fix] [--scope <route|path>]"
id: audit-security-nist
applies_to: [next, node, python, any]
modes: [discovery, fix]
output_dir: docs/audit/security/
depends_on: []
related: [audit-data, audit-dependencies, audit-observability, audit-integrations, audit-infra]
---

# /audit-security-nist — NIST-aligned security review

Follow the shared flow in `_skeleton.md`. Security uses its own scoring: rate each
finding with a **CVSS v4.0/3.1 vector** AND an **SP 800-30 likelihood × impact**
rating, adjusted for real deployment context; reconcile and prefer the
context-adjusted result for priority.

Governing standards: **CSF 2.0** (Govern/Identify/Protect/Detect/Respond/Recover),
**SP 800-53** control families, **SP 800-115** method (examine/interview/**test**),
**SP 800-63B** identity/AAL, **SP 800-218 SSDF** secure SDLC, **SP 800-30** risk.

## Rules of engagement (do first)
Confirm authorized scope, target env (**staging unless prod is authorized in
writing**), test accounts per role, and non-destructive constraint. Any live
secret/PII found = P0, redact value, record location only.

## Inventory (IDENTIFY)
Routes/APIs + auth requirement each; roles + trust boundaries; data inventory +
classification (public/internal/PII/secret/regulated); attack surface reachable
unauthenticated, per-role, and via direct API bypassing the UI.

## Checks (PROTECT/DETECT) — map each finding to control IDs + CWE
- **IA / 800-63B** — AAL enforced; credential storage; reset/recovery + account
  enumeration; MFA + bypass; brute-force/lockout; OAuth redirect/state/PKCE.
- **Session** — cookie flags (HttpOnly/Secure/SameSite); fixation; rotation on
  privilege change; idle/absolute timeout; server-side logout; expired/revoked
  token replay.
- **Authorization (highest yield)** — vertical escalation per role; horizontal
  **IDOR** on every object id via UI *and* direct API; server-side enforcement at
  API/domain layer not just UI; cross-user/tenant isolation at the query layer
  (Supabase RLS actually applied, not assumed).
- **API + input** — authn/authz/method per endpoint; injection (SQL/NoSQL/cmd/
  template/deserialization); mass assignment; boundary/length; rate limits.
- **File upload** — server-side content validation, size, path traversal, stored
  location executability, safe content-type on serve.
- **Crypto/data** — TLS+HSTS; at-rest protection; secure randomness; no homerolled.
- **Secrets/config/errors** — scan repo, client bundles, source maps, API
  responses, error output for keys/tokens; debug endpoints; stack/version leak;
  security headers (CSP, X-Content-Type-Options, frame-ancestors).
- **Logging/detect (AU)** — security events logged with context, without secrets/PII.
- **Business logic** — race/TOCTOU (double-spend, limit bypass); duplicate/replay;
  partial-success/dependency-failure integrity across layers.
- **Supply chain (SR/SSDF)** — deps vs NVD/CVE; lockfile + build integrity.

## Release gate
Do not declare security-ready while any P0/P1 is open, any auth/authz boundary is
untested (inferred ≠ tested), or any check area lacks a recorded method/result.
