/**
 * SureWealth Node content.generate provider — loads real generator from provider repo.
 * Set SUREWEALTH_ROOT to surewealth-education-platform checkout (fixture-only, no API).
 */
import fs from 'node:fs';
import path from 'node:path';
import { pathToFileURL } from 'node:url';

function surewealthRoot() {
  const root = process.env.SUREWEALTH_ROOT || path.resolve(process.cwd(), '..', 'surewealth-education-platform');
  if (!fs.existsSync(root)) {
    throw new Error(`SUREWEALTH_ROOT not found: ${root}`);
  }
  return root;
}

async function loadModules() {
  const root = surewealthRoot();
  const fixture = await import(
    pathToFileURL(path.join(root, 'scripts/course-generation/lib/generator/fixture-package.mjs')).href
  );
  const mo = await import(
    pathToFileURL(path.join(root, 'scripts/course-generation/lib/mo-rules.mjs')).href
  );
  return { synthesizeFixturePackage: fixture.synthesizeFixturePackage, MO_GROUNDING: mo.MO_GROUNDING };
}

let _mods;
async function mods() {
  if (!_mods) _mods = await loadModules();
  return _mods;
}

export const Provider = {
  async run(caseInput) {
    const seed = caseInput.seed || caseInput.topic || '';
    if (!String(seed).trim()) {
      return { outcome: 'reject', error_code: 'SEED_REQUIRED' };
    }
    const { synthesizeFixturePackage, MO_GROUNDING } = await mods();
    const brief = { topic: String(seed), jurisdiction: 'MO', creditType: 'ethics', hours: 1 };
    const pkg = synthesizeFixturePackage(brief, MO_GROUNDING);
    return {
      outcome: 'pass',
      artifact: {
        id: caseInput.id || 'sw-gen-1',
        title: pkg.course?.title || String(seed).slice(0, 80),
        body: pkg.course?.description || `Generated: ${seed}`,
      },
      course_package: pkg,
    };
  },
};

export const BrokenProvider = {
  run() {
    return { outcome: 'pass', artifact: {} };
  },
};

/** Sync wrapper for conformance runner (cases are sync in runner — use preloaded sync path). */
export function runSync(caseInput, impl = Provider) {
  const seed = caseInput.seed || caseInput.topic || '';
  if (!String(seed).trim()) {
    return { outcome: 'reject', error_code: 'SEED_REQUIRED' };
  }
  // Broken path
  if (impl === BrokenProvider) return BrokenProvider.run(caseInput);
  // Sync: require can't load ESM; tests use dynamic import helper
  throw new Error('Use runSurewealthConformance() for async provider');
}

export async function runSurewealthConformance(caseInput, broken = false) {
  if (broken) return BrokenProvider.run(caseInput);
  return Provider.run(caseInput);
}
