/**
 * validate_registry.test.mjs — unit tests for the audit-suite validator.
 * Run: node --test .cursor/commands/validate_registry.test.mjs
 * Zero-dependency (node:test + node:assert). Builds throwaway fixtures in tmp.
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { validateSuite } from "./validate_registry.mjs";

// Build a temp `.cursor/commands` dir from a { filename: content } map.
function makeFixture(files) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "audit-fix-"));
  const cmdDir = path.join(root, ".cursor", "commands");
  fs.mkdirSync(cmdDir, { recursive: true });
  for (const [name, content] of Object.entries(files)) {
    fs.writeFileSync(path.join(cmdDir, name), content, "utf8");
  }
  return cmdDir;
}

const REGISTRY_OK = `commands:
  - id: audit-foo
    command_file: .cursor/commands/audit-foo.md
  - id: audit-all
    command_file: .cursor/commands/audit-all.md
`;
const FOO = "---\nid: audit-foo\n---\nbody\n";
const ALL = "---\nid: audit-all\ndepends_on: [audit-foo]\n---\nbody\n";
const SKEL = "# skeleton\n";
const README = "# readme\n";
const BASE = { "AUDIT_REGISTRY.yaml": REGISTRY_OK, "_skeleton.md": SKEL, "README.md": README };

test("valid suite passes with no problems", () => {
  const dir = makeFixture({ ...BASE, "audit-foo.md": FOO, "audit-all.md": ALL });
  const { problems, count } = validateSuite(dir);
  assert.deepEqual(problems, [], "unexpected problems: " + problems.join("; "));
  assert.equal(count, 2);
});

test("missing command_file is caught", () => {
  const dir = makeFixture({ ...BASE, "audit-all.md": ALL }); // audit-foo.md omitted
  const { problems } = validateSuite(dir);
  assert.ok(problems.some((p) => /audit-foo/.test(p) && /missing/.test(p)),
    "expected a missing-file problem for audit-foo, got: " + problems.join("; "));
});

test("frontmatter id mismatch is caught", () => {
  const dir = makeFixture({ ...BASE, "audit-foo.md": "---\nid: audit-wrong\n---\nx\n", "audit-all.md": ALL });
  const { problems } = validateSuite(dir);
  assert.ok(problems.some((p) => /audit-foo/.test(p) && /id/.test(p)),
    "expected an id-mismatch problem, got: " + problems.join("; "));
});

test("orphan command file is caught", () => {
  const dir = makeFixture({
    ...BASE,
    "audit-foo.md": FOO,
    "audit-all.md": ALL,
    "audit-orphan.md": "---\nid: audit-orphan\n---\nx\n",
  });
  const { problems } = validateSuite(dir);
  assert.ok(problems.some((p) => /orphan/.test(p)),
    "expected an orphan problem, got: " + problems.join("; "));
});

test("missing support file is caught", () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "audit-fix-"));
  const cmdDir = path.join(root, ".cursor", "commands");
  fs.mkdirSync(cmdDir, { recursive: true });
  // registry + commands but no _skeleton.md / README.md
  fs.writeFileSync(path.join(cmdDir, "AUDIT_REGISTRY.yaml"), REGISTRY_OK);
  fs.writeFileSync(path.join(cmdDir, "audit-foo.md"), FOO);
  fs.writeFileSync(path.join(cmdDir, "audit-all.md"), ALL);
  const { problems } = validateSuite(cmdDir);
  assert.ok(problems.some((p) => /_skeleton\.md/.test(p)) && problems.some((p) => /README\.md/.test(p)),
    "expected missing-support-file problems, got: " + problems.join("; "));
});
