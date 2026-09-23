#!/usr/bin/env node
/**
 * init — create minimal Node-child scaffold markers without Python.
 */
import fs from "node:fs";
import path from "node:path";
import { REPO_ROOT, ensureDir } from "../lib/feedback.mjs";

const markerDir = ensureDir("adapters/node/.runtime");
const marker = path.join(markerDir, "initialized.json");
const payload = {
  initialized_at: new Date().toISOString(),
  adapter: "node",
  note: "Node adapter init complete (reference implementation)",
};
fs.writeFileSync(marker, JSON.stringify(payload, null, 2) + "\n");

// Ensure stack selection points at node when running as a node child sample
const sel = path.join(REPO_ROOT, "0_phase0_bootstrap/stack_adapter.yaml");
if (process.env.META_FRAMEWORK_SET_ADAPTER === "node") {
  fs.writeFileSync(
    sel,
    "# Active stack adapter selection\nadapter: node\nmanifest: adapters/node/stack_adapter.yaml\n",
    "utf8",
  );
}

console.log("[node:init] OK — wrote", path.relative(REPO_ROOT, marker));
process.exit(0);
