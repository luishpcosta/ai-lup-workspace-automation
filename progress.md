# Session Progress Log

## Current State

**Last Updated:** 2026-09-04
**Active Feature:** 005-stream-interacao-agente - Streaming ao vivo + interação com o agente — Verify, `done`
**Pending Gate:** Nenhum. Todas as 5 ADRs (001-005) implementadas, testadas e verificadas. Nenhuma próxima feature especificada ainda.

**Features anteriores, todas Verify/`done`**:
- 004-api-http-monitoria (`workflow serve`) — `POST /runs`, `GET /runs`(`/{chain_name}`), `POST /runs/{chain_name}/cancelar`.
- 003-execucoes-paralelas-independentes (`workflow run-many`) — `ThreadPoolExecutor`, State Store isolado por `chain_name`.
- 002-plugins-poc-pipeline-sdd — incluindo um teste real ponta a ponta completo (3 PRs reais mescladas em `github.com/luishpcosta/ai-lup-poc-target-cli`, 3 bugs reais achados/corrigidos) — ver seção "Execução real completa" abaixo.
- 001-motor-workflow-plugins — núcleo do motor.

## Sessão 2026-09-04 (4) — ADR-005: streaming ao vivo + interação real com o agente

Implementação da feature mais arriscada desta sequência: reescrita do
`plugins/claude_code_runner.py` (já em produção, PR real mesclada na `002`) de
`subprocess.run` bloqueante para `Popen` de longa duração com
`--input-format/--output-format stream-json`.

**Verificação real feita ANTES de codificar** (não depois):
1. `--json-schema` combinado com `--output-format stream-json`, ao vivo: achado
   real — a CLI usa uma tool call interna (`StructuredOutput`), e o evento final
   `type:"result"` traz um campo novo `structured_output` (já um dict parseado),
   além do `result` (string, como no modo sem streaming). `_extract_structured`
   prefere o campo novo.
2. Uma segunda mensagem escrita no stdin **enquanto a primeira ainda está sendo
   processada** de fato interrompe/redireciona o agente — testado direto na CLI
   ("conte até 5" interrompido por "pare, responda X") e **depois, de novo,
   através do plugin reescrito de verdade** (script real, ver abaixo).

**Implementação** (`plugins/claude_code_runner.py` reescrito + 2 endpoints novos em
`http_api.py`): `session_log_path` agora escrito incrementalmente; arquivo irmão
`<step>.instrucoes.jsonl` observado por uma thread de polling que repassa linhas
novas pro stdin do processo vivo; `GET /runs/{chain_name}/stream` (SSE, tail do log)
e `POST /runs/{chain_name}/instrucoes` (append no arquivo) em `http_api.py`,
resolvendo a etapa ativa só via `.db`+YAML — sem depender de `ServerState`, então
funciona igual pra execuções do terminal (requisito NFR-1, testado explicitamente:
todos os testes de streaming semeiam o run via `SqliteStateStore` direto, nunca via
`ServerState.trigger`).

**Smoke-test manual real** (não só fakes): rodei o plugin reescrito de verdade
(sem mocks — `Popen` real, `claude` real) contra um repositório git descartável
(sem remoto, pra garantir que nenhum `git push` real pudesse acontecer) e o
servidor MCP real de `samples/docs-site`. Escrevi uma instrução de interrupção real
no arquivo `.instrucoes.jsonl` 4 segundos depois de iniciar — **o `summary` final
retornado pelo plugin foi literalmente "PAROU"**, a palavra exata pedida na
instrução, confirmando que o mecanismo funciona de ponta a ponta através do código
real, não só do fake de teste. Nenhuma mudança indevida no repositório descartável
(`git log` continua só com o commit inicial).

**1 teste removido por ser redundante/perigoso**: uma tentativa inicial de testar
AC-10 abrindo um SSE stream sem nunca completar a etapa **travou o pytest** (o
`TestClient`/ASGI transport do FastAPI espera o generator terminar antes de devolver
controle do `with client.stream(...)`) — matei o processo manualmente e removi o
teste, já que AC-10 já estava coberto pelos testes de AC-06/AC-08 (que já semeiam o
run sem passar por `ServerState`).

`85/85 testes passando` (8 no plugin reescrito, 4 nos endpoints novos). `init.sh`
limpo.

## Sessão 2026-09-04 (3) — ADR-004: API HTTP e monitoria (workflow serve)

Nova demanda informal ("quero outras portas de entrada como http e endpoints de
monitoria... conectar via stream no runner... até interagir se necessário"),
elicitada via skill `issue-to-adr`. Escopo dividido em duas ADRs a pedido do usuário:

- **ADR-004** (`adr/ADR-004-api-http-monitoria.md` + acs, 4 atividades, 10+1 ACs) —
  implementada nesta sessão. Novo comando `workflow serve`, reaproveita
  `WorkflowEngine`/plugins/State Store exatamente como `run-many`. **Requisito chave do
  usuário**: monitoria precisa enxergar execuções disparadas por terminal OU API —
  resolvido com uma convenção de "diretório observado" (`--watch-dir`), sem qualquer
  acoplamento entre quem dispara e quem lê (leitura via `sqlite3` direto nos `.db`,
  sem passar pelo `StateStorePort`).
- **ADR-005** (`adr/ADR-005-stream-interacao-agente.md` + acs, 5 atividades, 10 ACs) —
  **só desenhada, não implementada ainda**. Streaming ao vivo + interação em tempo
  real com o agente. Verificado **ao vivo** nesta sessão (não suposição): `claude -p
  --input-format stream-json --output-format stream-json --verbose
  --permission-mode bypassPermissions` aceita uma instrução nova pelo stdin
  **enquanto já está processando** — testado mandando "conte de 1 a 5" e, no meio,
  "pare, responda X"; o agente mudou de direção de verdade. Mecanismo desenhado:
  arquivos (não memória) — `session_log_path` escrito incrementalmente +
  `<step>.instrucoes.jsonl` — porque o requisito de "ver ambos" também vale pro
  streaming (um `workflow run` no terminal é outro processo do SO).

### Implementação real da ADR-004 (specs/004-api-http-monitoria, T-1 a T-4, `done`)

`src/workflow_engine/adapters/http_api.py` (novo) + extensão pontual de `cli.py`
(subparser `serve`). 11 testes novos (`tests/test_http_api.py`), suíte completa **77
passed**. **Escopo revisado ao desenhar a implementação** (registrado na própria
ADR-004, não escondido): cancelamento de uma etapa **já em execução** não é suportado
— `subprocess.run` dentro de cada plugin é bloqueante e nunca expõe o `Popen` pra quem
chama, então não há handle pra matar de verdade; `/cancelar` só cancela o que ainda
está na fila (`Future.cancel()`, garantido pela stdlib) e responde 409 honesto pro
resto, em vez de fingir que cancelou.

**2 bugs reais achados pelos testes** (não hipotéticos — apareceram rodando):
1. `YamlJsonChainLoader` (herdado da `001`) nunca checava se o arquivo do config
   existe — `workflow run <inexistente>` quebrava com `FileNotFoundError` cru em vez
   de erro limpo. Corrigido na fonte (`_read_raw`/`load`), beneficia `run`/`run-many`/
   `serve` igualmente. Teste de regressão em `test_yaml_json_chain_loader.py`.
2. FastAPI aninha `HTTPException.detail` sob a chave `"detail"` por padrão — quebrava
   o contrato documentado (`{"error": {"code","message"}}` plano). Corrigido com um
   `@app.exception_handler(HTTPException)` customizado.

**Smoke-test manual real** (não só `TestClient`): subiu `workflow serve` de verdade
(`uvicorn`), bateu com `curl` real em todos os 4 endpoints — `POST /runs` (202,
assíncrono), `GET /runs` (lista agregada do watch-dir), `GET /runs/{chain_name}`
(com e sem `?include=io`, output do plugin aparece corretamente parseado como JSON),
`POST /runs/{x}/cancelar` (404 para desconhecido). Confirma que o `uvicorn.run()`
real funciona, não só o `TestClient` in-process.

### Trabalho de infraestrutura desta sessão (fora do fluxo SDD normal, a pedido do usuário)

- **Git inicializado na raiz do repo** (não existia antes) — commit inicial de 114
  arquivos, `.gitignore` cobrindo estado gerado (`workspaces/`, `run-many-state/`,
  `*.db`, logs ad-hoc) e excluindo `samples/target-cli/` (repo git próprio, já
  publicado separadamente).
- **Repositório remoto criado**: `github.com/luishpcosta/ai-lup-workspace-automation`
  (privado), push do commit inicial.
- **`CONTEXT-MAP.md` criado** (não existia) + `docs/motor-workflow/CONTEXT.md` —
  contexto único do repo, registrando as 5 ADRs (001-005) no grafo de dependências da
  skill `blueprintfy`. **Bug real achado e corrigido nas 5 ADRs**: o comentário HTML
  de instrução de front matter (que a própria skill `issue-to-adr` manda colocar
  antes do `---`) quebrava o parser real do `graph_query.py`, que exige `---` na
  primeira linha do arquivo — movido o comentário para depois do front matter em
  todas as 5 ADRs, validado rodando a ferramenta de verdade (`vigentes`/`impacto`
  funcionando corretamente agora).

## Sessão 2026-09-04 (2) — ADR-003: execuções paralelas independentes

Nova demanda informal ("permitir execuções paralelo... histórias que sei que não se
cruzam... repos diferentes, MS diferentes"), elicitada via skill `issue-to-adr`:
- `adr/ADR-003-execucoes-paralelas-independentes.md` + `adr/ADR-003-acs.md` (4
  atividades, 10 ACs) — decisão: novo comando `workflow run-many`, `ThreadPoolExecutor`
  (plugins liberam o GIL via `subprocess`, sem precisar de `multiprocessing`), um
  arquivo SQLite isolado por execução do lote (nomeado por `chain.name`), sem detecção
  automática de conflito (responsabilidade do usuário), sem parar o lote inteiro se uma
  falhar. **Único componente afetado: `adapters/cli.py`** — zero mudança em
  `domain/`/`application/`/plugins existentes.
- `specs/003-execucoes-paralelas-independentes/{spec,plan,tasks}.md` escritos a partir
  da ADR-003 — gate de cobertura fechado (AC-01 a AC-10 cobertas por T-1 a T-4).
- **Nenhum código escrito ainda** — próxima sessão começa pela T-1.

## Sessão 2026-09-04 — Infraestrutura de teste real (samples/)

A pedido do usuário ("crie uma pasta de samples ... quero teste real"), construída
infraestrutura real (não simulada) para rodar o pipeline da ADR-002 ponta a ponta:

- **`samples/docs-site/`** — site Docusaurus real com `docusaurus-plugin-mcp-server`
  (baseado em https://github.com/scalvert/docusaurus-plugin-mcp-server, SKILL.md
  verificado via WebFetch), populado com 11 páginas reais (PB/PRD/ADR/AC/Histórias)
  derivadas de `~/developer/ai-tools/ai-lup-skills/specs/{001,002,003}-cli-*` (specs
  reais do CLI `lup-skills`) + nossas próprias ADR-001/ADR-002 como exemplos de ADR.
  `npm run build` gera `build/mcp/{docs,search-index,manifest}.json`;
  `scripts/mcp-server.mjs` sobe um servidor HTTP real (`createNodeServer`) em
  `http://localhost:3456`.
- **`samples/target-cli/`** — o CLI `lup-skills` **recriado como repositório git local
  real** (código copiado sem `node_modules`/`.git`, `git init` + commit inicial; 36/36
  testes reais passando como baseline), mais um workflow real de CI
  (`.github/workflows/ci.yml`) e o script de polling
  (`scripts/poll_ci_checks.sh`, usa `gh pr checks --watch --fail-fast` — verificado
  contra `gh pr checks --help` real).
- **`samples/docs-site/docs/historias/historia-004-list-json.md`** — uma História
  **nova e não implementada** (`list --json`), criada especificamente como alvo real
  para o teste ponta a ponta (as histórias 001-003 já estavam implementadas no CLI
  real, não serviam de alvo).
- **`config/mcp-docusaurus.json`** — config MCP real (`--mcp-config` da ADR-002),
  `type: http`, `url: http://localhost:3456`.
- **`samples/hist-004-list-json.yaml`** — cadeia real (5 etapas) apontando pros
  caminhos absolutos acima, pronta para `workflow run`.

### Verificação real feita nesta sessão (não simulada)

- Servidor MCP local: `initialize`, `tools/list` e `tools/call` (`docs_search`) via
  `curl` puro — resposta correta, encontrou HIST-004 como top result.
- **`claude -p` real conectando no MCP via `--mcp-config`**: primeira tentativa com
  `--permission-mode acceptEdits --permission-prompts none` **falhou de verdade**
  (`permission_denials` não vazio — nega chamada de ferramenta MCP, só pré-aprova
  edição de arquivo). Corrigido para `--permission-mode bypassPermissions`, testado de
  novo, `permission_denials: []`, resposta correta (`"HIST-004: list --json — .../
  historia-004-list-json"`).
- **Envelope JSON de `--output-format json --json-schema ...` confirmado ao vivo**:
  `result` é uma string JSON escapada (`{"result": "{\"summary\": ...}", ...}`), não
  um objeto aninhado — exatamente o que `_parse_result` já esperava.
- Gap achado e corrigido: **nada no pipeline fazia `git commit`/`git push`** — prompt
  do modo `coding` (`claude_code_runner.py::_coding_prompt`) agora instrui
  explicitamente commit + push antes de retornar.
- Gap achado e corrigido: `shell_script_runner.py` não passava `cwd` — script relativo
  (`./scripts/poll_ci_checks.sh`) resolveria a partir do processo da automação, não do
  workspace clonado. Corrigido (`cwd = context.input["workspace_path"]`), com teste
  novo (`test_runs_inside_workspace_path_from_input`).
- `plugins/claude_code_runner.py`, `adr/ADR-002-plugins-poc-pipeline-sdd.md` e
  `specs/002-.../tasks.md` (T-3/T-6) atualizados com essas correções. `./init.sh`
  continua limpo depois de tudo isso.

### O que falta para o teste real ficar 100% completo

`samples/target-cli` hoje **não tem remoto `origin`** — é um repo git só local. Sem um
remoto GitHub real, `git push` (instruído no prompt) e `gh pr create` (etapa
`abrir_pr`) vão falhar. Isso é uma decisão do usuário, não algo a assumir sozinho:
criar um repositório novo no GitHub (via `gh repo create`) é uma ação visível,
vinculada à conta do usuário — perguntado diretamente antes de fazer isso (ver
pergunta feita ao usuário nesta sessão).

Servidor MCP local (`node scripts/mcp-server.mjs`, porta 3456) ficou rodando em
background ao final desta sessão — precisa estar no ar para qualquer nova tentativa de
`workflow run samples/hist-004-list-json.yaml`; se não estiver, resubir com
`cd samples/docs-site && npm run build && node scripts/mcp-server.mjs`.

## Execução real completa (2026-09-04) — PR #1 em ai-lup-poc-target-cli

Usuário confirmou criar um repositório GitHub novo e privado para o teste (autorizado
explicitamente, não decidido sozinho). `gh repo create ai-lup-poc-target-cli --private
--source=. --push` a partir de `samples/target-cli`.

`workflow run samples/hist-004-list-json.yaml` rodado de verdade, 3 tentativas até
passar (retomando do ponto de falha, sem repetir etapas já concluídas — RF-4 da
ADR-001 funcionando como projetado):

1ª tentativa: `preparar_ambiente` ✅ (clone real + `npm install`, 5min) →
`implementar_historia` ✅ (sessão real do `claude`, 1min40s, editou
`index.js`/`src/commands/list.js`/`test/list.test.js`) → `abrir_pr` ❌ (`gh pr create
--label automated-pr` falhou: label não existia no repo novo).

2ª tentativa (retomada): `abrir_pr` ❌ de novo — motivo diferente: título da PR
(`{{ summary }}` do agente, 1007 caracteres) excedeu o limite de 256 do GitHub
(`GraphQL: Title is too long`).

3ª tentativa (retomada): **PR #1 aberta com sucesso**
(https://github.com/luishpcosta/ai-lup-poc-target-cli/pull/1) → `aguardar_checks` ✅
(mas com bug real descoberto depois, ver abaixo) → `revisar_pr` ✅ (segunda sessão real
do `claude`, 1min40s, janela de contexto nova).

**3 bugs reais encontrados e corrigidos** (nenhum coberto pelos testes unitários
existentes, porque dependiam de integração real):
1. `git_pr.py`: título de PR sem limite de tamanho → `_truncate_title` (256 chars,
   defensivo) + teste `test_title_over_256_chars_is_truncated`.
2. `poll_ci_checks.sh` (em `samples/target-cli`, não no motor): `gh pr checks --watch`
   só espera checks que **já existem** — chamado logo após abrir a PR (antes de a CI
   registrar o check), retornou `exit_code 1` com "no checks reported" **imediatamente**,
   sem esperar. Como o `shell_script_runner` nunca trata `exit_code` não-zero como
   falha (contrato documentado — AC-09..11), a cadeia seguiu pra revisão mesmo assim.
   A CI real passou minutos depois por sorte de timing, não porque o pipeline
   verificou isso de verdade. Corrigido o script pra esperar o primeiro check aparecer
   antes de usar `--watch`. **Limitação arquitetural registrada na ADR-002**
   (Consequências/Riscos): a Engine não trava/ramifica com base em `output` de uma
   etapa, só em exceção — fora de escopo resolver isso agora.
3. `mcp-server.log` commitado sem querer no `target-cli` (resíduo de um erro de `cd`
   meu no início da sessão) — removido com commit de limpeza.

Estado final real, tudo verificado via `gh`/API do GitHub, não assumido:
- PR #1 aberta, label `automated-pr`, corpo referenciando HIST-004/ADR-002/AC/HIST-001,
  1 commit real (`c42e2e6`, autor `luishpcosta` via `gh` auth), 3 arquivos alterados.
- CI real (`gh pr checks 1`): `test pass 59s`, run
  https://github.com/luishpcosta/ai-lup-poc-target-cli/actions/runs/33830094552.
- Exatamente 1 PR, sem duplicatas.

### Conteúdo real da revisão (lido e conferido)

`revisar_pr.log` mostra uma revisão de verdade, não um rubber-stamp: usou a skill
`code-review` de verdade, analisou os 3 arquivos do diff, não achou bug de correção, e
encontrou um problema real de qualidade (lógica de array-vazio-em-JSON duplicada em 3
lugares em `src/commands/list.js`, com sugestão concreta de simplificação). Não foi
postado como comentário na PR (a ADR-002 não pedia isso — `summary` só fica no
`session_log_path` e no output da etapa).

### Pendências

- O repositório `ai-lup-poc-target-cli` é throwaway — decidir com o usuário quando
  apagá-lo (`gh repo delete`) depois que o teste tiver servido seu propósito.

## Status

### What's Done

- [x] Demanda elicitada e registrada em `adr/ADR-001-motor-workflow-plugins.md` e `adr/ADR-001-acs.md` (via skill `issue-to-adr`)
- [x] Harness SDD escaffoldado (`AGENTS.md`, `constitution.md`, `init.sh`, `progress.md`)
- [x] `specs/001-motor-workflow-plugins/{spec,plan,tasks}.md` escritos a partir do ADR-001
- [x] Núcleo do motor implementado e depois **refatorado para arquitetura hexagonal** em `src/workflow_engine/`: `domain/` (models, exceptions, ports — `Plugin`, `PluginRegistryPort`, `StateStorePort`, `EventLoggerPort`, `ChainLoaderPort`), `application/` (`RetryHandler`, `WorkflowEngine` — dependem só de `domain`), `adapters/` (`FileSystemPluginRegistry`, `SqliteStateStore`, `YamlJsonChainLoader`, `JsonEventLogger`, `cli.py` como composition root), mais `plugin_sdk.py` como fachada pública para autores de plugin
- [x] `pyproject.toml` (src-layout, `pip install -e ".[dev]"`, entry point `workflow` → `workflow_engine.adapters.cli:main`)
- [x] Style/lint decidido: **Ruff** (lint + format), config em `pyproject.toml`

- [x] Feature `002-plugins-poc-pipeline-sdd` elicitada e registrada em `adr/ADR-002-plugins-poc-pipeline-sdd.md` e `adr/ADR-002-acs.md` (via skill `issue-to-adr`, com verificação real contra a CLI do Claude Code instalada — `claude 2.1.260` — e contra o schema real já implementado do `YamlJsonChainLoader`/`RetryPolicy`)
- [x] `specs/002-plugins-poc-pipeline-sdd/{spec,plan,tasks}.md` escritos a partir da ADR-002 — gate de cobertura fechado (AC-01 a AC-20 cobertas por T-1 a T-7)
- [x] **T-1 a T-7 implementadas e verificadas**:
  - T-1: `YamlJsonChainLoader` estendido com bloco `vars:` + interpolação `{{ vars.<chave> }}` (retrocompatível — sem `vars:`, comportamento idêntico à `001`)
  - T-2: `plugins/workspace_setup.py` — clone/checkout, `workspace_path`/`base_commit_sha` determinísticos, docker compose opcional (`TransientError` na falha)
  - T-3/T-6: `plugins/claude_code_runner.py` — modos `coding`/`review` via CLI real (`claude 2.1.260`), `session_log_path` determinístico escrito mesmo em falha, `docs_referenced` extraído via `--json-schema`
  - T-4: `plugins/git_pr.py` — criação/atualização de PR via `gh` CLI real (`gh 2.97.0`), validação obrigatória de rastreabilidade antes de criar (bloqueia sem chamar `gh`)
  - T-5: `plugins/shell_script_runner.py` — execução com timeout, `context.input` exposto como env vars `WORKFLOW_INPUT_*`
  - T-7: `application/workflow_engine.py` (`_log`/`_correlation`) + `adapters/cli.py` (`--correlation-keys`) — não o `JsonEventLogger` (ver Decisions Made)
- [x] `examples/implementar-historia-sdd.yaml` criado; smoke-test manual (registry+loader reais, sem mocks) confirma descoberta dos 4 plugins e resolução de `vars:` ponta a ponta
- [x] `python -m pytest -q` → **57 passed** | `python -m compileall .` → exit 0 | `ruff check .` → All checks passed | `ruff format --check .` → 61 files already formatted (`./init.sh` limpo)

### What's In Progress

- [ ] Nenhuma tarefa em implementação no momento. Features `001` e `002` estão ambas em Verify/`done`.

### What's Next

1. Execução real ponta a ponta (não coberta nesta sessão): rodar `workflow run examples/implementar-historia-sdd.yaml` contra um repositório-alvo e servidor MCP reais, com `gh`/`git`/`docker`/`claude` de verdade — a suíte de testes cobre cada plugin isoladamente com `run_command` injetado (fake), nunca os binários reais em conjunto.
2. Confirmar a forma exata do envelope JSON que `claude -p --output-format json --json-schema ...` retorna (ver caveat no docstring de `plugins/claude_code_runner.py::_parse_result`) — só `claude --help` foi verificado nesta sessão, não uma invocação real.
3. Próxima feature ainda não definida — aguardando o usuário.

## Open Clarifications

Nenhuma bloqueante. Assunções registradas (não bloqueantes):
- Volume/escala assumido baixo/individual — ver `adr/ADR-001-motor-workflow-plugins.md`, seção Contexto.
- Seleção automática da "próxima história pendente" fica fora de escopo de `002` — ver `adr/ADR-002-plugins-poc-pipeline-sdd.md`, seção Contexto.

## Blockers / Risks

- [ ] Convenção de plugin (`run(context)->output`, `TransientError`, arquivo com `PLUGIN`/`PLUGIN_NAME`) precisa ser adotada consistentemente por todo plugin futuro — documentada em `src/workflow_engine/adapters/filesystem_plugin_registry.py` (docstring) e no ADR.
- [ ] Fronteira hexagonal (`domain` → `application` → `adapters`, uma via) não é verificada automaticamente — hoje depende de checagem manual (grep). Ruff não checa isso; se crescer, vale um lint rule dedicado (ex. import-linter) para travar isso em CI.
- [ ] (`002`) `gh` CLI e Docker precisam estar instalados/autenticados no ambiente onde os plugins rodam de verdade — fora do controle do motor. `gh`/`claude` foram verificados quanto a **flags** nesta sessão, mas nenhum dos dois foi invocado de fato com efeito real (nenhuma PR criada, nenhum clone real).
- [ ] (`002`) A forma exata do envelope JSON de `claude --output-format json --json-schema ...` não foi confirmada por uma execução real — `_parse_result` em `claude_code_runner.py` trata duas formas plausíveis defensivamente, mas isso precisa validação contra uma chamada real antes de considerar T-3/T-6 prontas para uso em produção (a suíte de testes usa um envelope fake, coerente com a suposição, não com uma resposta real capturada).
- [ ] (`002`) Erros de `git`/`install_cmd` no `workspace_setup` são tratados como falha permanente por padrão (simplificação deliberada — só a falha do `docker compose` é `TransientError`, por ser o único caso coberto por AC formal); distinguir rede transitória de erro de config exigiria parsing de stderr não coberto por nenhuma AC.

## Decisions Made

- **Escopo da feature 001**: todo o ADR-001 tratado como uma única feature SDD.
  - Context: usuário confirmou manter como um ADR só com 9 atividades.
  - Constitution impact: nenhuma emenda necessária.
- **Convenção concreta de descoberta de plugin**: cada arquivo `*.py` no diretório de plugins expõe `PLUGIN` (classe) e opcionalmente `PLUGIN_NAME`.
  - Context: decidida durante a implementação do núcleo por ser a forma mais simples de satisfazer AC-06/AC-07.
- **Formato da cadeia**: YAML (`.yaml`/`.yml`) e JSON (`.json`), decidido pela extensão do arquivo.
- **Refatoração para arquitetura hexagonal**: `domain/`/`application/`/`adapters/`, sem alterar comportamento.
  - Context: pedido explícito do usuário ("Refatore aplique hexagonal").
- **Ferramenta de lint/format: Ruff**.

- **Escopo da feature 002**: as 7 atividades da ADR-002 tratadas como uma única feature SDD, espelhando `001`.
  - Constitution impact: nenhuma — a extensão do Chain Loader não muda o contrato de Plugin (princípio 5 continua satisfeito).
- **Plugins novos ficam em `./plugins/` (fora de `src/`)**: adapters externos, descobertos pela `FileSystemPluginRegistry` já existente.
- **Correlação de auditoria (T-7) implementada em `WorkflowEngine`/`cli.py`, não em `JsonEventLogger`**.
  - Context: descoberto ao ler o código real durante a implementação — `JsonEventLogger` já repassa qualquer `**extra` recebido para o JSON de saída (via `record.__dict__`), então não havia nada para "estender" ali. Quem decide **quais campos** virar `correlacao` é `WorkflowEngine._correlation()`, parametrizado por um `correlation_keys: frozenset[str]` injetado — a Engine (genérica, da `001`) nunca tem os nomes `historia_id`/`pr_number` hardcoded; é `cli.py` (composition root, flag `--correlation-keys`, default `historia_id,branch,pr_number,pr_url`) quem decide isso, mantendo a Engine agnóstica de plugin.
  - Constitution impact: nenhuma — Data Model de `001` não muda; a extensão respeita a fronteira hexagonal (decisão de política fica no composition root).
- **`workdir` do Claude Code Runner não é um `param`**: lido de `context.input["workspace_path"]` em ambos os modos.
  - Context: a ADR-002 original listava `workdir` como `param` obrigatório em texto, mas o YAML de exemplo (mais concreto) nunca o declarava — corrigido na ADR antes de implementar, para a spec não divergir do código.
- **Carry-forward estendido ao modo `coding` do Claude Code Runner** (não só Git/PR e Shell/Script Runner, como a ADR original documentava).
  - Context: sem isso, `workspace_path` não tinha como chegar à etapa de revisão (2 hops adiante) — gap real encontrado ao desenhar o fluxo de dados antes de codificar; ADR-002 corrigida para refletir isso.
- **Flags reais do `gh` CLI verificadas** (`gh 2.97.0`): `create` usa `--label`, `edit` usa `--add-label` — não intercambiáveis. Corpo da PR sempre via `--body-file` (arquivo temporário), nunca `--body` inline.
- **Template rendering do Git/PR é um substituidor simples de `{{ campo }}`, não Jinja2**: lista vira string com `", ".join(...)` automaticamente.
  - Context: o YAML original da ADR usava sintaxe de filtro Jinja (`| join(', ')`), que não seria suportada por um substituidor simples — corrigido no exemplo antes de implementar, para não exigir uma dependência de templating só para o POC.
- **Erros de `git`/`install_cmd` no Workspace Setup tratados como falha permanente** (só `docker compose` é `TransientError`).
  - Context: distinguir falha de rede transitória de erro de configuração permanente (ex. branch inexistente) exigiria parsing frágil de stderr; nenhuma AC formal exige essa distinção além do caso do Docker — decisão tomada durante a implementação para não construir heurística não testada.

## Evidence of Completion

- [x] AC-01 a AC-15 (feature `001`) verificadas: `specs/001-motor-workflow-plugins/tasks.md`
- [x] AC-01 a AC-20 (feature `002`) verificadas: `specs/002-plugins-poc-pipeline-sdd/tasks.md` — evidência por tarefa (T-1 a T-7), todas `done`
- [x] `python -m pytest -q` → **57 passed** (2026-09-03) — inclui as 34 de `001` + 23 novas/estendidas de `002`
- [x] `python -m compileall .` → exit 0; `ruff check .` → All checks passed; `ruff format --check .` → 61 files already formatted
- [x] Coverage check clean em ambas as features: toda AC referenciada por ≥1 task, toda task referencia ≥1 AC
- [x] Smoke-test manual (`002`): `examples/implementar-historia-sdd.yaml` carregado com `FileSystemPluginRegistry`/`YamlJsonChainLoader` reais — 4 plugins descobertos, `vars:` resolvido corretamente

## Notes for Next Session

Features `001` e `002` estão ambas completas (fase Verify, `done`, `./init.sh` limpo). Os 4 plugins de POC (`workspace_setup`, `claude_code_runner`, `git_pr`, `shell_script_runner`) estão implementados e testados unitariamente (subprocess sempre injetado/fake — nenhum teste chama `git`/`gh`/`claude`/`docker` de verdade), mais um exemplo de cadeia completa em `examples/implementar-historia-sdd.yaml`. O que falta, explicitamente fora do escopo desta sessão: (1) uma execução real ponta a ponta contra um repositório/PR/servidor MCP verdadeiros, e (2) confirmar contra uma chamada real a forma exata do envelope JSON do `claude --output-format json --json-schema`. Nenhuma nova feature foi especificada ainda — a próxima sessão deve perguntar ao usuário o que vem a seguir (ex.: rodar o POC de verdade, ou uma nova ADR/feature).
