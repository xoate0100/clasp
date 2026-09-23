/**
 * Executing conformance runner (Node) — mirrors Python case_exec + assert_ops.
 */
function getPath(data, path) {
  let p = path.startsWith('$.') ? path.slice(2) : path;
  let cur = data;
  for (const part of p.split('.')) {
    if (Array.isArray(cur) && /^\d+$/.test(part)) {
      const idx = Number(part);
      if (idx < 0 || idx >= cur.length) throw new Error(path);
      cur = cur[idx];
      continue;
    }
    if (cur == null || typeof cur !== 'object' || !(part in cur)) {
      throw new Error(path);
    }
    cur = cur[part];
  }
  return cur;
}

function checkAssert(result, assertion) {
  const { op, path } = assertion;
  const expected = assertion.value;
  if (op === 'exists') {
    getPath(result, path);
    return;
  }
  const actual = getPath(result, path);
  if (op === 'eq' && actual !== expected) {
    throw new Error(`${path}: expected ${JSON.stringify(expected)} got ${JSON.stringify(actual)}`);
  }
  if (op === 'neq' && actual === expected) {
    throw new Error(`${path}: expected not ${JSON.stringify(expected)}`);
  }
  if (op === 'type') {
    const ok =
      (expected === 'array' && Array.isArray(actual)) ||
      (expected === 'object' && actual !== null && typeof actual === 'object' && !Array.isArray(actual)) ||
      (expected === 'string' && typeof actual === 'string') ||
      (expected === 'number' && typeof actual === 'number') ||
      (expected === 'boolean' && typeof actual === 'boolean');
    if (!ok) throw new Error(`${path}: type mismatch want=${expected}`);
  }
  if (op === 'contains' && !actual.includes(expected)) {
    throw new Error(`${path}: ${JSON.stringify(expected)} not in ${JSON.stringify(actual)}`);
  }
}

function invoke(impl, caseInput) {
  try {
    return impl.run(caseInput);
  } catch (exc) {
    return { outcome: 'fail', error_code: 'IMPL_EXCEPTION', detail: String(exc) };
  }
}

function normalizeOutcome(result) {
  if (result.outcome != null) return String(result.outcome);
  return result.error_code ? 'reject' : 'pass';
}

function errorMismatch(result, expect, want) {
  if (!['reject', 'fail'].includes(want)) return null;
  const code = expect.error_code;
  if (!code) return null;
  if (result.error_code === code) return null;
  return `error_code want=${code} got=${result.error_code}`;
}

function assertFailures(result, expect) {
  for (const assertion of expect.asserts || []) {
    try {
      checkAssert(result, assertion);
    } catch (exc) {
      return String(exc.message || exc);
    }
  }
  return null;
}

export function runCase(impl, caseDef) {
  const expect = caseDef.expect;
  const want = expect.outcome;
  const result = invoke(impl, caseDef.input || {});
  const got = normalizeOutcome(result);
  if (got !== want) {
    return { case_id: caseDef.id, passed: false, detail: `outcome want=${want} got=${got}` };
  }
  const err = errorMismatch(result, expect, want);
  if (err) return { case_id: caseDef.id, passed: false, detail: err };
  const detail = assertFailures(result, expect);
  if (detail) return { case_id: caseDef.id, passed: false, detail };
  return { case_id: caseDef.id, passed: true, detail: 'ok' };
}

export function runSuite(impl, suite) {
  const cases = (suite.cases || []).map((c) => runCase(impl, c));
  return {
    suite_id: suite.suite_id || 'unknown',
    passed: cases.length > 0 && cases.every((c) => c.passed),
    cases,
    failed_ids: cases.filter((c) => !c.passed).map((c) => c.case_id),
  };
}
