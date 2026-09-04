import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseArgs, verificationCommands } from '../scripts/lib/sdd-utils.mjs';

test('parseArgs handles flags, inline values, and positionals', () => {
  const args = parseArgs(['--target', '/tmp/x', '--force', '--agent-file=CLAUDE.md', 'pos']);
  assert.equal(args.target, '/tmp/x');
  assert.equal(args.force, true);
  assert.equal(args.agentFile, 'CLAUDE.md');
  assert.deepEqual(args._, ['pos']);
});

test('verificationCommands picks stack-specific commands', () => {
  assert.deepEqual(verificationCommands({ stack: 'go' }), ['go test ./...']);
  assert.deepEqual(verificationCommands({ stack: 'python' }), ['python -m pytest', 'python -m compileall .']);
});
