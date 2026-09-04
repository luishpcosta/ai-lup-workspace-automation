#!/usr/bin/env node
import { readdir } from 'node:fs/promises';
import path from 'node:path';
import {
  exists,
  listFiles,
  parseArgs,
  readText,
  writeText
} from './lib/sdd-utils.mjs';
import {
  buildReverseFeature,
  detectSourceRoot,
  extOf,
  extractExports,
  extractTestNames,
  groupIntoModules
} from './lib/reverse.mjs';

const args = parseArgs(process.argv.slice(2));

if (args.help) {
  console.log(`Usage: node scripts/reverse-engineer.mjs [--target DIR] [--src DIR] [--max-features N] [--dry-run] [--force]

Brownfield reverse-engineering: scans existing code and produces reconstructed
(retro) specs so new work can build on documented behavior.

For each detected module it derives acceptance criteria (preferring existing test
names, else exported symbols) and writes specs/NNN-slug/{spec,plan,tasks}.md with
phase: documented in the spec.md header.

  --src DIR        source root override (default: auto-detect src/ lib/ app/)
  --max-features N cap the number of features created (default 20)
  --dry-run        print what would be created without writing
  --force          overwrite existing spec files for a feature

Modules already present (an existing specs/NNN-slug directory by slug) are skipped.`);
  process.exit(0);
}

const target = path.resolve(args.target || args._[0] || process.cwd());
const dryRun = Boolean(args.dryRun);
const force = Boolean(args.force);
const maxFeatures = Number(args.maxFeatures || 20);

if (!await exists(target)) {
  console.error(`Target does not exist: ${target}`);
  process.exit(2);
}

const files = await listFiles(target, { maxFiles: 4000 });
const sourceRoot = args.src !== undefined ? String(args.src).replace(/\/$/, '') : detectSourceRoot(files);
const modules = groupIntoModules(files, sourceRoot);

if (modules.length === 0) {
  console.log(`No source modules detected under ${sourceRoot ? `${sourceRoot}/` : target}. Nothing to reverse-engineer.`);
  process.exit(0);
}

// Figure out which feature slugs/indices already exist under specs/.
const specsDir = path.join(target, 'specs');
let existingFeatureIds = [];
if (await exists(specsDir)) {
  const entries = await readdir(specsDir, { withFileTypes: true });
  existingFeatureIds = entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name);
}

const existingSlugs = new Set(existingFeatureIds.map((id) => id.replace(/^\d+-/, '')));
const nextIndex = () => {
  const max = existingFeatureIds.reduce((acc, id) => {
    const match = /^(\d+)-/.exec(id);
    return match ? Math.max(acc, Number(match[1])) : acc;
  }, 0);
  return max + 1;
};

const created = [];
let index = nextIndex();

for (const module of modules) {
  if (created.length >= maxFeatures) break;
  const slug = module.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  if (existingSlugs.has(slug)) continue;

  const exportsByFile = {};
  for (const file of module.sourceFiles) {
    exportsByFile[file] = extractExports(await readText(path.join(target, file)), extOf(file));
  }
  const testNames = [];
  for (const file of module.testFiles) {
    testNames.push(...extractTestNames(await readText(path.join(target, file))));
  }

  const feature = buildReverseFeature({ module, index, exportsByFile, testNames: [...new Set(testNames)] });
  created.push(feature);
  existingSlugs.add(slug);
  index += 1;
}

if (created.length === 0) {
  console.log('All detected modules already have a specs/ entry. Nothing new to add.');
  process.exit(0);
}

console.log(`Reverse-engineering ${target}`);
console.log(`Source root: ${sourceRoot || '(repo root)'} | modules detected: ${modules.length} | features ${dryRun ? 'to add' : 'added'}: ${created.length}`);
console.log('');

for (const feature of created) {
  console.log(`${dryRun ? 'WOULD ADD' : 'ADD'} ${feature.id}  (${feature.criteria.length} AC from ${feature.acSource})`);
  if (dryRun) continue;
  const dir = path.join(target, 'specs', feature.id);
  await copyMarkdown(path.join(dir, 'spec.md'), feature.specMarkdown, force);
  await copyMarkdown(path.join(dir, 'plan.md'), feature.planMarkdown, force);
  await copyMarkdown(path.join(dir, 'tasks.md'), feature.tasksMarkdown, force);
}

if (!dryRun) {
  console.log('');
  console.log('Next: review each retro-spec\'s Acceptance Criteria and Assumptions/To Confirm checklist.');
} else {
  console.log('');
  console.log('Dry run — no files written.');
}

async function copyMarkdown(filePath, contents, overwrite) {
  if (!overwrite && await exists(filePath)) {
    console.log(`  SKIP ${path.relative(target, filePath)} (exists)`);
    return;
  }
  await writeText(filePath, contents);
  console.log(`  WRITE ${path.relative(target, filePath)}`);
}
