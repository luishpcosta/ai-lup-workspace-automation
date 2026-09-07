# Context Map

Monorepo: `backend/` (motor de workflow, implementado) e `frontend/` (painel de
controle web, implementado desde a ADR-006 — ver Planejamento).

## Contextos

- [motor-workflow](./backend/docs/motor-workflow/CONTEXT.md) — motor de workflow
  local com plugins Python, mais seus pontos de entrada (CLI, HTTP) e observabilidade
  (execuções paralelas, monitoria, streaming)
- [frontend](./frontend/docs/CONTEXT.md) — painel de controle web (SPA) que consome
  a API HTTP/SSE do motor-workflow

## Relacionamentos

- `frontend` depende de `motor-workflow` (consome `GET/POST /runs*`, `GET /workflows`,
  `GET /workspace/repos`, SSE de `/stream`) — ADR-006 só adicionou `CORSMiddleware` ao
  lado `motor-workflow`; ADR-007 acrescenta 3 rotas novas (`/workflows`,
  `/workspace/repos`, `/runs/from-template`), consumidas pelo redesenho do disparo no
  `frontend`; ADR-009 acrescenta o parâmetro de consulta opcional `root` a
  `GET /workspace/repos` (aditivo, retrocompatível) e faz `LOCAL_REPOS_ROOT` virar
  fonte de default da raiz no `serve`; ADR-010 acrescenta o campo `plugin` por etapa em
  `GET /runs/{chain_name}` (aditivo, retrocompatível), consumido pelo `StreamPanel` para
  identificar a plataforma agêntica do step em execução; ADR-011 acrescenta o campo
  `archived` a `GET /runs`/`GET /runs/{chain_name}`, o parâmetro de consulta opcional
  `archived` a `GET /runs` e as rotas `POST /runs/{chain_name}/arquivar` e
  `.../desarquivar` (tudo aditivo, retrocompatível), consumidos pelo `RunsList`/
  `RunDetail` para arquivamento e atualização automática.

## Decisões (ADR)

Cada contexto mantém seu próprio diretório de ADRs, mas a **numeração é global e
sequencial entre eles** (não reinicia por contexto) — antes de criar uma ADR nova,
em qualquer contexto, confira o maior número já usado nos dois diretórios abaixo.

- [Registro de decisões — motor-workflow](./backend/adr/) — ADR-001 a ADR-005,
  ADR-007 e ADR-008, todas em `contextos: [motor-workflow]` (ADR-007 também
  `contextos: [..., frontend]`, `afeta: [frontend]`).
- [Registro de decisões — frontend](./frontend/adr/) — ADR-006, ADR-009, ADR-010 e
  ADR-011, todas `contextos: [frontend]`, `afeta: [motor-workflow]` (ADR-009
  `depende_de: [ADR-006, ADR-007]`; ADR-010 `depende_de: [ADR-005, ADR-006,
  ADR-007]`; ADR-011 `depende_de: [ADR-006, ADR-007, ADR-010]`) — próxima ADR nova,
  em qualquer contexto, é ADR-012.

Ver `<contexto>/adr/ADR-00N-*.md` para o front matter de relação
(`depende_de`/`afeta`/`supera`) de cada uma.

## Planejamento (to-be)

- **motor-workflow**: [specs](./backend/docs/specs/) — spec/plan/tasks por feature
  (harness SDD, `backend/AGENTS.md`), uma pasta por feature numerada (`001-...` a
  `006-...`, todas implementadas) e `007-implementar-local-pr-via-ci` (ADR-008, modo
  `coding_local` + ação `confirm_pr` — implementada e verificada de ponta a ponta
  contra `ai-lup-poc-target-cli` real, PR #8 aberta pela CI do repositório-alvo).
- **frontend**: harness SDD próprio criado (`frontend/AGENTS.md`,
  `frontend/constitution.md`, `frontend/init.sh`); [specs](./frontend/docs/specs/)
  — `docs/specs/006-frontend-painel-controle/{spec,plan,tasks}.md` (ADR-006,
  implementada), `docs/specs/007-selecao-template-execucao/{spec,plan,tasks}.md`
  (ADR-007, redesenho do disparo por template/repo local/specs remotas),
  `docs/specs/008-config-boot-runtime-pasta-trabalho/{spec,plan,tasks}.md` (ADR-009,
  defaults de boot via `painel-config.json` + pasta de trabalho trocável em runtime —
  implementada), `docs/specs/009-refinamentos-ux-stream-legivel/{spec,plan,tasks}.md`
  (ADR-010, alternador de tema reposicionado, seletor "Knowledge Bases" sobre
  `react-select` e stream ao vivo com leitura formatada por padrão + log bruto por
  opção; contrato novo do lado `motor-workflow` é pequeno o bastante para não abrir
  spec própria nesse contexto, documentado no `plan.md` desta feature) e
  `docs/specs/010-atualizacao-arquivamento-execucoes/{spec,plan,tasks}.md` (ADR-011,
  painel e detalhe de execuções atualizam sozinhos por polling enquanto há execução em
  andamento, mais arquivamento/desarquivamento reversível persistido no backend; mesmo
  padrão de contrato pequeno documentado no `plan.md`, sem spec própria em
  `motor-workflow`).
