import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  buildReverseFeature,
  detectSourceRoot,
  extractExports,
  extractTestNames,
  groupIntoModules,
  isTestFile,
  slugify
} from '../scripts/lib/reverse.mjs';

test('slugify normalizes names', () => {
  assert.equal(slugify('User Auth!'), 'user-auth');
  assert.equal(slugify('___'), 'module');
});

test('isTestFile recognizes common test conventions', () => {
  assert.equal(isTestFile('src/auth/auth.test.ts'), true);
  assert.equal(isTestFile('tests/test_login.py'), true);
  assert.equal(isTestFile('src/auth/auth.ts'), false);
});

test('detectSourceRoot prefers src then lib then app', () => {
  assert.equal(detectSourceRoot(['src/a.ts', 'lib/b.ts']), 'src');
  assert.equal(detectSourceRoot(['lib/b.ts']), 'lib');
  assert.equal(detectSourceRoot(['index.js']), '');
});

test('groupIntoModules splits by first segment under source root', () => {
  const modules = groupIntoModules(
    ['src/auth/login.ts', 'src/auth/login.test.ts', 'src/billing/charge.ts', 'README.md'],
    'src'
  );
  assert.deepEqual(modules.map((m) => m.name), ['auth', 'billing']);
  const auth = modules.find((m) => m.name === 'auth');
  assert.deepEqual(auth.sourceFiles, ['src/auth/login.ts']);
  assert.deepEqual(auth.testFiles, ['src/auth/login.test.ts']);
});

test('extractExports handles JS/TS forms', () => {
  const names = extractExports(
    `export function login() {}
     export const TOKEN = 1;
     export class Session {}
     export { helper as publicHelper };
     module.exports.legacy = 1;`,
    '.ts'
  );
  assert.ok(names.includes('login'));
  assert.ok(names.includes('TOKEN'));
  assert.ok(names.includes('Session'));
  assert.ok(names.includes('publicHelper'));
  assert.ok(names.includes('legacy'));
});

test('extractExports handles Python public defs/classes', () => {
  const names = extractExports(`def login():\n    pass\nclass Session:\n    pass\ndef _private():\n    pass`, '.py');
  assert.deepEqual(names.sort(), ['Session', 'login']);
});

test('extractTestNames reads JS test titles and python test fns', () => {
  const js = extractTestNames(`describe('auth', () => { it('logs in', () => {}); test("rejects bad password", () => {}); });`);
  assert.ok(js.includes('logs in'));
  assert.ok(js.includes('rejects bad password'));
  const py = extractTestNames(`def test_logs_in():\n    pass`);
  assert.ok(py.includes('logs in'));
});

test('buildReverseFeature derives ACs from tests and stays traceability-clean', () => {
  const module = { name: 'auth', sourceFiles: ['src/auth/login.ts'], testFiles: ['src/auth/login.test.ts'] };
  const feature = buildReverseFeature({
    module,
    index: 2,
    exportsByFile: { 'src/auth/login.ts': ['login'] },
    testNames: ['logs in', 'rejects bad password']
  });
  assert.equal(feature.id, '002-auth');
  assert.equal(feature.acSource, 'tests');
  assert.equal(feature.criteria.length, 2);
});

test('buildReverseFeature falls back to exports, then to module-level AC', () => {
  const exportsOnly = buildReverseFeature({
    module: { name: 'billing', sourceFiles: ['src/billing/charge.ts'], testFiles: [] },
    index: 3,
    exportsByFile: { 'src/billing/charge.ts': ['charge', 'refund'] },
    testNames: []
  });
  assert.equal(exportsOnly.acSource, 'exports');
  assert.equal(exportsOnly.criteria.length, 2);

  const bare = buildReverseFeature({
    module: { name: 'util', sourceFiles: ['src/util/x.ts'], testFiles: [] },
    index: 4,
    exportsByFile: {},
    testNames: []
  });
  assert.equal(bare.acSource, 'module');
  assert.equal(bare.criteria.length, 1);
});
