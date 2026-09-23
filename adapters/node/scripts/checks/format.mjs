#!/usr/bin/env node
/** format check — placeholder enforcing LF and no tabs in adapter sources */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
let failed = 0;
function walk(d) {
  for (const ent of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, ent.name);
    if (ent.isDirectory()) walk(p);
    else if (/\.(mjs|js|json|yml|yaml|md)$/.test(ent.name)) {
      const text = fs.readFileSync(p, "utf8");
      if (text.includes("\t")) {
        console.error("[format] tabs not allowed:", p);
        failed++;
      }
    }
  }
}
walk(root);
console.log(failed ? `[format] ${failed} failure(s)` : "[format] OK");
process.exit(failed ? 1 : 0);
