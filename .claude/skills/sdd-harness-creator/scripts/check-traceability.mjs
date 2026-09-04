#!/usr/bin/env node
import path from 'node:path';
import { exists, parseArgs } from './lib/sdd-utils.mjs';

const args = parseArgs(process.argv.slice(2));

if (args.help) {
  console.log(`Usage: node scripts/check-traceability.mjs [--target DIR]

REMOVED: sdd-harness-creator no longer tracks state in spec-registry.json.
Traceability is now a manual check against the "Coverage Check" section in
each feature's tasks.md. This command stays as a no-op (exit 0) so old
init.sh scripts that call it don't break.`);
  process.exit(0);
}

const target = path.resolve(args.target || args._[0] || process.cwd());
const registryPath = path.join(target, 'spec-registry.json');

console.error('check-traceability.mjs was removed: sdd-harness-creator no longer tracks state in spec-registry.json.');
console.error('Traceability is now a manual check against the "Coverage Check" section in each feature\'s tasks.md.');
if (await exists(registryPath)) {
  console.error(`Found ${path.relative(target, registryPath) || 'spec-registry.json'} from an older version of this harness.`);
  console.error('Run "node skills/sdd-harness-creator/scripts/migrate-from-registry.mjs --target ." once, then remove this step from init.sh.');
}
process.exit(0);
