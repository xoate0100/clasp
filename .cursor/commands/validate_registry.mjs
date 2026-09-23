#!/usr/bin/env node
/**
 * validate_registry.mjs — assert the /audit-* command suite is internally consistent.
 *
 * Zero-dependency (Node >=18). Run against the real suite:
 *   node .cursor/commands/validate_registry.mjs
 * Unit-tested via validate_registry.test.mjs (node --test).
 *
 * Checks:
 *   1. AUDIT_REGISTRY.yaml exists and parses at least one command.
 *   2. Support files (_skeleton.md, README.md) exist.
 *   3. Every registry command_file exists on disk.
 *   4. Every command file has YAML frontmatter whose `id` matches the registry id.
 *   5. No orphan audit-*.md file exists that isn't registered.
 *   6. audit-all's depends_on covers every other command id.
 *
 * Exit 0 = all pass; exit 1 = one or more failures.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

/**
 * Validate a `.cursor/commands` directory. Pure: returns results, does not exit.
 * @param {string} cmdDir absolute path to the commands dir
 * @returns {{problems: string[], passes: string[], count: number}}
 */
export function validateSuite(cmdDir) {
  const REGISTRY = path.join(cmdDir, "AUDIT_REGISTRY.yaml");
  const repoRel = (rel) => path.resolve(cmdDir, "..", "..", rel); // rel is repo-root-relative
  const problems = [];
  const passes = [];
  const fail = (m) => problems.push(m);
  const pass = (m) => passes.push(m);

  // 1. registry present
  if (!fs.existsSync(REGISTRY)) {
    fail(`AUDIT_REGISTRY.yaml not found (${REGISTRY})`);
    return { problems, passes, count: 0 };
  }
  const registryText = fs.readFileSync(REGISTRY, "utf8");

  // 2. support files
  for (const f of ["_skeleton.md", "README.md"]) {
    if (fs.existsSync(path.join(cmdDir, f))) pass(`support file present: ${f}`);
    else fail(`missing support file: ${f}`);
  }

  // 3. parse command entries (id + command_file) from the `commands:` block
  const entries = [];
  {
    let inCommands = false;
    let cur = null;
    for (const line of registryText.split(/\r?\n/)) {
      if (/^commands:\s*$/.test(line)) { inCommands = true; continue; }
      if (!inCommands) continue;
      const idM = line.match(/^\s*-\s*id:\s*(\S+)/);
      if (idM) { if (cur) entries.push(cur); cur = { id: idM[1], command_file: null }; continue; }
      const cfM = line.match(/^\s*command_file:\s*(\S+)/);
      if (cfM && cur && cur.command_file === null) cur.command_file = cfM[1];
    }
    if (cur) entries.push(cur);
  }
  if (entries.length === 0) fail("no command entries parsed from registry");
  else pass(`parsed ${entries.length} command entries`);

  // 4. each command_file exists + frontmatter id matches
  for (const e of entries) {
    if (!e.command_file) { fail(`entry '${e.id}' has no command_file`); continue; }
    const abs = repoRel(e.command_file);
    if (!fs.existsSync(abs)) { fail(`command_file missing for '${e.id}': ${e.command_file}`); continue; }
    const text = fs.readFileSync(abs, "utf8");
    const fm = text.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (!fm) { fail(`'${e.id}' has no YAML frontmatter: ${e.command_file}`); continue; }
    const fmId = fm[1].match(/^\s*id:\s*(\S+)/m);
    if (!fmId) fail(`'${e.id}' frontmatter missing id`);
    else if (fmId[1] !== e.id) fail(`'${e.id}': frontmatter id '${fmId[1]}' != registry id`);
    else pass(`command ok: ${e.id}`);
  }

  // 5. orphan check — every audit-*.md file must be registered
  const registered = new Set(entries.map((e) => e.command_file && path.basename(e.command_file)));
  for (const f of fs.readdirSync(cmdDir)) {
    if (/^audit-.*\.md$/.test(f) && !registered.has(f)) fail(`orphan command file not in registry: ${f}`);
  }

  // 6. audit-all depends_on coverage (read from its own frontmatter array)
  const allEntry = entries.find((e) => e.id === "audit-all");
  if (!allEntry || !allEntry.command_file) {
    fail("audit-all entry not found in registry");
  } else if (fs.existsSync(repoRel(allEntry.command_file))) {
    const allText = fs.readFileSync(repoRel(allEntry.command_file), "utf8");
    const dep = allText.match(/depends_on:\s*\[([^\]]*)\]/);
    const deps = dep ? dep[1].split(",").map((s) => s.trim()).filter(Boolean) : [];
    for (const e of entries) {
      if (e.id === "audit-all") continue;
      if (!deps.includes(e.id)) fail(`audit-all depends_on missing '${e.id}'`);
    }
    if (deps.length) pass(`audit-all depends_on lists ${deps.length} commands`);
  }

  return { problems, passes, count: entries.length };
}

// ---- CLI ----
const isMain = process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMain) {
  const cmdDir = path.dirname(fileURLToPath(import.meta.url));
  const { problems, passes, count } = validateSuite(cmdDir);
  for (const p of passes) console.log(`[audit-registry] PASS ${p}`);
  if (problems.length) {
    for (const p of problems) console.error(`[audit-registry] FAIL ${p}`);
    console.error(`[audit-registry] ${problems.length} problem(s) found`);
    process.exit(1);
  }
  console.log(`[audit-registry] OK — ${count} commands validated, no problems`);
  process.exit(0);
}
