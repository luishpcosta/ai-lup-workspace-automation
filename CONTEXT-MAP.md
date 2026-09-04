# Context Map

Monorepo: `backend/` (motor de workflow, implementado) e `frontend/` (painel de
controle web, decidido na ADR-006, ainda não implementado — ver Planejamento).

## Contextos

- [motor-workflow](./backend/docs/motor-workflow/CONTEXT.md) — motor de workflow
  local com plugins Python, mais seus pontos de entrada (CLI, HTTP) e observabilidade
  (execuções paralelas, monitoria, streaming)
- [frontend](./frontend/docs/CONTEXT.md) — painel de controle web (SPA) que consome
  a API HTTP/SSE do motor-workflow

## Relacionamentos

- `frontend` depende de `motor-workflow` (consome `GET/POST /runs*`, SSE de
  `/stream`) — sem rota nova de negócio, só `CORSMiddleware` adicionado ao lado
  `motor-workflow` (ADR-006).

## Decisões (ADR)

- [Registro de decisões](./backend/adr/) — ADR-001 a ADR-006. ADR-001 a ADR-005 em
  `contextos: [motor-workflow]`; ADR-006 em `contextos: [frontend]`,
  `afeta: [motor-workflow]`. Ver `backend/adr/ADR-00N-*.md` para o front matter de
  relação (`depende_de`/`afeta`/`supera`) de cada uma.

## Planejamento (to-be)

- **motor-workflow**: [specs](./backend/docs/specs/) — spec/plan/tasks por feature
  (harness SDD, `backend/AGENTS.md`), uma pasta por feature numerada (`001-...` a
  `005-...`, todas implementadas).
- **frontend**: decidido na ADR-006 (painel de controle v1 via REST/SSE); specs
  (`spec.md`/`plan.md`/`tasks.md`) ainda não escritas — próximo passo antes de
  codificar, por `AGENTS.md`.
