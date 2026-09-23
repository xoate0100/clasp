---
description: Sweep for incomplete / disconnected implementation — stubs, dead handlers, unwired UI/API/DB
argument-hint: "[--fix] [--scope <path>]"
id: audit-completeness
applies_to: [next, node, any]
modes: [discovery, fix]
output_dir: docs/audit/completeness/
depends_on: []
related: [audit-journey, audit-observability, audit-docs]
---

# /audit-completeness — incomplete / disconnected implementation sweep

Follow the shared flow in `_skeleton.md`. Goal: find work that *looks* done but
isn't wired end-to-end. Trace each layer boundary UI → API/server-action →
domain → storage → jobs → external service and flag every break.

## Inventory
List: interactive controls (buttons/forms/links) and their handlers; API routes /
server actions and their callers; Supabase tables/columns and their readers/writers;
background jobs and their triggers; feature flags and what they gate.

## Checks
- **Marker scan** — `TODO`, `FIXME`, `HACK`, `XXX`, `placeholder`, `mock`,
  `dummy`, `temporary`, `stub`, `WIP`, hardcoded/inline data that should be dynamic.
- **Dead controls** — buttons/links/forms with no handler, no-op `onClick`, or
  handlers that only `console.log`.
- **Unwired frontend** — UI features with no backend call; optimistic UI with no
  persistence; forms that never submit or discard their result.
- **Orphaned backend** — API routes / server actions the UI never calls; endpoints
  reachable but unreferenced.
- **Unused data** — Supabase columns/tables never read or never written; migrations
  for features that don't exist.
- **Missing states** — absent loading / empty / success / error states on async UI.
- **Missing error handling** — unguarded `await`, swallowed catches, no fallback.
- **Feature flags masking gaps** — flags permanently off hiding half-built work.
- **Duplicated/contradictory** — two implementations of the same thing that disagree.

## Evidence
For each: file:line of the gap, the layer boundary it breaks, and whether the
feature is user-reachable. Confirmed = you traced the break; Suspected = inferred
from static reference only.
