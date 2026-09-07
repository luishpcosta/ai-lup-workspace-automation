# Session Progress Log

## Current State

**Last Updated:** 2026-09-06
**Active Feature:** 008-config-boot-runtime-pasta-trabalho — Configuração de boot em runtime e pasta de trabalho — Verify, `done`
**Active SDD Phase:** Verify
**Pending Gate:** Nenhum. Todas as 8 ACs (AC-01 a AC-08) implementadas e verificadas — ver `docs/specs/008-config-boot-runtime-pasta-trabalho/tasks.md`.

## Sessão 2026-09-06 — ADR-009 (contexto `frontend`, `afeta: [motor-workflow]`): config de boot + pasta de trabalho

Pedido do usuário durante uma sessão de retoque visual do painel: instalação nova exige
digitar as duas URLs à mão sempre, os campos da tela de configuração usavam
**placeholder com valor real** (lido como se já estivesse preenchido), e a raiz de
repositórios locais só existia como flag de linha de comando — sem ela, o seletor de
repositórios ficava vazio sem forma de corrigir a não ser resubir o backend.

**Conflito de constituição levantado antes de codar, não contornado**: a alternativa
óbvia para os defaults (`.env` do Vite) viola o princípio 6 (`import.meta.env` é
assado no bundle); a alternativa óbvia para a raiz trocável (rota `PUT` nova) esbarra
no princípio 5 (rota nova exige ADR). As duas decisões foram levadas ao usuário antes
da implementação (ver ADR-009, Alternativas consideradas).

`lib/config.js` ganhou uma segunda fonte de valores (`public/painel-config.json`,
arquivo estático lido por `fetch` no boot, nunca `import.meta.env`) com precedência
`localStorage` > arquivo > vazio, **campo a campo** — salvar só o `baseUrl` não apaga o
default do `specsBaseUrl`. `SettingsScreen.jsx` foi redesenhada: selo "default do
arquivo" por campo, zero `placeholder`, campo novo de pasta de trabalho, botão
"Restaurar defaults do arquivo". No motor, `GET /workspace/repos` ganhou `?root=`
opcional (aditivo, retrocompatível — é filtro de leitura, não estado do processo) e
`--local-repos-root` passou a ter `LOCAL_REPOS_ROOT` como fonte de default.

Investigação que mudou o desenho: `local_repos_root` só é lido por
`GET /workspace/repos` — não é estado do motor (o disparo usa o `repo_path` completo
recebido por parâmetro). Isso é o que permitiu resolver a troca por parâmetro de
consulta em vez de uma rota de escrita com estado mutável no servidor.

`75/75 testes do frontend` (14 novos: `config.test.js` ganhou uma segunda `describe`
com 7 testes de AC-01 a AC-05, `apiClient.test.js` +2, `SettingsScreen.test.jsx` +5 —
era 61 antes desta feature). `125/125 testes do backend` (5 novos:
`test_http_api_templates.py` +4 para AC-06/AC-07, `test_http_api.py` +1 para AC-08 —
era 120 antes). `npm run lint`/`ruff` limpos.

**Verificado de ponta a ponta, não só em teste unitário**: backend real subido com
`LOCAL_REPOS_ROOT` no ambiente (sem flag) confirmou o seletor populado; troca da pasta
de trabalho pela tela, com o backend já rodando, confirmou o seletor trocando de árvore
via `?root=` sem reiniciar nada; reload da página confirmou a raiz persistida.

## Sessão 2026-09-06 — ADR-007 (contexto `motor-workflow`, `afeta: [frontend]`): disparo por template

Redesenho pedido pelo usuário: o disparo deixa de ser um texto livre resolvido por
convenção de nome de arquivo (`configDir`/`resolveConfigPath.js`, ADR-006) e passa a
ser por **workflow (template)** — o backend expõe `GET /workflows` com o schema de
parâmetros de cada um, e o formulário de disparo (`TriggerForm.jsx`) se monta
dinamicamente a partir disso (`DynamicParamsForm.jsx`), sem hardcode de nenhum
template específico. Dois componentes novos resolvem os dois tipos de campo "fonte
externa": `RepoPicker.jsx` (repositórios locais, `GET /workspace/repos`) e
`SpecPicker.jsx` (specs remotas, fetch **direto do browser** em
`${specsBaseUrl}/docs-index.json` — decisão do usuário, sem proxy no backend; novo
`lib/specsClient.js`, deliberadamente fora de `apiClient.js` por falar com uma origem
diferente do backend do motor).

`configDir` saiu da `SettingsScreen`/`config.js`, substituído por `specsBaseUrl`;
`resolveConfigPath.js` e seu teste foram removidos (órfãos — nada mais resolvia
ID→path). `createRun(configPath)` também saiu de `apiClient.js` (sem chamador),
substituído por `createRunFromTemplate(templateId, params)`.
`RunsList`/`RunDetail`/`StreamPanel`/`InstructionBox`/`App.jsx` **não mudaram** —
`onDispatched`/`refreshToken` continuam exatamente como estavam.

**Decisão de escopo registrada, não decidida sozinho**: o disparo em lote (múltiplos
IDs num único envio, ADR-006 RF-03) sai de escopo nesta reformulação — params agora são
estruturados (repositório + prompt + specs), não uma lista plana; repetir o envio do
formulário cobre o caso de uso. Ver `docs/specs/007-selecao-template-execucao/spec.md`,
Non-Goals.

`61/61 testes passando` (21 novos: `config.test.js`/`apiClient.test.js` atualizados,
`specsClient.test.js`, `TemplateSelector.test.jsx`, `RepoPicker.test.jsx`,
`SpecPicker.test.jsx`, `DynamicParamsForm.test.jsx`, `TriggerForm.test.jsx`
reescrito — era 40 antes desta feature). `npm run build`/`npm run lint` limpos.
**Não verificado ainda nesta sessão**: fluxo real num navegador (mesma limitação já
registrada na feature `006` — sem Playwright neste ambiente).

## Status

### What's Done

- [x] Harness SDD criado (`AGENTS.md`, `constitution.md`, `init.sh`, este `progress.md`)
- [x] ADR-006 (com achados de entrevista de UX) movida para `adr/`
- [x] `docs/specs/006-frontend-painel-controle/{spec,plan,tasks}.md` escritas a partir da ADR-006, gate de cobertura fechado (13 ACs, 12 tasks)
- [x] Scaffold real: React 19 + Vite 5 (JS), Vitest + Testing Library, ESLint 9
  (trocado de oxlint/Vite 8 padrão do `create-vite` — binários nativos
  `rolldown`/`oxlint` não carregam no Node 20.17 desta máquina; downgrade
  documentado, não escondido — ver Decisions Made)
- [x] `lib/config.js`, `lib/resolveConfigPath.js`, `lib/apiClient.js` (erro tipado
  conexão/HTTP; `openStream` via `fetch`+`ReadableStream`, não `EventSource`, para
  distinguir 409 de 200)
- [x] `SettingsScreen`, `RunsList` (destaque visual de falha), `RunDetail`
  (tabela por etapa + cancelar), `TriggerForm` (disparo em lote por ID de
  documento de referência), `StreamPanel`, `InstructionBox`
- [x] `CORSMiddleware` em `backend/.../http_api.py::build_app` (única mudança de
  backend; 2 testes de regressão novos, `backend/tests/test_http_api.py`)
- [x] 40/40 testes do frontend passando, `npm run lint`/`npm run build` limpos
- [x] 87/87 testes do backend passando (inclui as 2 novas AC-11), `ruff` limpo
- [x] **Verificação real** (não só mocks): `workflow serve` real (porta 8010) +
  `vite` dev server real (porta 5183) rodando simultaneamente; `curl` com header
  `Origin` real confirmou `access-control-allow-origin: *` e preflight `OPTIONS`
  real confirmou `access-control-allow-methods: GET, POST` — CORS funciona de
  ponta a ponta, não é só suposição de que o middleware está certo

### What's In Progress

- [ ] Nenhuma — feature completa

### What's Next

Nenhuma feature nova especificada ainda. Possível próximo passo (não pedido
ainda): executar o rename pendente de `historia_id` (registrado como decisão
pendente na ADR-006, atravessa vocabulário de ADR-001/002 no backend).

## Open Clarifications

Nenhuma pendente e bloqueante.

## Blockers / Risks

- [ ] Testes desta feature não cobrem um navegador real (sem Playwright neste
  ambiente) — só unidade/integração com `fetch`/stream mockados. A parte que
  não podia ser mockada com confiança (CORS real) foi verificada com processos
  reais (ver acima); o que fica sem cobertura automática é só a interação
  visual (layout, destaque CSS).
- [ ] `npm audit` reporta 5 vulnerabilidades (3 moderate, 1 high, 1 critical) —
  todas do mesmo problema conhecido do `esbuild` do Vite 5 (dev server aceita
  requisição de qualquer site enquanto roda localmente, GHSA-67mh-4wv8-2f99).
  Afeta só o dev server local, não o build de produção. Aceito nesta versão
  (mesma postura de "uso local/individual, sem auth" já decidida na ADR-006);
  revisitar ao considerar Vite 6+ quando o Node desta máquina for atualizado.

## Decisions Made

- **Vite 8 (`rolldown`) e `oxlint` trocados por Vite 5 e ESLint 9**: description
  — o `create-vite` padrão instalou Vite 8 + `oxlint`, ambos com binário nativo
  que não carrega no Node 20.17.0 desta máquina (`EBADENGINE`, requer
  `^20.19.0 || >=22.12.0`). Vite 5 + ESLint 9 (`^18.18.0 || ^20.9.0`) funcionam
  de verdade nesta máquina — testado (`npm run build`/`npm run lint` reais).
  - Context: descoberto ao rodar `npm run build` pela primeira vez (erro real
    de módulo nativo ausente, não suposição).
  - Constitution impact: `constitution.md` já reflete React 19 + Vite 5 +
    Vitest + ESLint como stack real (não mais "a definir").
- **Disparo em lote atualiza a listagem, não navega automaticamente para
  detalhe**: com vários IDs disparados de uma vez, não há "o" item para
  navegar — `TriggerForm` chama `onDispatched()` ao final do lote, que só
  força um refresh de `RunsList`. Corrigido também o texto de `spec.md`
  AC-06, que ainda dizia "leva ao detalhe" (divergência da própria ADR-006-acs.md).

## Evidence of Completion

- [x] AC-01 a AC-13 verificadas: `docs/specs/006-frontend-painel-controle/tasks.md`
  (T-1 a T-12, todas `done`, evidência por tarefa)
- [x] Coverage check limpo: toda AC tem ≥1 task e toda task referencia uma AC
- [x] `npm test` → 40 passed; `npm run build` → ok; `npm run lint` → limpo
- [x] `python -m pytest` (backend) → 87 passed; `ruff check`/`format` → limpos
- [x] Verificação real ponta a ponta (processos reais, não `TestClient`/mock) —
  ver "What's Done" acima

## Notes for Next Session

Feature 006 está completa e verificada. Se uma nova demanda de frontend
aparecer, a próxima ADR (em qualquer contexto) é `ADR-007` (numeração global,
ver `../CONTEXT-MAP.md`). O rename pendente de `historia_id` (ADR-006,
Consequências) segue em aberto, sem prazo definido.
