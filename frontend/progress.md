# Session Progress Log

## Current State

**Last Updated:** 2026-09-07
**Active Feature:** 011-tempo-execucao-tabela — Tempo de execução na tabela de execuções — Verify, `done`
**Active SDD Phase:** Verify
**Pending Gate:** Nenhum. Todas as 7 ACs (AC-01 a AC-07) implementadas e verificadas — ver `docs/specs/011-tempo-execucao-tabela/tasks.md`.

## Sessão 2026-09-07 — ADR-012 (contexto `frontend`, `afeta: [motor-workflow]`): tempo de execução na tabela

Usuário perguntou, em chat, se já seria possível trazer o "tempo de execução" de cada
workflow para a tabela de execuções do painel, a partir do dado que já existe na base
(sem PRD, sem skill de elicitação formal — ver ADR-012, Contexto). Duas explorações
(backend e frontend) confirmaram que sim: `created_at`/`updated_at` por execução já
são persistidos no `.db` SQLite por chain e já lidos por `list_runs`/`get_run_detail`
em `http_api.py`, mas nunca subtraídos nem expostos como duração.

`duration_seconds` (inteiro, segundos, ou `null`) passou a ser calculado inline em
`http_api.py`, reaproveitando os timestamps já desempacotados — sem nova coluna, sem
novo modelo Pydantic. Regra: status terminal usa `updated_at - created_at` (fixo);
`running`/`pending` usa `now() - created_at` (recalculado a cada request, já que
`updated_at` fica parado no último step concluído enquanto a execução está ativa).
Timestamp ausente/corrompido degrada para `null` em vez de erro — mesma postura
defensiva de `_step_plugins_by_name` (ADR-010). `RunsList.jsx` ganhou uma coluna
"Duração" entre "Status" e "Atualizado", formatada por um novo `formatDuration()` em
`lib/format.js` (`"45s"`/`"2min 14s"`/`"1h 03min"`) — **sem nenhum polling novo**: a
coluna só se beneficia do `setTimeout` recursivo que `RunsList` já roda enquanto há
execução ativa (ADR-011-AT-04).

**Decisão de escopo registrada, não decidida sozinha**: duração por etapa em
`RunDetail` ficou fora desta feature — usuário pediu especificamente "a tabela"
(listagem); o dado (`started_at`/`finished_at` por step) já é exposto pela API hoje,
então uma extensão futura não exige mudança de contrato adicional (ver ADR-012,
Alternativas consideradas).

`103/103 testes do frontend` (2 novos: `RunsList.test.jsx`, describe
`RunsList — tempo de execução (ADR-012-AC-06)` — era 101 antes desta feature).
`135/135 testes do backend` (3 novos em `test_http_api.py`: run terminado com
timestamps fixados direto no `.db` via `UPDATE` para valor exato sem flakiness, run
`running` mantido ativo via o padrão já existente de blocking plugin para confirmar
não-decrescimento, timestamp corrompido para confirmar degradação graciosa — era 132
antes). `npm run lint`/`npm run build`/`ruff check`/`ruff format` limpos.

**Verificado num navegador real, não só em teste unitário**: `workflow serve` real
(porta 8000) + `vite` dev server real (porta 5173) já em execução, reiniciados após a
mudança. As 4 execuções reais já existentes no `watch_dir` mostraram a coluna
"Duração" com valores batendo exatamente com `updated_at - created_at` (ex.: 415s →
"6min 55s", 277s → "4min 37s"). Uma execução nova, real (`shell_script_runner` com
`sleep 20`, sem mock, `duration-smoke-test`), disparada diretamente no mesmo
`watch_dir` do backend em execução, apareceu como "Em execução" com "13s" logo após o
disparo e — sem nenhum clique em "Atualizar" — avançou sozinha para "Concluído" com
"20s" fixo, confirmando o cálculo `now() - created_at` durante a execução, o valor
fixo ao terminar, e que a coluna se beneficia do polling já existente da ADR-011 sem
nenhum mecanismo novo. `.db` de teste removido após a verificação.

## Sessão 2026-09-07 — ADR-011 (contexto `frontend`, `afeta: [motor-workflow]`): atualização automática + arquivamento

Três atritos relatados pelo usuário em conversa (elicitado via skill `issue-to-adr`,
sem PRD — ver ADR-011, Contexto):

1. Ao disparar uma execução, o painel de execuções só refletia o progresso real via
   clique manual em "Atualizar".
2. A tela de detalhe buscava as etapas uma única vez ao entrar — o botão "Atualizar"
   ali só reconectava o stream ao vivo, nunca refazia a busca do detalhe, então a
   tabela de etapas ficava parada mesmo com a execução avançando de verdade.
3. Painel acumulava execuções concluídas/antigas sem forma de tirá-las de vista.

**Duas decisões arquiteturais levadas ao usuário antes de codar, não decididas
sozinho** (elicitação, 1 rodada, 2 perguntas fechadas): (a) o estado de "arquivada"
persiste no **backend** (não `localStorage`) — decisão explícita do usuário, precisa
sobreviver a troca de navegador/dispositivo; (b) arquivar é **reversível** — filtro
"Arquivadas" + ação de desarquivar, nunca uma exclusão disfarçada. Ver ADR-011,
Alternativas consideradas.

`archived_at` (nullable) persiste no mesmo `.db` SQLite por chain, lido/escrito
direto via `sqlite3` em `http_api.py` — mesmo padrão de desacoplamento já usado por
`list_runs`/`get_run_detail` (ADR-004), fora do `StateStorePort`. Migração aditiva
(`ALTER TABLE ... ADD COLUMN`, idempotente) roda sob demanda, cobrindo `.db` antigos
e novos sem script de migração separado. Duas rotas novas
(`POST /runs/{chain_name}/arquivar`/`.../desarquivar`, idempotentes, mesmo contrato
de erro 404 de `cancelar`); `GET /runs` ganha `?archived=true` (default: exclui
arquivadas, comportamento de hoje preservado); `GET /runs/{chain_name}` ganha
`archived` (aditivo).

`RunsList`/`RunDetail` passam a reconsultar `GET /runs`/`GET /runs/{chain_name}`
sozinhos via `setTimeout` recursivo (não `setInterval` fixo — um `setInterval`
decidiria se reagenda com o estado de uma rodada atrás, ainda não atualizado no
instante em que o efeito roda; o `setTimeout` decide com o dado que acabou de
chegar), enquanto houver algo `running`/`pending`; para sozinho quando não há mais
nada ativo. `RunsList` ganhou um card "Arquivadas" na `summary-strip` (troca a
própria consulta para `?archived=true`, não filtra em memória) e um botão
"Arquivar"/"Desarquivar" por linha; `RunDetail` ganhou a mesma ação no cabeçalho.
`StreamPanel` não mudou — continua com seu próprio SSE por step, independente deste
polling.

`101/101 testes do frontend` (12 novos: `apiClient.test.js` +4, `RunsList.test.jsx`
+4, `RunDetail.test.jsx` +4 — era 93 antes desta feature, com fake timers para as
ACs de polling). `132/132 testes do backend` (5 novos em `test_http_api.py` — era
127 antes). `npm run lint`/`npm run build`/`ruff check`/`ruff format` limpos.

**Verificado num navegador real, não só em teste unitário**: `workflow serve` real
(porta 8123) + `vite` dev server real (porta 5183) rodando simultaneamente, com uma
chain real de 2 etapas (`shell_script_runner` com `sleep`, sem mock) disparada via
`curl`. Painel avançou de "Em execução" para "Concluído" sozinho, sem nenhum clique
em "Atualizar"; tela de detalhe aberta durante a execução avançou "passo-2 Em
execução" → ambas as etapas "Concluído" sozinha, com o botão "Cancelar" sumindo ao
virar terminal; arquivar pelo detalhe (vira "Desarquivar", detalhe continua
acessível), arquivar pela listagem (some da lista padrão), aba "Arquivadas" (mostra
só a arquivada) e desarquivar (volta para a listagem padrão) — todos confirmados
visualmente de ponta a ponta, com screenshots do fluxo completo.

## Sessão 2026-09-07 — ADR-010 (contexto `frontend`, `afeta: [motor-workflow]`): tema, Knowledge Bases, stream legível

Três atritos relatados pelo usuário em conversa (elicitado via skill `issue-to-adr`,
sem PRD — ver ADR-010, Contexto):

1. `ThemeToggle` intercalado entre os botões de ação da topbar em vez de separado
   deles.
2. `SpecPicker` era uma lista de checkboxes rotulada "Specs de referência" — o usuário
   pediu explicitamente o padrão `react-select` (combobox em barra, multi-seleção,
   busca) rotulado **"Knowledge Bases"** (exemplo de código fornecido na própria
   demanda).
3. `StreamPanel` mostrava o `stream-json` bruto do `claude` CLI linha a linha; pedido
   para identificar a plataforma agêntica do step e, por padrão, privilegiar leitura
   (texto + rastros de ferramenta), com o log bruto disponível por opção.

**Decisão de escopo registrada, não decidida sozinho**: a renomeação para "Knowledge
Bases" troca só o rótulo visível (label do template YAML + textos do picker) —
`docs_referenced`, `spec_multiselect` e o nome do arquivo `SpecPicker.jsx` continuam
como estavam, sem ganho funcional em renomear identificadores internos agora (ADR-010,
Contexto — Assunções registradas).

`SpecPicker.jsx` foi reescrito sobre `react-select` (`unstyled`, estilizado 100% via
`classNamePrefix="select"` contra os tokens já existentes em `index.css` — sem adotar
o tema padrão da lib nem um design system externo). `GET /runs/{chain_name}` ganhou o
campo aditivo `plugin` por item de `steps[]` (`get_run_detail`, `http_api.py`),
resolvido do YAML da chain via `config_path` já persistido — mesma técnica que
`_resolve_active_claude_step` (ADR-005) já usava para decidir se um step é
"streamável", só que agora exposta na resposta em vez de só uma decisão interna.
`lib/claudeStream.js` (novo) interpreta as linhas `stream-json` do `claude` CLI em
turnos (texto/tool/summary), com fallback `raw` por linha não reconhecida — nunca
lança. `StreamPanel.jsx` escolhe o formatador por um registro `{plugin: formatter}`;
hoje só `claude_code_runner` tem entrada — sem formatador, ou linha não reconhecida,
cai no `<pre>` de log bruto que já existia, preservado como alternância explícita
("Ver log bruto"/"Ver leitura formatada"), nunca removido.

`89/89 testes do frontend` (14 novos: `claudeStream.test.js` com 8 testes,
`StreamPanel.test.jsx` +4, `SpecPicker.test.jsx` reescrito com 5 testes — era 75
antes desta feature). `127/127 testes do backend` (2 novos:
`test_get_run_detail_includes_plugin_per_step_adr010_ac08`,
`test_get_run_detail_plugin_is_null_when_config_missing_adr010_ac08` — era 125
antes). `npm run lint`/`npm run build`/`ruff check` limpos.

**Verificado num navegador real, não só em teste unitário**: `workflow serve` real
(porta 8123) + `vite` dev server real (porta 5183) rodando simultaneamente — o
alternador de tema aparece à direita dos botões com divisor visual (claro e escuro);
`GET /workflows` real confirmou `"label":"Knowledge Bases"`; o combobox `react-select`
abre, busca, seleciona/remove múltiplos itens e é excluído da lista de opções ao ser
selecionado (`fetch` de `docs-index.json` mockado no navegador para exercitar o caso
com dados, já que não há um repositório de specs remoto real disponível neste
ambiente); um run concluído (sem step `running`) confirmou que `StreamPanel` sem
`plugin` se comporta exatamente como antes desta feature (regressão zero).

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

Feature 011 (ADR-012) está completa e verificada — ver a sessão mais recente no topo
deste arquivo para detalhes (coluna "Duração" em `RunsList`, `duration_seconds`
derivado em tempo de leitura, sem instrumentação nova). Se uma nova demanda aparecer,
a próxima ADR (em qualquer contexto) é `ADR-013` (numeração global, ver
`../CONTEXT-MAP.md`). Ponto explicitamente fora de escopo em ADR-012: duração por
etapa na tela de detalhe (`RunDetail`) — o dado (`started_at`/`finished_at` por step)
já é exposto pela API hoje, pronto para uma extensão futura sem mudança de contrato
adicional. Pontos anteriores ainda em aberto: da ADR-011, arquivamento em lote e
exclusão definitiva de execução seguem fora de escopo; da ADR-010, suporte a qualquer
plataforma agêntica além de `claude_code_runner` segue fora de escopo — o registro de
formatadores em `StreamPanel.jsx` já está pronto para receber uma entrada nova sem
redesenho. O rename pendente de `historia_id` (ADR-006, Consequências) segue em
aberto, sem prazo definido.
