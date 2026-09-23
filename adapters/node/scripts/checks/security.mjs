#!/usr/bin/env node
/** security — reject obvious hardcoded secrets in adapter tree */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
const patterns = [
  /api[_-]?key\s*=\s*['"][A-Za-z0-9_\-]{16,}/i,
  /ghp_[A-Za-z0-9]{20,}/,
  /xox[baprs]-[A-Za-z0-9-]+/,
];
let failed = 0;
function walk(d) {
  for (const ent of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, ent.name);
    if (ent.isDirectory()) walk(p);
    else if (/\.(mjs|js|json|yml|yaml|md)$/.test(ent.name)) {
      const text = fs.readFileSync(p, "utf8");
      for (const re of patterns) {
        if (re.test(text)) {
          console.error("[security] possible secret:", p);
          failed++;
          break;
        }
      }
    }
  }
}
walk(root);
console.log(failed ? `[security] ${failed} failure(s)` : "[security] OK");
process.exit(failed ? 1 : 0);
