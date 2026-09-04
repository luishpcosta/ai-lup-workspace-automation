# Spec-Driven Pattern

## Problem

Agents that jump straight to code optimize for "something that runs" instead of "the thing that was asked." They invent requirements, skip edge cases, and declare done without proof. SDD fixes this by making the **specification the source of truth** and deriving everything else from it.

## The Flow

```
Constitution (once)
   │
   ▼
Specify → Clarify → Plan → Tasks → Implement → Verify
   └────────── one feature at a time, gated ──────────┘
```

Each arrow is a **gate**. You cannot enter the next phase until the current gate passes.

| Phase | Produces | Gate |
|---|---|---|
| Specify | `spec.md` (what/why) | Every requirement has a testable AC-ID; scope + edge cases stated |
| Clarify | resolved markers | Zero `[NEEDS CLARIFICATION]` left |
| Plan | `plan.md` (how) | Every FR covered; decisions consistent with the constitution |
| Tasks | `tasks.md` | Bidirectional AC↔task coverage |
| Implement | code + tests | One task at a time; AC proven by a test |
| Verify | evidence | Every AC `verified` with recorded evidence |

## Single source: markdown

There is no separate machine-readable registry. Each `spec.md`/`plan.md`/`tasks.md` carries its own `**Phase:**` line, and `tasks.md` carries a Status/Evidence column per task plus a Coverage Check section. The same AC IDs appear in `spec.md` and `tasks.md` so the two stay in sync by construction.

## Traceability rules (the core invariant)

1. **No orphan ACs** — every acceptance criterion links to ≥1 task in `tasks.md`.
2. **No orphan tasks** — every task in `tasks.md` references some AC.
3. **No open clarifications** past the draft phase.
4. **Evidence before done** — a task marked `done` must carry evidence; a `verified`/`done` feature must have *all* its ACs covered by `done` tasks.

These are confirmed manually against `tasks.md`'s Coverage Check before advancing a phase — there's no script gate, so this depends on the agent actually checking before claiming a feature done.

## Gates vs. the classic harness

The sibling `harness-creator` uses a feature list and a single "definition of done." SDD adds:

- a **constitution** (invariants that plans must honor),
- **per-phase gates** instead of one done-gate,
- **acceptance-criteria traceability** as a first-class, checkable property.

## Common failure modes

- **Spec leaks implementation** — tech/file names in `spec.md`. Keep how in `plan.md`.
- **Untestable ACs** — "works well" is not an AC. Use Given/When/Then with an observable outcome.
- **Silent gate skipping** — starting code before the Tasks gate. Record any deliberate skip in `progress.md`.
- **Done without evidence** — marking a task done with no command/output. Nothing checks this automatically; review `tasks.md`/`progress.md` before claiming the feature done.

## Brownfield adoption (reverse-engineering)

Most repos already have code. To adopt SDD without rewriting, run `reverse-engineer.mjs`: it scans source modules and reconstructs **retro-specs** so future work builds on documented behavior instead of guesses.

- Acceptance criteria are derived from **existing test names** when present (tests are de-facto specs), else from **exported/public symbols**.
- Features land with `**Phase:** documented` and `**Origin:** reverse-engineered` in the generated `spec.md` — meaning "code exists, spec reconstructed, pending re-verification." Advance them toward `verified`/`done` by confirming the criteria reflect *intended* behavior and recording evidence.
- Generated criteria describe *current* behavior. Always review them: current behavior is not necessarily correct behavior. Uncertainties go under "Assumptions / To Confirm" (not as gate-blocking `[NEEDS CLARIFICATION]` markers), so the Coverage Check stays clean while you triage.

## Authoring lives in the target repo

This pattern is enforced by the files the harness drops into the target repo (templates with inline guidance + `AGENTS.md` gates), so any agent can author specs without installing a skill. A dedicated authoring skill is only worth extracting later if the heuristics outgrow the templates.
