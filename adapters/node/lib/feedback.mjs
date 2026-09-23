import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID } from "node:crypto";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
export const REPO_ROOT = path.resolve(__dirname, "../../..");

export function readJson(rel) {
  const p = path.join(REPO_ROOT, rel);
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

export function ensureDir(rel) {
  const p = path.join(REPO_ROOT, rel);
  fs.mkdirSync(p, { recursive: true });
  return p;
}

export function appendFeedbackEvent(event) {
  const logRel = "6_ai_runtime_context/ai_feedback_log.json";
  const logPath = path.join(REPO_ROOT, logRel);
  ensureDir("6_ai_runtime_context");
  let doc = { entries: [] };
  if (fs.existsSync(logPath)) {
    try {
      const raw = JSON.parse(fs.readFileSync(logPath, "utf8"));
      if (Array.isArray(raw)) doc = { entries: raw };
      else if (raw && Array.isArray(raw.entries)) doc = raw;
      else if (raw && Array.isArray(raw.events)) doc = { entries: raw.events };
    } catch {
      doc = { entries: [] };
    }
  }
  doc.entries.push(event);
  fs.writeFileSync(logPath, JSON.stringify(doc, null, 2) + "\n", "utf8");
  return event;
}

export function makeFeedbackEvent({ category, title, body, component, files, stack_coupling }) {
  const event = {
    event_id: randomUUID(),
    schema_version: "1.0.0",
    timestamp: new Date().toISOString(),
    category,
    title,
    body,
    component: component || "meta-framework",
    files: files || [],
    severity: "medium",
    requires_human_intervention: category === "STACK_COUPLING",
    source: {
      adapter_id: "node",
      emitter: "adapters/node/lib/feedback.mjs",
      template_version: readTemplateVersion(),
    },
  };
  if (stack_coupling) event.stack_coupling = stack_coupling;
  return event;
}

export function readTemplateVersion() {
  const p = path.join(REPO_ROOT, "0_phase0_bootstrap/META_FRAMEWORK_VERSION.yaml");
  if (!fs.existsSync(p)) return "unknown";
  const m = fs.readFileSync(p, "utf8").match(/template_version:\s*"?([^"\n]+)"?/);
  return m ? m[1].trim() : "unknown";
}

export function assertNoPythonRequired(label) {
  // Soft check used by health — documents intent; CI Phase 6 hard-asserts PATH.
  if (process.env.META_FRAMEWORK_REQUIRE_NO_PYTHON === "1") {
    const pathEnv = process.env.PATH || "";
    // Heuristic only; Phase 6 uses a scrubbed PATH.
    if (/\bpython(\.exe)?\b/i.test(pathEnv) && process.env.META_FRAMEWORK_PYTHON_SCRUBBED !== "1") {
      console.warn(`[node-adapter] WARN (${label}): PYTHON may be on PATH; set META_FRAMEWORK_PYTHON_SCRUBBED=1 in conformance tests`);
    }
  }
}
