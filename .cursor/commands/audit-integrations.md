---
description: Third-party integration audit — ActiveCampaign, GA4, Google OAuth, Gmail/Calendar/Drive
argument-hint: "[--service <name>] [--fix]"
id: audit-integrations
applies_to: [next, node, any]
modes: [discovery, fix]
output_dir: docs/audit/integrations/
depends_on: []
related: [audit-security-nist, audit-observability]
---

# /audit-integrations — third-party integration audit

Follow the shared flow in `_skeleton.md`. Verifies each external integration is
wired, resilient, and correctly gated. Secret-storage findings hand to
`/audit-security-nist`.

## Inventory
List every integration and its touchpoints: **ActiveCampaign** (contact/notes
sync, automations, tags), **Google Analytics 4** (events, consent), **Google
OAuth** (via Supabase SSR), and Gmail/Calendar/Drive-backed automations (e.g. the
Waters Hardware attachment archiver Apps Script). For each: auth method, config
location, and the code paths that call it.

## Checks
- **Auth / token health** — tokens present, valid, refreshed; scopes minimal;
  OAuth redirect/callback correct; expiry handled without silent breakage.
- **Config presence** — required env vars set per environment (e.g.
  `NEXT_PUBLIC_GA_MEASUREMENT_ID` present where GA4 is expected).
- **Consent & gating** — GA4/analytics fires only after consent; privacy copy
  published; no PII leaked to analytics.
- **Webhooks & retries** — inbound/outbound webhooks verified (signature), with
  retry/idempotency; failures don't corrupt state.
- **Partial-failure handling** — if ActiveCampaign/GA/OAuth is down, the app
  degrades gracefully rather than blocking the user or losing data.
- **Rate limits & backoff** — respected; no unthrottled loops.
- **Event/schema drift** — the fields sent match what the remote expects
  (AC custom fields, GA4 event params); flag stale mappings.
- **Data sync integrity** — records that should sync (client notes → AC) actually
  do, once, without duplication.

## Evidence
Integration + call site + observed request/response (redacted) per finding.
