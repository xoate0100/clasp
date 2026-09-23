#!/usr/bin/env node
/** syntax check — ensure adapter scripts parse */
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const dir = path.dirname(fileURLToPath(import.meta.url));
const scriptsDir = path.join(dir, "..");
let failed = 0;
function walk(d) {
  for (const ent of fs.readdirSync(d, { withFileTypes: true })) {
    const p = path.join(d, ent.name);
    if (ent.isDirectory()) walk(p);
    else if (ent.name.endsWith(".mjs")) {
      const r = spawnSync(process.execPath, ["--check", p], { encoding: "utf8" });
      if (r.status !== 0) {
        console.error("[syntax] FAIL", p, r.stderr);
        failed++;
      }
    }
  }
}
walk(scriptsDir);
console.log(failed ? `[syntax] ${failed} failure(s)` : "[syntax] OK");
process.exit(failed ? 1 : 0);
