#!/usr/bin/env node
import path from 'node:path';
import { exists, parseArgs } from './lib/sdd-utils.mjs';

const args = parseArgs(process.argv.slice(2));

if (args.help) {
  console.log(`Usage: node scripts/validate-sdd-harness.mjs [--target DIR]

REMOVED: structural scoring depended on spec-registry.json, which this skill
no longer uses. This command stays as a no-op (exit 0) for compatibility.`);
  process.exit(0);
}

const target = path.resolve(args.target || args._[0] || process.cwd());
const registryPath = path.join(target, 'spec-registry.json');

console.error('validate-sdd-harness.mjs was removed: it scored a harness against spec-registry.json, which sdd-harness-creator no longer uses.');
if (await exists(registryPath)) {
  console.error(`Found ${path.relative(target, registryPath) || 'spec-registry.json'} from an older version of this harness.`);
  console.error('Run "node skills/sdd-harness-creator/scripts/migrate-from-registry.mjs --target ." once, then remove any references to this command.');
}
process.exit(0);
