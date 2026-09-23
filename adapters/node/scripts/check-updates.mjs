#!/usr/bin/env node
/** check-updates — compare local template_version to hub (git ls-remote tags). */
import { spawnSync } from "node:child_process";
import { readTemplateVersion, REPO_ROOT } from "../lib/feedback.mjs";
import fs from "node:fs";
import path from "node:path";

function hubUrl() {
  if (process.env.TEMPLATE_REPO) return process.env.TEMPLATE_REPO;
  const p = path.join(REPO_ROOT, "0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml");
  const text = fs.readFileSync(p, "utf8");
  const m = text.match(/template_repo:\s*"([^"]+)"/);
  return m ? m[1] : "https://github.com/xoate0100/project_initializer.git";
}

const local = readTemplateVersion();
const remote = hubUrl();
console.log(`[node:check-updates] local=${local}`);
console.log(`[node:check-updates] hub=${remote}`);

const r = spawnSync("git", ["ls-remote", "--tags", remote], { encoding: "utf8" });
if (r.status !== 0) {
  console.error("[node:check-updates] hub unreachable (exit 4)");
  console.error(r.stderr || r.stdout);
  process.exit(4);
}

const tags = (r.stdout || "")
  .split("\n")
  .map((l) => {
    const m = l.match(/refs\/tags\/(v?[\d.]+)/);
    return m ? m[1].replace(/^v/, "") : null;
  })
  .filter(Boolean);

const newest = tags.sort((a, b) => a.localeCompare(b, undefined, { numeric: true })).at(-1) || "unknown";
console.log(`[node:check-updates] newest_tag=${newest}`);
console.log(`[node:check-updates] update_available=${newest !== local && newest !== "unknown"}`);
process.exit(0);
