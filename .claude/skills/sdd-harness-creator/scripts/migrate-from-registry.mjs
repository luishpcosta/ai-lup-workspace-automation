#!/usr/bin/env node
import { rename } from 'node:fs/promises';
import path from 'node:path';
import { exists, parseArgs, readText } from './lib/sdd-utils.mjs';

const args = parseArgs(process.argv.slice(2));

if (args.help) {
  console.log(`Usage: node scripts/migrate-from-registry.mjs [--target DIR]

One-time helper for a harness scaffolded before sdd-harness-creator dropped
spec-registry.json. It never deletes data:
  - prints a summary of every feature/phase/AC found in spec-registry.json
  - renames it to spec-registry.json.bak (skips if a .bak already exists)
  - prints a manual checklist for what still needs a human look (AGENTS.md/
    CLAUDE.md, init.sh, and constitution.md may reference removed scripts
    or the old file)

It does not attempt to auto-patch AGENTS.md/CLAUDE.md/init.sh/constitution.md:
those files are often customized per project, and guessing at a text
replacement there is exactly the kind of hidden destructive behavior this
skill avoids. See references/upgrading.md for the full step-by-step checklist.`);
  process.exit(0);
}

const target = path.resolve(args.target || args._[0] || process.cwd());
const registryPath = path.join(target, 'spec-registry.json');
const backupPath = `${registryPath}.bak`;

if (!await exists(registryPath)) {
  console.log(`No spec-registry.json found in ${target}. Nothing to migrate.`);
  process.exit(0);
}

let registry = null;
try {
  registry = JSON.parse(await readText(registryPath));
} catch (error) {
  console.error(`spec-registry.json is not valid JSON (${error.message}) — backing it up anyway, but no summary to show.`);
}

if (registry) {
  const features = Array.isArray(registry.features) ? registry.features : [];
  console.log(`Found ${features.length} feature(s) in ${path.relative(target, registryPath)}:`);
  console.log('');
  for (const feature of features) {
    const criteria = Array.isArray(feature.acceptance_criteria) ? feature.acceptance_criteria : [];
    const verified = criteria.filter((ac) => ac.status === 'verified').length;
    console.log(`  ${feature.id ?? '(unknown)'} [${feature.phase ?? '(unknown)'}] ${feature.name ?? ''} — AC ${verified}/${criteria.length} verified`);
  }
  console.log('');
}

if (await exists(backupPath)) {
  console.error(`${path.relative(target, backupPath)} already exists — leaving ${path.relative(target, registryPath)} in place. Resolve the existing backup manually.`);
} else {
  await rename(registryPath, backupPath);
  console.log(`Renamed ${path.relative(target, registryPath)} -> ${path.relative(target, backupPath)} (nothing deleted).`);
}

console.log('');
console.log('Manual checklist (not auto-patched — these files may be customized):');
console.log('  - init.sh: remove any step that calls check-traceability.mjs.');
console.log('  - AGENTS.md / CLAUDE.md: replace any mention of spec-registry.json,');
console.log('    registry-status.mjs, or registry-update.mjs with: phase tracked in');
console.log('    the **Phase:** line of each spec.md/plan.md/tasks.md; evidence');
console.log('    tracked in the Status/Evidence columns of tasks.md and in progress.md.');
console.log('  - constitution.md: check the quality-bar/verification section for any');
console.log('    claim that ./init.sh runs a traceability gate (check-traceability) and');
console.log('    update it to match what init.sh actually verifies now.');
console.log('See skills/sdd-harness-creator/references/upgrading.md for the full checklist.');
process.exit(0);
