# {{AGENT_FILE_NAME}}

{{PROJECT_PURPOSE}}

This project uses **Spec-Driven Development (SDD)**: the specification is the source of truth. Code is derived from the spec, and a feature is done only when every acceptance criterion has recorded evidence. Do not write code before its feature has passed the Tasks gate.

## Startup Workflow

Before doing anything:

1. **Confirm working directory** with `pwd`
2. **Read this file** completely
3. **Read `constitution.md`** — these are non-negotiable project principles
4. **Run `./init.sh`** to verify environment health
5. **Check feature status**: look at the `**Phase:**` line at the top of each `specs/NNN-slug/spec.md` (or `plan.md`/`tasks.md`)
6. **Review recent commits** with `git log --oneline -5`

If `init.sh` fails, repair that before adding new scope.

## The SDD Flow

Advance exactly **one feature at a time** through these phases. Each phase has a gate; do not enter the next phase until the gate passes.

| Phase | You produce | Gate to leave |
|---|---|---|
| **Specify** | `specs/NNN-slug/spec.md` | Every requirement has a testable acceptance criterion (AC-ID); scope and edge cases stated |
| **Clarify** | clarifications resolved in spec.md | Zero `[NEEDS CLARIFICATION]` markers remain |
| **Plan** | `specs/NNN-slug/plan.md` | Every functional requirement is addressed; decisions consistent with `constitution.md` |
| **Tasks** | `specs/NNN-slug/tasks.md` | Every AC has ≥1 task **and** every task references an AC |
| **Implement** | code + tests | One task at a time; never start before the Tasks gate passes |
| **Verify** | evidence in `tasks.md`'s Evidence column and `progress.md` | Every AC has recorded passing evidence |

Update the `**Phase:**` line at the top of the feature's `spec.md`/`plan.md`/`tasks.md` as you advance.

## Authoring Guidance (per phase)

- **Specify** — Describe *what* and *why*, never *how*. Write acceptance criteria as testable statements (`AC-1: Given… When… Then…`). Mark anything uncertain with `[NEEDS CLARIFICATION: question]`. List explicit non-goals.
- **Clarify** — Resolve every marker. Record the answer inline; if it changes scope, update the acceptance criteria.
- **Plan** — Describe *how*: architecture, data model, interfaces/contracts, key decisions and alternatives. Reference the constitution for any constraint you rely on. Cover every functional requirement.
- **Tasks** — Break the plan into small, ordered, independently verifiable tasks. Tag each task with the AC it satisfies in `tasks.md`'s Satisfies column (e.g. `T-3` satisfies `AC-2`).
- **Implement** — Take one task, implement it, write/extend the test that proves its AC, then mark the task `done` in `tasks.md` with evidence in the Evidence column.

## Working Rules

- **Spec is truth**: if code and spec disagree, fix the spec first (or the code to match it) — never silently diverge.
- **No skipped gates**: bypassing a gate requires an explicit decision recorded in `progress.md`.
- **Stay in scope**: only touch files for the current feature's current task.
- **Verification required**: don't mark an AC verified without running the check and recording evidence.
- **Leave clean state**: the next session must be able to run `./init.sh` immediately.

## Required Artifacts

- `constitution.md` — project principles/invariants
- `specs/NNN-slug/{spec,plan,tasks}.md` — per-feature documents; each carries its own `**Phase:**`, and `tasks.md` carries per-task Status/Evidence
- `progress.md` — session continuity log
- `init.sh` — verification

## Definition of Done

A feature is done only when ALL are true:

- [ ] `spec.md`, `plan.md`, `tasks.md` exist and their gates passed
- [ ] Every acceptance criterion has task(s) marked `done` in `tasks.md` with evidence in the Evidence column
- [ ] `tasks.md`'s Coverage Check confirms no orphan ACs/tasks, and `spec.md` has zero open `[NEEDS CLARIFICATION]` markers
- [ ] Required verification (tests / lint / type-check) actually ran
- [ ] Repository remains restartable from `./init.sh`

## End of Session

1. Update the touched feature's `**Phase:**` line and the Status/Evidence columns in `tasks.md`
2. Update `progress.md` with current state and the active phase
3. Record unresolved clarifications, blockers, or risks
4. Commit with a descriptive message once work is in a safe state
5. Leave the repo clean enough to run `./init.sh` immediately

## Verification Commands

```bash
# Full verification
{{PRIMARY_VERIFICATION_COMMAND}}
```

Required checks:
{{VERIFICATION_COMMANDS}}

## Escalation

- **Constitution conflict**: stop and ask the user; never override a principle silently.
- **Unresolvable ambiguity**: keep it as `[NEEDS CLARIFICATION]`, flag in `progress.md`, ask the user.
- **Repeated test failures**: update progress, flag for human review.
- **Scope ambiguity**: re-read the feature's `spec.md` acceptance criteria.
