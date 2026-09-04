import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { test } from 'node:test';

const run = promisify(execFile);
const SCRIPTS = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'scripts');

async function withTempProject(fn) {
  const dir = await mkdtemp(path.join(tmpdir(), 'sdd-harness-'));
  try {
    await fn(dir);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

test('create-sdd-harness scaffolds all expected files (no spec-registry.json)', async () => {
  await withTempProject(async (dir) => {
    await run('node', [path.join(SCRIPTS, 'create-sdd-harness.mjs'), '--target', dir]);
    for (const rel of [
      'AGENTS.md', 'constitution.md',
      'progress.md', 'init.sh',
      'specs/001-example/spec.md', 'specs/001-example/plan.md', 'specs/001-example/tasks.md'
    ]) {
      const content = await readFile(path.join(dir, rel), 'utf8');
      assert.ok(content.length > 0, `${rel} should exist and be non-empty`);
    }
    await assert.rejects(readFile(path.join(dir, 'spec-registry.json')));
  });
});

test('scaffold fills date placeholders (no YYYY-MM-DD masks left)', async () => {
  await withTempProject(async (dir) => {
    await run('node', [path.join(SCRIPTS, 'create-sdd-harness.mjs'), '--target', dir]);
    for (const rel of ['progress.md', 'specs/001-example/spec.md', 'specs/001-example/plan.md', 'specs/001-example/tasks.md']) {
      const content = await readFile(path.join(dir, rel), 'utf8');
      assert.doesNotMatch(content, /YYYY-MM-DD/, `${rel} still has a date mask`);
      assert.match(content, /\*\*Last [Uu]pdated:\*\* \d{4}-\d{2}-\d{2}/, `${rel} should carry a real date`);
    }
  });
});

test('reverse-engineer adds a documented feature with phase/origin in the markdown', async () => {
  await withTempProject(async (dir) => {
    await run('node', [path.join(SCRIPTS, 'create-sdd-harness.mjs'), '--target', dir]);
    await mkdir(path.join(dir, 'src', 'auth'), { recursive: true });
    await writeFile(path.join(dir, 'src', 'auth', 'login.ts'), 'export function login() { return true; }\n');
    await writeFile(
      path.join(dir, 'src', 'auth', 'login.test.ts'),
      "import { it } from 'node:test';\nit('logs the user in', () => {});\n"
    );

    const { stdout } = await run('node', [path.join(SCRIPTS, 'reverse-engineer.mjs'), '--target', dir]);
    assert.match(stdout, /002-auth/);

    const spec = await readFile(path.join(dir, 'specs', '002-auth', 'spec.md'), 'utf8');
    assert.match(spec, /\*\*Phase:\*\* documented/);
    assert.match(spec, /\*\*Origin:\*\* reverse-engineered/);
    assert.doesNotMatch(spec, /YYYY-MM-DD/, 'retro-spec should not keep the date mask');
    assert.match(spec, /\*\*Last updated:\*\* \d{4}-\d{2}-\d{2}/);

    const tasks = await readFile(path.join(dir, 'specs', '002-auth', 'tasks.md'), 'utf8');
    assert.match(tasks, /AC-1/);
  });
});

test('reverse-engineer --dry-run writes nothing', async () => {
  await withTempProject(async (dir) => {
    await run('node', [path.join(SCRIPTS, 'create-sdd-harness.mjs'), '--target', dir]);
    await mkdir(path.join(dir, 'src', 'billing'), { recursive: true });
    await writeFile(path.join(dir, 'src', 'billing', 'charge.ts'), 'export function charge() {}\n');

    const { stdout } = await run('node', [path.join(SCRIPTS, 'reverse-engineer.mjs'), '--target', dir, '--dry-run']);
    assert.match(stdout, /Dry run/);

    await assert.rejects(readFile(path.join(dir, 'specs', '003-billing', 'spec.md')));
  });
});

test('reverse-engineer skips a module that already has a specs/ entry', async () => {
  await withTempProject(async (dir) => {
    await run('node', [path.join(SCRIPTS, 'create-sdd-harness.mjs'), '--target', dir]);
    await mkdir(path.join(dir, 'src', 'example'), { recursive: true });
    await writeFile(path.join(dir, 'src', 'example', 'thing.ts'), 'export function thing() {}\n');

    const { stdout } = await run('node', [path.join(SCRIPTS, 'reverse-engineer.mjs'), '--target', dir]);
    assert.doesNotMatch(stdout, /001-example/);
  });
});

test('check-traceability.mjs shim exits 0 and points at migrate-from-registry.mjs when spec-registry.json exists', async () => {
  await withTempProject(async (dir) => {
    await writeFile(path.join(dir, 'spec-registry.json'), JSON.stringify({ features: [] }));
    const { stderr } = await run('node', [path.join(SCRIPTS, 'check-traceability.mjs'), '--target', dir]);
    assert.match(stderr, /removed/i);
    assert.match(stderr, /migrate-from-registry\.mjs/);
  });
});

test('check-traceability.mjs shim exits 0 with no spec-registry.json present', async () => {
  await withTempProject(async (dir) => {
    await run('node', [path.join(SCRIPTS, 'check-traceability.mjs'), '--target', dir]);
  });
});

test('validate-sdd-harness.mjs shim exits 0', async () => {
  await withTempProject(async (dir) => {
    await run('node', [path.join(SCRIPTS, 'validate-sdd-harness.mjs'), '--target', dir]);
  });
});

test('migrate-from-registry reports nothing to migrate when there is no spec-registry.json', async () => {
  await withTempProject(async (dir) => {
    const { stdout } = await run('node', [path.join(SCRIPTS, 'migrate-from-registry.mjs'), '--target', dir]);
    assert.match(stdout, /Nothing to migrate/);
  });
});

test('migrate-from-registry summarizes and backs up an existing spec-registry.json', async () => {
  await withTempProject(async (dir) => {
    const registry = {
      features: [{
        id: '001-example', name: 'Example Feature', phase: 'tasked',
        acceptance_criteria: [
          { id: 'AC-1', description: 'x', tasks: ['T-1'], status: 'verified', evidence: 'tests pass' },
          { id: 'AC-2', description: 'y', tasks: ['T-1'], status: 'pending' }
        ]
      }]
    };
    await writeFile(path.join(dir, 'spec-registry.json'), JSON.stringify(registry));

    const { stdout } = await run('node', [path.join(SCRIPTS, 'migrate-from-registry.mjs'), '--target', dir]);
    assert.match(stdout, /001-example \[tasked\]/);
    assert.match(stdout, /AC 1\/2 verified/);
    assert.match(stdout, /Renamed spec-registry\.json/);

    await assert.rejects(readFile(path.join(dir, 'spec-registry.json')));
    const backup = JSON.parse(await readFile(path.join(dir, 'spec-registry.json.bak'), 'utf8'));
    assert.deepEqual(backup, registry);
  });
});

test('migrate-from-registry does not overwrite an existing backup', async () => {
  await withTempProject(async (dir) => {
    await writeFile(path.join(dir, 'spec-registry.json'), JSON.stringify({ features: [] }));
    await writeFile(path.join(dir, 'spec-registry.json.bak'), 'previous backup');

    const { stderr } = await run('node', [path.join(SCRIPTS, 'migrate-from-registry.mjs'), '--target', dir]);
    assert.match(stderr, /already exists/);

    const original = await readFile(path.join(dir, 'spec-registry.json'), 'utf8');
    assert.equal(JSON.parse(original).features.length, 0);
    const backup = await readFile(path.join(dir, 'spec-registry.json.bak'), 'utf8');
    assert.equal(backup, 'previous backup');
  });
});
