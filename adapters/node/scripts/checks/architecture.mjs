#!/usr/bin/env node
/** architecture — node adapter must not invoke python tooling at runtime */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const self = fileURLToPath(import.meta.url);
const root = path.join(path.dirname(self), "..");
const banned = [
  /["']python3?["']/,
  /3_bootstrap_scripts\/[A-Za-z0-9_/.-]+\.py/,
];
let failed = 0;
function walk(d) {
  for (const ent of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, ent.name);
    if (ent.isDirectory()) walk(p);
    else if (ent.name.endsWith(".mjs") && path.resolve(p) !== path.resolve(self)) {
      const text = fs.readFileSync(p, "utf8");
      for (const re of banned) {
        if (re.test(text)) {
          console.error("[architecture] python coupling detected:", p);
          failed++;
          break;
        }
      }
    }
  }
}
walk(root);
console.log(failed ? `[architecture] ${failed} failure(s)` : "[architecture] OK");
process.exit(failed ? 1 : 0);
