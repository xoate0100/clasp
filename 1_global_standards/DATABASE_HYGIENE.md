# DATABASE_HYGIENE Standard

Status: Required for any schema or migration work.

## Purpose

Define minimum done criteria for database changes so agents and humans do not ship schema drift, unsafe migrations, or non-reproducible production state.

## Core Rules

1. Migrations are mandatory for schema changes.
2. Every migration includes both upgrade and downgrade paths.
3. Never edit an already-applied migration; create a new revision.
4. Never stamp over a physically divergent shared database without an explicit reconciliation plan.
5. Use migration-safe connection settings (direct/session mode as required by provider), not pooled runtime settings that break DDL.

## SOLID Mapping for Schema Work

- SRP: one logical concern per migration.
- OCP: prefer additive expand → migrate data → contract patterns.
- LSP: maintain a single migration head or explicitly merge branches.
- ISP: keep domain logic independent of vendor console workflows.
- DIP: application code depends on repository/session abstractions, not hard-coded engine URLs.

## Operations

- Secrets must come from env/secret manager only.
- Set explicit timeouts and bounded pools.
- Use ephemeral local DB in CI where possible.
- Log migration success/failure events without logging credentials.

## Caching

- Cache read projections and metadata only.
- Database remains source of truth.
- Invalidate related cache keys/tags after migration apply.

## Security

- Use least-privilege roles (application role distinct from migration owner when practical).
- Enforce TLS for managed connections.
- Use parameterized queries.
- Never store secrets or PII in migration scripts or fixtures.

## Data Modeling Defaults

- 3NF as default for operational entities.
- Denormalize only with documented tradeoff and freshness owner.
- Prefer UUID primary keys and timestamptz timestamps.
- Enforce uniqueness at database level for idempotency keys.

## Template Enforcement Expectations

- This document is part of template standards.
- Projects should add migration validation into pre-commit/CI gates.
- Agent guardrails should block schema edits without migrations.
