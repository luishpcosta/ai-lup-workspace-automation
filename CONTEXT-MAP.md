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

Cada contexto mantém seu próprio diretório de ADRs, mas a **numeração é global e
sequencial entre eles** (não reinicia por contexto) — antes de criar uma ADR nova,
em qualquer contexto, confira o maior número já usado nos dois diretórios abaixo.

- [Registro de decisões — motor-workflow](./backend/adr/) — ADR-001 a ADR-005,
  todas em `contextos: [motor-workflow]`.
- [Registro de decisões — frontend](./frontend/adr/) — ADR-006 (`contextos:
  [frontend]`, `afeta: [motor-workflow]`) — próxima ADR nova, em qualquer
  contexto, é ADR-007.

Ver `<contexto>/adr/ADR-00N-*.md` para o front matter de relação
(`depende_de`/`afeta`/`supera`) de cada uma.

## Planejamento (to-be)

- **motor-workflow**: [specs](./backend/docs/specs/) — spec/plan/tasks por feature
  (harness SDD, `backend/AGENTS.md`), uma pasta por feature numerada (`001-...` a
  `005-...`, todas implementadas).
- **frontend**: harness SDD próprio criado (`frontend/AGENTS.md`,
  `frontend/constitution.md`, `frontend/init.sh`); [specs](./frontend/docs/specs/)
  ainda vazio — `docs/specs/006-frontend-painel-controle/{spec,plan,tasks}.md` (a
  partir da ADR-006) é o próximo passo antes de codificar, por `frontend/AGENTS.md`.
