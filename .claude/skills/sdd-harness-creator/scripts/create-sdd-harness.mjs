#!/usr/bin/env node
import { chmod, mkdir } from 'node:fs/promises';
import path from 'node:path';
import {
  copyTemplate,
  detectPackageManager,
  detectProject,
  exists,
  initScriptFromCommands,
  isoDate,
  isoDateTime,
  parseArgs,
  verificationCommands,
  writeText
} from './lib/sdd-utils.mjs';

const args = parseArgs(process.argv.slice(2));

if (args.help) {
  console.log(`Usage: node scripts/create-sdd-harness.mjs [--target DIR] [--agent-file AGENTS.md|CLAUDE.md] [--package-manager npm|pnpm|yarn|bun] [--commands "a,b"] [--force]

Creates a spec-driven (SDD) harness:
  AGENTS.md or CLAUDE.md      (SDD flow + gates)
  constitution.md
  specs/001-example/{spec,plan,tasks}.md
  progress.md
  init.sh                     (verification)

Existing files are skipped unless --force is set.`);
  process.exit(0);
}

const target = path.resolve(args.target || args._[0] || process.cwd());
const agentFile = args.agentFile || 'AGENTS.md';
const force = Boolean(args.force);
const project = await detectProject(target);
project.packageManager = detectPackageManager(target, args.packageManager);
const commands = args.commands
  ? String(args.commands).split(',').map((command) => command.trim()).filter(Boolean)
  : verificationCommands(project, args.packageManager);

await mkdir(target, { recursive: true });

const agentReplacements = {
  AGENT_FILE_NAME: agentFile,
  PROJECT_PURPOSE: project.stack === 'generic'
    ? 'Spec-driven harness for reliable agent-assisted development.'
    : `Spec-driven harness for reliable agent-assisted development in a ${project.stack} codebase.`,
  VERIFICATION_COMMANDS: commands.map((command) => `- \`${command}\``).join('\n'),
  PRIMARY_VERIFICATION_COMMAND: './init.sh'
};

const dates = { DATE: isoDate(), DATETIME: isoDateTime() };
const exampleReplacements = { FEATURE_NAME: 'Example Feature', FEATURE_ID: '001-example', ...dates };

const results = [];
results.push(await copyTemplate('agents.md', path.join(target, agentFile), agentReplacements, { force }));
results.push(await copyTemplate('constitution.md', path.join(target, 'constitution.md'), {}, { force }));
results.push(await copyTemplate('progress.md', path.join(target, 'progress.md'), dates, { force }));

const exampleDir = path.join(target, 'specs', '001-example');
results.push(await copyTemplate('spec.md', path.join(exampleDir, 'spec.md'), exampleReplacements, { force }));
results.push(await copyTemplate('plan.md', path.join(exampleDir, 'plan.md'), exampleReplacements, { force }));
results.push(await copyTemplate('tasks.md', path.join(exampleDir, 'tasks.md'), exampleReplacements, { force }));

const initPath = path.join(target, 'init.sh');
if (force || !await exists(initPath)) {
  await writeText(initPath, initScriptFromCommands(commands));
  await chmod(initPath, 0o755);
  results.push({ path: initPath, status: 'written' });
} else {
  results.push({ path: initPath, status: 'skipped', reason: 'exists' });
}

console.log(`Created SDD harness for ${target}`);
console.log(`Detected stack: ${project.stack}`);
console.log('Verification commands:');
for (const command of commands) console.log(`  - ${command}`);
console.log('');
for (const result of results) {
  console.log(`${result.status.toUpperCase()} ${path.relative(target, result.path)}${result.reason ? ` (${result.reason})` : ''}`);
}
console.log('');
console.log('Next: replace specs/001-example with your first real feature.');
