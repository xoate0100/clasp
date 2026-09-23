#!/usr/bin/env node
/** submit-feedback — emit feedback_event.schema.json conforming entry (local log). */
import { makeFeedbackEvent, appendFeedbackEvent } from "../lib/feedback.mjs";

const args = process.argv.slice(2);
function flag(name, fallback = "") {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : fallback;
}

const category = flag("--category", "OPERATIONAL_ERROR");
const title = flag("--title", "[Node] feedback event");
const body = flag("--body", "Submitted via adapters/node/scripts/submit-feedback.mjs");

const event = makeFeedbackEvent({
  category,
  title,
  body,
  files: [],
  stack_coupling:
    category === "STACK_COUPLING" || category === "PORTABILITY"
      ? {
          assumed_runtime: flag("--assumed-runtime", "unknown"),
          affected_os: ["any"],
          lifecycle_verb: flag("--verb", ""),
          workaround: flag("--workaround", ""),
        }
      : undefined,
});

appendFeedbackEvent(event);
console.log("[node:submit-feedback] wrote event", event.event_id, event.category);
process.exit(0);
