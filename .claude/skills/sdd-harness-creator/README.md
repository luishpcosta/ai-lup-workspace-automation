# sdd-harness-creator

A compact skill for building and auditing **spec-driven (SDD)** harnesses around AI coding agents.

It makes a repository drive implementation from specifications: each feature flows through Specify → Clarify → Plan → Tasks → Implement → Verify, with gates between phases and traceability from every acceptance criterion to a task and to verification evidence.

It is the spec-driven sibling of `harness-creator`. The scripts use only Node.js built-in modules and are self-contained, so the skill installs and runs independently.

## Use

```bash
node skills/sdd-harness-creator/scripts/create-sdd-harness.mjs --target /path/to/project
node skills/sdd-harness-creator/scripts/reverse-engineer.mjs   --target /path/to/project   # brownfield
```

For an existing codebase, `reverse-engineer.mjs` reconstructs specs from current behavior: it scans source modules, derives acceptance criteria from existing tests (or exported symbols), and seeds `specs/` with `**Phase:** documented` features. Use `--dry-run` first.

## What It Creates

- `AGENTS.md` or `CLAUDE.md` — SDD flow and phase gates
- `constitution.md` — project principles/invariants
- `specs/NNN-slug/{spec,plan,tasks}.md` — example feature
- `progress.md`
- `init.sh` — verification

## Tracking state

There's no separate registry file — each `spec.md`/`plan.md`/`tasks.md` carries its own `**Phase:**` line, and `tasks.md` carries per-task Status/Evidence columns plus a Coverage Check. Traceability and verification are confirmed manually against those, not by a script.

## Migrating from a version with `spec-registry.json`

If a project already has `spec-registry.json` from an older version of this skill:

```bash
node skills/sdd-harness-creator/scripts/migrate-from-registry.mjs --target /path/to/project
```

It prints a summary of what the registry tracked, renames it to `spec-registry.json.bak` (never deletes), and lists what to check by hand in `AGENTS.md`/`CLAUDE.md`/`init.sh`.

## Boundaries

This skill is for spec-driven harness engineering, not model selection, prompt tuning alone, or app architecture. Keep project-specific facts (constitution, specs) in the target repository.
