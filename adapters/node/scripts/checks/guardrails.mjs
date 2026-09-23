#!/usr/bin/env node
/** guardrails — require stack_adapter selection file */
import fs from "node:fs";
import path from "node:path";
import { REPO_ROOT } from "../../lib/feedback.mjs";

const sel = path.join(REPO_ROOT, "0_phase0_bootstrap/stack_adapter.yaml");
if (!fs.existsSync(sel)) {
  console.error("[guardrails] missing 0_phase0_bootstrap/stack_adapter.yaml");
  process.exit(1);
}
const text = fs.readFileSync(sel, "utf8");
if (!/adapter:\s*\w+/.test(text)) {
  console.error("[guardrails] stack_adapter.yaml missing adapter field");
  process.exit(1);
}
console.log("[guardrails] OK");
process.exit(0);
