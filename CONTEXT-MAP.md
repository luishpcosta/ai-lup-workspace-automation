# Context Map

Monorepo: `backend/` (motor de workflow, implementado) e `frontend/` (reservado,
ainda sem código — ver Planejamento).

## Contextos

- [motor-workflow](./backend/docs/motor-workflow/CONTEXT.md) — motor de workflow
  local com plugins Python, mais seus pontos de entrada (CLI, HTTP) e observabilidade
  (execuções paralelas, monitoria, streaming)

## Relacionamentos

Sem relacionamentos entre contextos ainda — `frontend/` não tem contexto próprio
até que passe a ter código.

## Decisões (ADR)

- [Registro de decisões](./backend/adr/) — ADR-001 a ADR-005, todas em `contextos:
  [motor-workflow]`. Ver `backend/adr/ADR-00N-*.md` para o front matter de relação
  (`depende_de`/`afeta`/`supera`) de cada uma.

## Planejamento (to-be)

- **motor-workflow**: [specs](./backend/specs/) — spec/plan/tasks por feature
  (harness SDD, `backend/AGENTS.md`), uma pasta por feature numerada (`001-...` a
  `005-...`, todas implementadas).
- **frontend**: pasta reservada (`./frontend/`), sem contexto/ADR/specs ainda —
  criar quando o trabalho de UI começar de fato.
