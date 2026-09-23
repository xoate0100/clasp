#!/usr/bin/env node
/** health — verify node toolchain + adapter scripts exist */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { spawnSync } from "node:child_process";
import { REPO_ROOT, assertNoPythonRequired } from "../lib/feedback.mjs";

assertNoPythonRequired("health");

const required = [
  "adapters/node/stack_adapter.json",
  "adapters/node/scripts/init.mjs",
  "adapters/node/scripts/generate-context.mjs",
  "adapters/node/scripts/validate.mjs",
  "adapters/node/scripts/check-updates.mjs",
  "adapters/node/scripts/apply-updates.mjs",
  "adapters/node/scripts/submit-feedback.mjs",
  "adapters/node/scripts/health.mjs",
  "adapters/node/scripts/crosswalk.mjs",
];

let failed = 0;
for (const rel of required) {
  const p = path.join(REPO_ROOT, rel);
  if (!fs.existsSync(p)) {
    console.error("[node:health] missing", rel);
    failed++;
  }
}

const ver = spawnSync(process.execPath, ["--version"], { encoding: "utf8" });
console.log("[node:health] node", (ver.stdout || "").trim());

const major = Number((ver.stdout || "").replace(/^v/, "").split(".")[0]);
if (Number.isFinite(major) && major < 20) {
  console.error("[node:health] node >= 20 required");
  failed++;
}

console.log(failed ? `[node:health] FAIL (${failed})` : "[node:health] OK");
process.exit(failed ? 1 : 0);
