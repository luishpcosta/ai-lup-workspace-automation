# Upgrading an already-scaffolded harness

`lup-skills update sdd-harness-creator` only replaces this skill's own files in the
target repo (`.claude/skills/sdd-harness-creator/` or `.agents/skills/sdd-harness-creator/`).
It never touches what `create-sdd-harness.mjs` already wrote *inside* that repo —
`AGENTS.md`/`CLAUDE.md`, `constitution.md`, `init.sh`, `specs/**`. So whenever this
skill's templates or scripts change, already-scaffolded repos can silently fall out
of sync. Run this checklist in such a repo after updating the skill.

## Checklist

1. **`spec-registry.json` present?** Run:
   ```bash
   node skills/sdd-harness-creator/scripts/migrate-from-registry.mjs --target .
   ```
   It backs the file up (never deletes) and prints what it tracked.

2. **`init.sh`** — look for any step calling a script that's now a no-op shim
   (`check-traceability.mjs`, `validate-sdd-harness.mjs`). Remove that step; those
   scripts now exist only to keep old `init.sh` files from breaking, not as a real gate.

3. **`AGENTS.md` / `CLAUDE.md`** — search for `spec-registry.json`,
   `registry-status.mjs`, `registry-update.mjs`. Replace any mention with:
   - phase tracked in the `**Phase:**` line of each `spec.md`/`plan.md`/`tasks.md`
   - evidence tracked in `tasks.md`'s Status/Evidence columns and in `progress.md`

4. **`constitution.md`** — check the quality-bar/verification section for any claim
   that `./init.sh` runs a traceability gate (`check-traceability`). Update it to
   describe what `init.sh` actually verifies now (it usually still names something
   that no longer exists, even after step 2-3 are done — it's easy to miss).

5. Re-run `./init.sh` and confirm it's still green before committing.

## When this applies

Only to repos scaffolded before this skill dropped `spec-registry.json`. A fresh
`create-sdd-harness.mjs` run already produces the markdown-only shape — nothing
in this checklist applies to it.
