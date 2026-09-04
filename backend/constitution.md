# Project Constitution

Non-negotiable principles for this repository. Plans and code must comply; conflicts are escalated to a human, never overridden silently.

> Replace the examples below with your project's real principles. Keep them few, concrete, and testable.

## Principles

1. **Spec before code** — No implementation begins before its feature has an approved spec and passes the Tasks gate.
2. **Every behavior is traceable** — Each acceptance criterion maps to a task and to verification evidence.
3. **Verification is mandatory** — A feature is done only when its acceptance criteria are proven by automated checks (or explicitly recorded manual evidence).
4. **Small, reversible steps** — One feature and one task at a time; keep the repo restartable.
5. **Plugin contract is stable** — Changes to the Plugin Interface (`run(context) -> output`, `TransientError`) require a new ADR; no silent breaking change to existing plugins.
6. **Hexagonal boundary is one-way** — `domain/` imports nothing from `application/` or `adapters/`; `application/` imports nothing from `adapters/`. Only `adapters/` (composition root: `adapters/cli.py`) may import concrete infrastructure (sqlite3, PyYAML, argparse, logging handlers).

## Technical Constraints

- **Language / stack**: Python >= 3.10 (ver `pyproject.toml`); motor de workflow local (`adr/ADR-001-motor-workflow-plugins.md`). Dependência externa: PyYAML (parsing da config declarativa).
- **Test framework**: pytest.
- **Style / lint**: Ruff (`ruff check` para lint, `ruff format --check` para formatação) — config em `pyproject.toml` (`[tool.ruff]`), regras `E`, `F`, `I` (isort), `UP` (pyupgrade), `B` (bugbear). Nenhuma exceção sem `# noqa` justificado inline.
- **Architecture boundaries**: arquitetura hexagonal (ports & adapters) em `src/workflow_engine/` — `domain/` (entidades + ports, sem infra), `application/` (orquestração, depende só de `domain/`), `adapters/` (implementações concretas + `cli.py` como composition root). Plugins nunca importam internals do motor — só `workflow_engine.plugin_sdk` (fachada pública sobre `domain.ports.Plugin`). O Workflow Engine nunca depende de um adapter concreto, apenas dos ports em `domain/ports.py`.

## Quality Bar

- Verification command(s) that must pass: `python -m pytest`, `python -m compileall .`, `ruff check .`, `ruff format --check .` (ver `init.sh`).
- Coverage / review expectations: toda AC de `specs/001-motor-workflow-plugins/spec.md` precisa de evidência de teste antes de a feature ser marcada `done` em `tasks.md`.

## Amendments

Changing this constitution requires an explicit decision recorded in `progress.md` (date, rationale, who approved).
