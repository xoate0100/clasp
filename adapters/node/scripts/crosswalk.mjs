#!/usr/bin/env node
/**
 * crosswalk — onboard / upgrade (COMMAND_INTERFACE §4.8).
 * Node governance path: must not invoke Python (assertNoPythonRequired).
 */
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { REPO_ROOT, assertNoPythonRequired } from "../lib/feedback.mjs";

assertNoPythonRequired("crosswalk");

const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const offline = args.includes("--offline");
const force = args.includes("--force");
const adapterIdx = args.indexOf("--adapter");
const adapterOverride = adapterIdx >= 0 ? args[adapterIdx + 1] : null;

const SEL = path.join(REPO_ROOT, "0_phase0_bootstrap/stack_adapter.yaml");
const VER = path.join(REPO_ROOT, "0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml");

function parseAdapterId() {
  if (!fs.existsSync(SEL)) return null;
  const text = fs.readFileSync(SEL, "utf8");
  const m = text.match(/^\s*adapter:\s*["']?([a-zA-Z0-9_-]+)/m);
  return m ? m[1] : null;
}

function manifestExists(id) {
  return fs.existsSync(path.join(REPO_ROOT, "adapters", id, "stack_adapter.json"));
}

function isOnboarded() {
  if (!fs.existsSync(SEL) || !fs.existsSync(VER)) return false;
  const id = parseAdapterId();
  return Boolean(id && manifestExists(id));
}

function writeSelection(adapterId) {
  const dir = path.dirname(SEL);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    SEL,
    `# Active stack adapter selection\nadapter: ${adapterId}\nmanifest: adapters/${adapterId}/stack_adapter.yaml\n`,
    "utf8",
  );
}

function ensureVersionStub() {
  if (fs.existsSync(VER)) return;
  fs.mkdirSync(path.dirname(VER), { recursive: true });
  fs.writeFileSync(
    VER,
    'template_version: "0.0.0"\ntemplate_repo: "https://github.com/xoate0100/project_initializer.git"\ninstalled_at: "1970-01-01T00:00:00Z"\nlast_updated_at: "1970-01-01T00:00:00Z"\nupdate_history: []\n',
    "utf8",
  );
}

function resolveTarget() {
  if (adapterOverride) return adapterOverride;
  const existing = parseAdapterId();
  if (existing && manifestExists(existing)) return existing;
  if (manifestExists("generic")) return "generic";
  if (manifestExists("node")) return "node";
  return "generic";
}

function hubReachable() {
  let url = process.env.TEMPLATE_REPO || "https://github.com/xoate0100/project_initializer.git";
  if (fs.existsSync(VER)) {
    const m = fs.readFileSync(VER, "utf8").match(/template_repo:\s*"([^"]+)"/);
    if (m) url = m[1];
  }
  const r = spawnSync("git", ["ls-remote", "--heads", url], { encoding: "utf8" });
  return r.status === 0;
}

if (isOnboarded() && !force) {
  console.log(`[crosswalk] already aligned (adapter=${parseAdapterId()}) — idempotent no-op`);
  process.exit(0);
}

let target = resolveTarget();
if (!manifestExists(target) && target !== "generic") {
  console.error(`[crosswalk] adapter '${target}' missing; falling back to generic`);
  target = "generic";
}
if (!manifestExists(target)) {
  console.error(`[crosswalk] FATAL: adapters/${target}/stack_adapter.json missing`);
  process.exit(3);
}

if (dryRun) {
  console.log(`[crosswalk] dry-run: would select adapter=${target}`);
  process.exit(0);
}

writeSelection(target);
ensureVersionStub();

if (!offline && !hubReachable()) {
  console.error("[crosswalk] hub unreachable (exit 4)");
  process.exit(4);
}

console.log(`[crosswalk] OK adapter=${target} (subsumed init+check-updates+apply-updates)`);
process.exit(0);
