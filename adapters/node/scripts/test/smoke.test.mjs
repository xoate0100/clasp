#!/usr/bin/env node
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");

test("node adapter manifest exists", () => {
  assert.ok(fs.existsSync(path.join(root, "adapters/node/stack_adapter.json")));
});

test("feedback schema exists", () => {
  assert.ok(fs.existsSync(path.join(root, "7_schemas/feedback_event.schema.json")));
});
