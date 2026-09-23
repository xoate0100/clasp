---
description: Runtime & execution safety preflight — loops, leaks, handles, races, buffers, disk/process blast radius
argument-hint: "[--fix] [--scope <path>]"
id: audit-runtime-safety
applies_to: [next, node, python, any]
modes: [discovery, fix]
output_dir: docs/audit/runtime-safety/
depends_on: []
related: [audit-observability, audit-optimization, audit-completeness]
---

# /audit-runtime-safety — runtime & execution safety preflight

Follow the shared flow in `_skeleton.md`. This is the "floss before it rots" pass:
find code that can hang, leak, corrupt, or take down the **dev machine** when an
agent runs tests and scripts — *before* it runs them. Static analysis here; the
runtime seatbelt is `agentic/exec_guard.py` (see Enforcement below).

## Inventory
Enumerate what actually executes: test suites and their runner config, scripts
(`scripts/`, `bin/`, npm/pnpm scripts, Makefile targets), watchers/dev servers,
background jobs, migration/seed/wipe scripts, and anything an agent might invoke.
Note which touch real data or external services.

## Checks (the hazard classes)

**Non-termination / runaway compute**
- infinite/unbounded loops (`while(true)` with no exit); unbounded or mutual
  recursion (stack overflow); accidental exponential algorithms; catastrophic
  regex backtracking (ReDoS); busy-wait/spin loops; retry with no cap/backoff;
  self-retriggering watcher/rebuild loops; tests with no per-test timeout.

**Memory**
- leaks from retained refs, accumulating listeners/subscriptions, closures over
  large objects; structures that only grow (caches, queues); loading huge
  files/datasets fully into memory vs streaming; `Promise.all` over huge inputs;
  accumulating results in a loop until OOM.

**Handles / descriptors / connections**
- unclosed files/streams (fd exhaustion); unclosed DB connections / pool
  exhaustion; leaked sockets / keep-alive agents; intervals/timers/watchers never
  disposed; temp files never cleaned up.

**Concurrency / correctness**
- races on shared mutable state; TOCTOU; deadlock/livelock from lock ordering;
  unsynchronized parallel writes to the same file/table; missing `await` /
  async-ordering assumptions; non-idempotent ops run concurrently; flaky tests
  rooted in any of these.

**Buffers / streams / I/O**
- buffer over/under-run and off-by-one on typed arrays (native/WASM interop);
  ignored stream backpressure (fast producer, slow consumer -> blowup);
  **undrained child-process stdout/stderr -> pipe deadlock/hang**; encoding
  mishandling; untrusted input into fixed buffers.

**Disk / filesystem**
- filling the disk with logs/temp/artifacts; recursive writes into a watched or
  source dir; destructive ops on the wrong path (`rm -rf`, unguarded globs,
  writes outside a sandbox); path traversal in generated paths; symlink loops.

**Process / OS blast radius (machine-killers)**
- fork bombs / unbounded subprocess spawn; builds/tests saturating all cores
  (`-j` unlimited); orphaned/zombie processes never reaped; signal mishandling
  killing the wrong PID; network floods that self-DDoS or trip rate limits/bans;
  running with admin rights against system paths.

**External-service side effects during runs**
- tests hitting **production** DB/services; real emails/SMS/charges via live
  integrations (ActiveCampaign, Gmail, payments) because calls weren't mocked;
  migration/seed/wipe pointed at real data; real API keys loaded in a test run.

**Security-of-execution**
- `eval`/dynamic exec of untrusted input; installing unpinned packages mid-run;
  `curl | bash`; secrets leaking into logs/artifacts a run produces.

**Determinism / observability**
- no timeouts or resource caps configured anywhere; no output/log size caps;
  non-deterministic tests (wall-clock, RNG, live network); no cleanup-on-failure;
  ignored exit codes hiding failures.

## Enforcement (pairs with this audit)
The audit finds hazards; `agentic/exec_guard.py` contains them at runtime. Runs
must go through it:
`python -m agentic.exec_guard --timeout <s> --max-memory-mb <mb> -- <command>`
(or `run_guarded(...)`). Harness `script` tools are guarded automatically. For
each finding, recommend the specific fix **and** the guard cap that would have
contained it.

## Evidence
File:line + hazard class + whether it's on an agent-invocable path (higher
priority). Confirmed = traced/reproduced; Suspected = static-only.
