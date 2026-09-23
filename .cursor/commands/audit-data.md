---
description: Database & storage audit — Supabase schema/migrations/RLS design, indexes, CDN/storage strategy
argument-hint: "[--scope <table|schema>] [--fix]"
id: audit-data
applies_to: [next, node]
modes: [discovery, fix]
output_dir: docs/audit/data/
depends_on: []
related: [audit-security-nist, audit-infra]
---

# /audit-data — database & storage audit

Follow the shared flow in `_skeleton.md`. Design/perf/integrity lens on data.
RLS *security* enforcement hands to `/audit-security-nist`; here RLS is reviewed
for correctness and performance. Supabase MCP available when connected.

## Inventory
Schemas/tables/columns and relationships; migrations (`supabase/migrations/`);
RLS policies; indexes; storage strategy (Supabase vs external — note SureWealth
media lives on **Google Cloud Storage + secure CDN**, not Supabase Storage); any
self-hosted db.

## Checks
- **Migration integrity** — migrations are ordered, reversible where feasible,
  and reflect the live schema; no drift between migrations and deployed db; no
  destructive migration without a guard.
- **RLS design** — policies exist for every table exposed to the client, are
  correct, and don't cause N+1 or full-scan performance cliffs.
- **Indexes & queries** — missing indexes on filtered/joined/ordered columns;
  N+1 access patterns; unbounded queries; missing pagination.
- **Constraints & integrity** — FKs, uniqueness, not-null, enums/check
  constraints; orphaned rows; data that violates intended invariants.
- **Storage strategy** — correct bucket/CDN routing; public vs signed access;
  cache headers/TTL on the CDN; no large blobs in Postgres that belong on CDN.
- **Backup / restore** — a restore path exists and is documented; PITR where
  warranted.
- **Data lifecycle** — soft vs hard delete consistency; retention; no orphaned
  storage objects after row deletion.

## Evidence
Table/policy/query + `explain`/measurement where possible per finding.
