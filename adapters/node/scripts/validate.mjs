#!/usr/bin/env node
/** validate — run Node-side required checks (HOOK_CONTRACT subset). */
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { REPO_ROOT } from "../lib/feedback.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const testsOnly = process.argv.includes("--tests-only");

const checks = testsOnly
  ? [["tests", path.join(__dirname, "test/smoke.test.mjs"), true]]
  : [
      ["syntax", path.join(__dirname, "checks/syntax.mjs"), false],
      ["format", path.join(__dirname, "checks/format.mjs"), false],
      ["security", path.join(__dirname, "checks/security.mjs"), false],
      ["architecture", path.join(__dirname, "checks/architecture.mjs"), false],
      ["guardrails", path.join(__dirname, "checks/guardrails.mjs"), false],
      ["tests", path.join(__dirname, "test/smoke.test.mjs"), true],
    ];

let failed = 0;
for (const [id, script, isTest] of checks) {
  const args = isTest ? ["--test", script] : [script];
  const result = spawnSync(process.execPath, args, { cwd: REPO_ROOT, encoding: "utf8" });
  if (result.status !== 0) {
    console.error(`[node:validate] FAIL check=${id}`);
    if (result.stdout) process.stdout.write(result.stdout);
    if (result.stderr) process.stderr.write(result.stderr);
    failed += 1;
  } else {
    console.log(`[node:validate] PASS check=${id}`);
  }
}

process.exit(failed === 0 ? 0 : 1);
