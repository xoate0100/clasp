/**
 * Node capability adapter (Wave B/C) — vendor + executing conformance.
 */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

import { runSuite } from './conformance_runner.mjs';

export function treeIntegrity(dir) {
  const hash = crypto.createHash('sha256');
  const walk = (d) => {
    for (const ent of fs.readdirSync(d, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      const p = path.join(d, ent.name);
      if (ent.isDirectory()) walk(p);
      else {
        hash.update(path.relative(dir, p).split(path.sep).join('/'));
        hash.update(fs.readFileSync(p));
      }
    }
  };
  walk(dir);
  return 'sha256-' + hash.digest('hex');
}

export function vendorCapability(registryRoot, capabilityId, dest) {
  const src = path.join(registryRoot, 'capabilities', capabilityId);
  fs.rmSync(dest, { recursive: true, force: true });
  fs.cpSync(src, dest, { recursive: true });
  const desc = JSON.parse(fs.readFileSync(path.join(dest, 'descriptor.json'), 'utf8'));
  return {
    capability_id: capabilityId,
    git_tag: `capability/${capabilityId}/v${desc.version}`,
    integrity: treeIntegrity(dest),
    vendored_path: dest,
  };
}

export async function runConformanceSuite(vendoredDir, impl) {
  const suite = JSON.parse(fs.readFileSync(path.join(vendoredDir, 'conformance', 'suite.json'), 'utf8'));
  const asyncImpl = {
    run: (input) => Promise.resolve(impl.run(input)),
  };
  // runSuite is sync — unwrap async provider
  const cases = [];
  for (const caseDef of suite.cases || []) {
    const result = await asyncImpl.run(caseDef.input || {});
    const { runCase } = await import('./conformance_runner.mjs');
    cases.push(runCase({ run: () => result }, caseDef));
  }
  return {
    suite_id: suite.suite_id,
    passed: cases.length > 0 && cases.every((c) => c.passed),
    failed_ids: cases.filter((c) => !c.passed).map((c) => c.case_id),
    cases,
  };
}

export async function loadSurewealthProvider(broken = false) {
  const mod = await import('./providers/surewealth_content_generate.mjs');
  return broken ? mod.BrokenProvider : mod.Provider;
}

export async function offlineConformanceNode(vendoredDir, { broken = false, surewealthRoot } = {}) {
  if (surewealthRoot) process.env.SUREWEALTH_ROOT = surewealthRoot;
  const impl = await loadSurewealthProvider(broken);
  return runConformanceSuite(vendoredDir, impl);
}

/** Legacy: shell to Python for content.publish */
export function offlineConformanceViaPython(hubRoot, vendoredDir, implModule = 'content_publish') {
  const script = `
from pathlib import Path
import json, sys
sys.path.insert(0, r${JSON.stringify(hubRoot)})
from backend.capability_adapter.conformance_runner import ContentPublishImpl, BrokenContentPublishImpl, run_suite
suite = json.loads(Path(r${JSON.stringify(path.join(vendoredDir, 'conformance', 'suite.json'))}).read_text(encoding='utf-8'))
impl = BrokenContentPublishImpl() if ${JSON.stringify(implModule)} == 'broken' else ContentPublishImpl()
r = run_suite(impl, suite)
print(json.dumps({"passed": r.passed, "failed": r.failed_ids}))
`;
  const out = execFileSync('python', ['-c', script], { encoding: 'utf8' });
  return JSON.parse(out.trim().split('\n').pop());
}
