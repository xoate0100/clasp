#!/usr/bin/env node
/**
 * apply-updates — sync neutral protocol + adapters/node only (never python trees).
 * Dry-run by default unless --apply is passed (safety for hub dogfood).
 */
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import os from "node:os";
import { REPO_ROOT, readTemplateVersion, makeFeedbackEvent, appendFeedbackEvent } from "../lib/feedback.mjs";

const apply = process.argv.includes("--apply");
const forbidden = [
  "adapters/python",
  "3_bootstrap_scripts",
  "agent_platform",
];

const allowedPrefixes = [
  "1_global_standards/",
  "5_reference_architectures/",
  "7_schemas/",
  "adapters/node/",
  "8_ci/",
  ".cursor/commands/",
];

// Child-owned coordination state — never copy the hub fleet list onto spokes.
const skipExact = new Set([
  "5_reference_architectures/CHILD_REPOSITORY_REGISTRY.yaml",
]);

function hubUrl() {
  if (process.env.TEMPLATE_REPO) return process.env.TEMPLATE_REPO;
  const p = path.join(REPO_ROOT, "0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml");
  const text = fs.readFileSync(p, "utf8");
  const m = text.match(/template_repo:\s*"([^"]+)"/);
  return m ? m[1] : "https://github.com/xoate0100/project_initializer.git";
}

console.log(`[node:apply-updates] local=${readTemplateVersion()} apply=${apply}`);

if (!apply) {
  console.log("[node:apply-updates] dry-run only (pass --apply to copy). Listing allowed sync prefixes:");
  for (const p of allowedPrefixes) console.log("  -", p);
  console.log("[node:apply-updates] forbidden:", forbidden.join(", "));
  process.exit(0);
}

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "mf-node-update-"));
const clone = spawnSync("git", ["clone", "--depth", "1", hubUrl(), tmp], { encoding: "utf8" });
if (clone.status !== 0) {
  console.error("[node:apply-updates] clone failed", clone.stderr);
  process.exit(4);
}

function shouldCopy(rel) {
  const norm = rel.replace(/\\/g, "/");
  if (forbidden.some((f) => norm === f || norm.startsWith(f + "/"))) return false;
  if (skipExact.has(norm)) return false;
  return allowedPrefixes.some((p) => norm.startsWith(p));
}

function walkCopy(srcRoot, rel = "") {
  const abs = path.join(srcRoot, rel);
  for (const ent of fs.readdirSync(abs, { withFileTypes: true })) {
    const childRel = path.join(rel, ent.name).replace(/\\/g, "/");
    if (ent.isDirectory()) {
      if (forbidden.some((f) => childRel === f || childRel.startsWith(f + "/"))) continue;
      walkCopy(srcRoot, childRel);
    } else if (shouldCopy(childRel)) {
      const dest = path.join(REPO_ROOT, childRel);
      fs.mkdirSync(path.dirname(dest), { recursive: true });
      fs.copyFileSync(path.join(srcRoot, childRel), dest);
      console.log("[node:apply-updates] copied", childRel);
    }
  }
}

try {
  walkCopy(tmp);
  console.log("[node:apply-updates] OK");
} catch (err) {
  appendFeedbackEvent(
    makeFeedbackEvent({
      category: "UPDATE_ISSUE",
      title: "[Update] Node adapter apply-updates failed",
      body: String(err),
    }),
  );
  console.error(err);
  process.exit(1);
} finally {
  fs.rmSync(tmp, { recursive: true, force: true });
}
process.exit(0);
