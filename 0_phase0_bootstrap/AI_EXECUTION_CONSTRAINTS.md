# AI Execution Constraints (L2.5)
- Single agent (Cursor) may perform autonomous plan execution inside sandbox.
- Pre-commit and CI jobs are immutable enforcement gates.
- No edits to meta-framework, standards, schemas, or CI.
- All commits must satisfy: format, lint, type/static checks, security scan, arch rules, tests+coverage, doc sync, commit schema.
- Multi-component aware: per-component toolchains and thresholds.
