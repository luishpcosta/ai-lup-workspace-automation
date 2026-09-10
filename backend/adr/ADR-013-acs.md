# Atividades e Acceptance Criteria — ADR-013

> Referência: `ADR-013-coding-local-interativo-ask-user.md`. Cada atividade
> pertence a um componente e tem 1+ AC vinculada.

## Componente: Servidor MCP ask_user (`backend/mcp_servers/ask_user_server.py`)

### Atividade ADR-013-AT-01: tool `ask_user(question, options?)`

- **Descrição**: Servidor stdio (`FastMCP`) com uma única tool. Lê
  `WORKSPACE_PATH`/`RUN_ID`/`STEP_NAME`/`ASK_USER_TIMEOUT_SECONDS` de variáveis de
  ambiente. Ao ser chamada: escreve `pergunta_path` (question/options/asked_at),
  limpa qualquer `resposta_path` remanescente de uma pergunta anterior, faz
  polling de `resposta_path` (~0.5s) até aparecer ou estourar o timeout; lê e
  apaga os dois arquivos ao final (respondida ou não).
- **Depende de**: nenhuma (arquivo novo, sem alteração em código existente).

**AC ADR-013-AC-01** (verificado manualmente, fora do pytest — ver nota abaixo)
```
Dado um processo `ask_user_server` com WORKSPACE_PATH/RUN_ID/STEP_NAME configurados
Quando `ask_user("Qual branch?", options=["feature/x","feature/y"])` é chamada e,
  ~0.5s depois, `resposta_path` é escrito com "feature/x"
Então a chamada devolve exatamente "feature/x"; `pergunta_path` e `resposta_path`
  não existem mais depois que a chamada retorna
```

**AC ADR-013-AC-02** (verificado manualmente, fora do pytest — ver nota abaixo)
```
Dado o mesmo cenário do AC-01, mas com ASK_USER_TIMEOUT_SECONDS baixo e nenhuma
  resposta escrita
Quando o timeout estoura
Então a chamada devolve um texto de fallback (contém "sem resposta"), instruindo o
  agente a prosseguir com seu melhor julgamento; `pergunta_path` não existe mais
```

> Nota: `mcp_servers/` não faz parte de `backend/src`/`backend/plugins` cobertos
> pela suíte `pytest` deste monorepo (é um processo `stdio` separado, invocado
> pelo próprio `claude`, não importado por nenhum módulo do motor) — AC-01/AC-02
> foram verificados chamando `ask_user()` diretamente num script isolado
> (import + simulação de resposta chegando / de timeout), não por um teste
> automatizado neste diretório. Candidato a `tests/test_ask_user_server.py`
> dedicado numa iteração futura, se o padrão de teste deste monorepo (pytest via
> `pythonpath`) for estendido para cobrir `mcp_servers/` também.

---

## Componente: Plugin Claude Code Runner (`backend/plugins/claude_code_runner.py`)

### Atividade ADR-013-AT-02: Modo `coding_local_interativo`

- **Descrição**: Mesmo shape de `coding_local` (ADR-008) — `workspace_path` de
  `context.input`/`context.params`, mesmo schema, mesmo prompt-base — mais
  `_build_interactive_mcp_config`, que mescla o MCP estático (`mcp_config_path`)
  com uma entrada `ask-user` (`command: sys.executable`, `args` apontando pro
  script por caminho absoluto, `env` com `WORKSPACE_PATH`/`RUN_ID`/`STEP_NAME`) e
  escreve o resultado em `<step>.mcp-config.json`.
- **Depende de**: ADR-013-AT-01 (o servidor que a entrada `ask-user` invoca).

**AC ADR-013-AC-03** — `tests/test_claude_code_runner_plugin.py::test_coding_local_interativo_mode_builds_merged_mcp_config_with_ask_user`
```
Dado um step `modo: coding_local_interativo` com `mcp_config_path` apontando para
  um JSON estático existente (ex.: docs-mcp-proxy)
Quando o plugin roda
Então `--mcp-config` recebido pelo `claude` aponta para
  `<workspace>/.workflow-logs/<run_id>/<step>.mcp-config.json`; esse arquivo
  contém tanto o server estático original quanto uma entrada `ask-user` com
  `env.WORKSPACE_PATH`/`RUN_ID`/`STEP_NAME` corretos e `args[0]` absoluto
  terminando em `ask_user_server.py`; o prompt enviado ao agente menciona
  `ask_user`
```

**AC ADR-013-AC-04** — `tests/test_claude_code_runner_plugin.py::test_coding_local_interativo_mode_without_static_mcp_config_file_still_gets_ask_user`
```
Dado `mcp_config_path` apontando para um arquivo que não existe no disco
Quando o plugin roda
Então o merge não falha — parte de `{"mcpServers": {}}` e o arquivo mesclado final
  contém só a entrada `ask-user`
```

**AC ADR-013-AC-05** — `tests/test_claude_code_runner_plugin.py::test_coding_local_interativo_mode_without_workspace_path_raises`
```
Dado `context.input`/`context.params` sem `workspace_path`
Quando o plugin roda
Então levanta `ValueError` mencionando `workspace_path`, nenhum processo `claude`
  é iniciado (mesmo contrato de `coding_local`, ADR-008-AC-02)
```

**AC ADR-013-AC-06** (regressão) — suíte completa de `test_claude_code_runner_plugin.py`
```
Dado os modos existentes `coding`, `review`, `investigar`, `coding_local`
Quando a suíte de testes do plugin roda após a mudança
Então nenhum teste existente desses quatro modos muda de comportamento ou quebra —
  `coding_local_interativo` é aditivo, sem alteração em `_run_coding_local`/
  `_coding_local_prompt`/`_build_cmd`
```

---

## Componente: API HTTP (`backend/src/workflow_engine/adapters/http_api.py`)

### Atividade ADR-013-AT-03: `POST /runs/{chain_name}/resposta`

- **Descrição**: Mesma resolução de `POST /instrucoes` (`_resolve_active_claude_step`),
  escreve (sobrescreve) `_resposta_path` com o corpo `{"resposta": "..."}`, 202.
- **Depende de**: nenhuma (endpoint novo, reaproveita resolução já existente da
  ADR-005).

**AC ADR-013-AC-07** — `tests/test_http_api_streaming.py::test_post_answer_writes_deterministic_resposta_file`
```
Dado uma etapa `claude_code_runner` `running` para um `chain_name`
Quando `POST /runs/{chain_name}/resposta` é chamado com `{"resposta": "..."}`
Então responde 202 `{chain_name, status: "accepted"}`; o arquivo
  `<workspace>/.workflow-logs/<run_id>/<step>.resposta.json` existe com o texto
  exato enviado
```

**AC ADR-013-AC-08** — `tests/test_http_api_streaming.py::test_post_answer_overwrites_previous_pending_answer`
```
Dado o mesmo cenário do AC-07
Quando `POST /resposta` é chamado duas vezes seguidas com textos diferentes
Então `resposta_path` contém só o texto da segunda chamada — sobrescreve, não
  acrescenta (no máximo uma pergunta pendente por vez, ADR-013-Decisão)
```

**AC ADR-013-AC-09** — `tests/test_http_api_streaming.py::test_post_answer_refuses_when_no_active_claude_step`
```
Dado nenhuma etapa `claude_code_runner` `running` para o `chain_name`
Quando `POST /resposta` é chamado
Então responde 409 `not_interactable` — mesmo código de erro já usado por
  `/instrucoes` (ADR-005-AC-09) para o mesmo cenário
```

### Atividade ADR-013-AT-04: Campo aditivo `awaiting_input`

- **Descrição**: `status == "running" and _pergunta_path(...).exists()`, calculado
  via `_resolve_active_claude_step` (reaproveitado) em `list_runs`/
  `get_run_detail`. Sem coluna nova no State Store.
- **Depende de**: ADR-013-AT-01/AT-02 (é a existência de `pergunta_path`, escrito
  pelo servidor MCP, que faz o campo virar `true`).

**AC ADR-013-AC-10** — `tests/test_http_api_streaming.py::test_awaiting_input_true_while_pergunta_file_exists_adr013`
```
Dado uma etapa `claude_code_runner` `running`
Quando `<step>.pergunta.json` é criado
Então tanto `GET /runs/{chain_name}["awaiting_input"]` quanto o item correspondente
  em `GET /runs` viram `true`; apagar o arquivo volta ambos para `false`
```

**AC ADR-013-AC-11** — `tests/test_http_api_streaming.py::test_awaiting_input_false_for_terminal_run_even_with_leftover_pergunta_file`
```
Dado um `<step>.pergunta.json` remanescente (ex.: de um crash) e a run já marcada
  como não-`running` (`workflow_runs.status` != "running")
Quando `GET /runs/{chain_name}` é chamado
Então `awaiting_input` é `false` — o guard `status == "running"` decide antes de
  qualquer checagem de arquivo, então um arquivo órfão nunca ressuscita o sinal
```

**AC ADR-013-AC-12** (regressão) — `tests/test_http_api.py::test_get_run_detail_includes_plugin_per_step_adr010_ac08`, `tests/test_http_api.py::test_get_run_detail_includes_archived_field_adr011_ac07`
```
Dado os campos já existentes de `GET /runs/{chain_name}` (`chain_name`, `run_id`,
  `status`, `created_at`, `updated_at`, `duration_seconds`, `steps`, `archived`)
Quando a resposta é inspecionada após esta mudança
Então todos continuam presentes, no mesmo formato — `awaiting_input` é o único
  campo novo (mesmo padrão aditivo de `plugin`/`archived`/`duration_seconds`,
  ADR-010/011/012)
```

---

## Componente: Templates de workflow (`backend/config/workflow_templates/`)

### Atividade ADR-013-AT-05: Template `claude-implementar-local-interativo`

- **Descrição**: Cópia de `claude-implementar-local.yaml` (ADR-008), só trocando
  `modo: coding_local` por `modo: coding_local_interativo` no step `implementar`;
  step `confirmar_pr` idêntico.
- **Depende de**: ADR-013-AT-02.

**AC ADR-013-AC-13** (mesmo mecanismo comprovado nas ADR-007-AC/ADR-008-AC-10 — sem teste dedicado neste monorepo, `FileSystemWorkflowTemplateRegistry` já é coberto por testes próprios que não precisam de um caso por template)
```
Dado o backend rodando com o template novo presente em
  `config/workflow_templates/`
Quando o usuário chama `GET /workflows`
Então "Implementar com Claude Code (interativo)" aparece na lista, com o mesmo
  `params_schema` de "Implementar com Claude Code" — sem nenhuma mudança em
  `GET /workflows` em si
```

**AC ADR-013-AC-14** (regressão)
```
Dado o template existente `claude-implementar-local`
Quando `GET /workflows` é chamado após a mudança
Então ele continua aparecendo com o mesmo `params_schema` de antes — o arquivo não
  foi alterado
```

---

## Componente: Frontend — `StreamPanel.jsx` (`frontend/src/components/StreamPanel.jsx`)

### Atividade ADR-013-AT-06: Deriva `pendingQuestion` do stream

- **Descrição**: `findPendingQuestion(turns)` procura o turno `tool` mais recente
  com `name === 'ask_user' && status === 'running'` (já produzido genericamente
  por `claudeStream.js`, ADR-010, sem mudança nele) e extrai
  `{text, options}` de `turn.input`. Repassa via prop `onPendingQuestion` (efeito
  reativo a `pendingQuestion`, mais um efeito de desmontagem que reporta `null`).
- **Depende de**: nenhuma (usa o parser existente sem alteração).

**AC ADR-013-AC-15** — `StreamPanel.test.jsx::"reports a pending ask_user tool call (still running) via onPendingQuestion"`
```
Dado um evento `assistant`/`tool_use` com `name: "ask_user"` chega pelo stream,
  sem `tool_result` ainda
Quando `StreamPanel` processa o stream
Então `onPendingQuestion` é chamado com `{text: <question>, options: <options>}`
```

**AC ADR-013-AC-16** — `StreamPanel.test.jsx::"reports null once the ask_user call resolves (tool_result arrives)"`
```
Dado o cenário do AC-15, seguido de um evento `user`/`tool_result` para o mesmo
  `tool_use_id`
Quando `StreamPanel` processa a linha nova
Então `onPendingQuestion` é chamado novamente com `null`
```

**AC ADR-013-AC-17** — `StreamPanel.test.jsx::"reports null on unmount, so a new run never inherits a stale question"`
```
Dado uma pergunta pendente ativa
Quando o componente desmonta (troca de execução — `RunDetail` remonta via `key`)
Então `onPendingQuestion` é chamado com `null` antes de desmontar
```

---

## Componente: Frontend — `InstructionBox.jsx` (`frontend/src/components/InstructionBox.jsx`)

### Atividade ADR-013-AT-07: Modo pergunta/resposta

- **Descrição**: Novo prop `pendingQuestion`. Sem ele, formulário idêntico ao de
  hoje (`postInstruction`). Com ele: mostra o texto da pergunta; `options` não
  vazio vira um botão por opção (clique já envia); sem `options`, campo de texto
  rotulado "Resposta"; em ambos os casos, envia via `postAnswer`
  (`POST .../resposta`), nunca `postInstruction`.
- **Depende de**: ADR-013-AT-06 (quem fornece `pendingQuestion`).

**AC ADR-013-AC-18** — `InstructionBox.test.jsx::"shows the agent question and sends a free-text answer via postAnswer, not postInstruction"`
```
Dado `pendingQuestion={text: "...", options: []}`
Quando o usuário digita uma resposta e envia
Então `postAnswer(chainName, resposta)` é chamado, `postInstruction` não é chamado,
  "Resposta enviada." aparece
```

**AC ADR-013-AC-19** — `InstructionBox.test.jsx::"renders one button per option and sends the clicked option as the answer"`
```
Dado `pendingQuestion={text: "...", options: ["A", "B"]}`
Quando o usuário clica no botão "B"
Então `postAnswer(chainName, "B")` é chamado imediatamente — sem campo de texto
  livre visível
```

**AC ADR-013-AC-20** — `InstructionBox.test.jsx::"shows a clear error on 409 not_interactable when answering, without crashing"`
```
Dado `postAnswer` rejeita com `ApiError{code: "not_interactable"}`
Quando o usuário envia uma resposta
Então a mensagem de erro aparece via `role="alert"`, sem quebrar a tela
```

**AC ADR-013-AC-21** (regressão) — `InstructionBox.test.jsx::"sends the typed message to postInstruction and confirms delivery"` (teste pré-existente, sem alteração)
```
Dado nenhum `pendingQuestion` (prop ausente/null)
Quando a suíte de testes do componente roda após a mudança
Então o formulário de instrução livre continua se comportando exatamente como
  antes — mesmo label, mesmo botão, mesmo `postInstruction`
```

---

## Componente: Frontend — `RunsList.jsx` (`frontend/src/components/RunsList.jsx`)

### Atividade ADR-013-AT-08: Destaque passivo para run aguardando resposta

- **Descrição**: Linha ganha a classe `run-row-awaiting` e um badge
  "❓ Aguardando resposta" quando `run.awaiting_input` é `true` — mesmo padrão
  visual passivo já usado para `run-row-failed` (ADR-006-AC-12).
- **Depende de**: ADR-013-AT-04 (`awaiting_input` vindo de `GET /runs`).

**AC ADR-013-AC-22** — `RunsList.test.jsx::"highlights a run whose agent is waiting for an answer, passively, like a failed run"`
```
Dado um item de `GET /runs` com `awaiting_input: true`
Quando a lista é renderizada
Então a linha tem a classe `run-row-awaiting` e o texto "Aguardando resposta"
  aparece
```

**AC ADR-013-AC-23** — `RunsList.test.jsx::"shows no badge for a running run that is not awaiting input"`
```
Dado um item `running` com `awaiting_input: false`
Quando a lista é renderizada
Então nem a classe `run-row-awaiting` nem o badge aparecem
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-013 | AT-01 | AC-01, AC-02 | Servidor MCP ask_user | Concluído (verificação manual fora do pytest — ver nota) |
| RF-02 | ADR-013 | AT-02 | AC-03, AC-04, AC-05, AC-06 | Claude Code Runner | Concluído |
| RF-03 | ADR-013 | AT-03 | AC-07, AC-08, AC-09 | API HTTP | Concluído |
| RF-04 | ADR-013 | AT-05 | AC-13, AC-14 | Templates de workflow | Concluído (AC-13 sem teste dedicado, mesmo mecanismo já coberto pela ADR-007/ADR-008) |
| RF-05 | ADR-013 | AT-04 | AC-10, AC-11, AC-12 | API HTTP | Concluído |
| RF-06 | ADR-013 | AT-06, AT-07 | AC-15, AC-16, AC-17, AC-18, AC-19, AC-20, AC-21, AC-27 | StreamPanel, InstructionBox | Concluído (AC-27: bug crítico de reconhecimento de nome, encontrado no primeiro teste manual real e corrigido) |
| RF-07 | ADR-013 | AT-08 | AC-22, AC-23 | RunsList | Concluído |
| RNF-01 | ADR-013 | AT-02, AT-05 | AC-06, AC-14 | Claude Code Runner, Templates de workflow | Concluído |
| RNF-02 (herdado) | ADR-013 | AT-02 | AC-06 | Claude Code Runner | Concluído |
| RNF-03 (herdado) | ADR-013 | AT-01, AT-03 | AC-07, AC-27 | Servidor MCP ask_user, API HTTP | Concluído — verificado por execução real de ponta a ponta contra `ai-lup-poc-target-cli` (ver AC-27): pausa, resposta pelo painel, segunda pergunta, conclusão dos dois steps |

> **Verificado manualmente, de ponta a ponta** (2026-09-10), com a CLI `claude`
> real e o repositório-alvo real `ai-lup-poc-target-cli`: disparado "Implementar
> com Claude Code (interativo)"; o agente chamou `ask_user` (duas vezes, em
> sequência); a primeira tentativa expôs um bug real na UI (ver AC-27) — depois
> de corrigido ao vivo, a pergunta passou a aparecer corretamente no painel
> (`RunsList` com o badge de "Aguardando resposta" e `InstructionBox` como
> formulário de resposta); a resposta enviada pelo painel voltou para o agente
> (confirmado pelo log real da sessão) e a run concluiu normalmente (`implementar`
> + `confirmar_pr`, ambos `completed`).

## Correções decorrentes de revisão de código (pós-implementação inicial)

Uma revisão de correção (`code-review`, nível `high`) sobre o diff completo desta
ADR encontrou 4 pontos; os 3 abaixo eram bugs/riscos reais e foram corrigidos —
cada um ganhou teste de regressão próprio, listado junto. O quarto (nit de
performance em `get_run_detail`, ver ADR-013-AC-26) também foi corrigido.

## Correção decorrente do primeiro teste manual real (ponta a ponta)

**ADR-013-AC-27** (bug crítico — quebrava a feature inteira) — `frontend/src/components/StreamPanel.jsx` (`isAskUserTool`), `StreamPanel.test.jsx::"reports a pending ask_user tool call via onPendingQuestion using the real namespaced tool name"` / `"also recognizes the bare ask_user name..."`
```
Bug encontrado (usuário, teste manual real contra claude-implementar-local-interativo,
  repo ai-lup-poc-target-cli): a pergunta do agente nunca virava o formulário de
  resposta — aparecia como card de tool genérico, com o JSON cru do `input` e sem
  nenhum jeito de responder pelo painel. O usuário ficou com o agente preso
  esperando, mesmo mandando uma instrução livre pelo `InstructionBox` (retida sem
  efeito, ver AC-25 — o canal certo, `/resposta`, nunca foi alcançado porque o
  formulário certo nunca apareceu).
Causa raiz: `findPendingQuestion` comparava `turn.name === 'ask_user'`, mas o
  `claude` CLI reporta uma tool call MCP com o nome namespaced
  `mcp__<server>__<tool>` — verificado ao vivo no log real da sessão:
  `"name":"mcp__ask-user__ask_user"`, nunca o `ask_user` puro que o próprio
  servidor declara. A comparação exata nunca casava, então `pendingQuestion`
  ficava sempre `null`.
Correção: `isAskUserTool(name)` casa tanto o nome puro (`ask_user`) quanto
  qualquer nome terminado em `__ask_user` (cobre o namespace `mcp__ask-user__`
  independente da chave de server usada em `_build_interactive_mcp_config`).
Destravado manualmente enquanto a correção ainda não tinha subido: as duas
  perguntas pendentes da run real presa (`claude-implementar-local-interativo--
  6c931751`) foram respondidas diretamente via `POST /runs/{chain_name}/resposta`
  — a run concluiu (`implementar` + `confirmar_pr`, PR já existente confirmada),
  provando que o mecanismo de pausa/retomada real (backend) sempre funcionou; o
  bug era só a UI não reconhecer a pergunta para oferecer o formulário.
```

**Isso também resolve a pendência de verificação manual de ponta a ponta**
(ver nota em RNF-03/AC-13, abaixo) — a execução real contra `ai-lup-poc-target-cli`
confirmou: pergunta aparece (depois da correção), resposta pelo painel de fato
destrava o agente, o agente faz uma segunda pergunta de acompanhamento (prova de
que múltiplas perguntas sequenciais na mesma run funcionam), e a run conclui os
dois steps (`implementar` + `confirmar_pr`) normalmente.

**ADR-013-AC-24** (correção de bug) — `frontend/src/components/InstructionBox.jsx`, `InstructionBox.test.jsx::"does not leak..."` (2 testes)
```
Bug encontrado: `status`/`errorMessage` eram estado único, compartilhado entre o
  modo pergunta e o modo instrução — uma confirmação de um modo podia aparecer no
  outro logo depois de `pendingQuestion` mudar de valor (ex.: responder uma
  pergunta e, quando ela resolve, ver "Instrução enviada." sem ter enviado
  instrução nenhuma).
Correção: estado separado por modo (`answerStatus`/`answerError` vs
  `instructionStatus`/`instructionError`) — cada formulário só lê/escreve o seu.
Verificado: dois testes de regressão cobrindo as duas direções da troca de modo.
```

**ADR-013-AC-25** (mitigação de risco) — `backend/plugins/claude_code_runner.py` (`_poll_instructions`/`_run_streaming_session`), `test_claude_code_runner_plugin.py::"holds instruction while ask_user pending..."` / `"never forwards instruction while ask_user stays pending"`
```
Risco encontrado: `_poll_instructions` continuava encaminhando linhas novas de
  `.instrucoes.jsonl` para o stdin do `claude` mesmo com uma tool call `ask_user`
  pendente (sem `tool_result` ainda) — injetar uma mensagem de usuário nessa
  janela é comportamento não verificado do CLI (diferente de "dirigir um turno em
  andamento", que a ADR-005 verificou ao vivo).
Mitigação: `_poll_instructions` passa a receber `pergunta_path` (só no modo
  `coding_local_interativo`) e segura (não descarta) qualquer instrução nova
  enquanto esse arquivo existir, encaminhando assim que a pergunta resolver.
Verificado: instrução é retida durante a pergunta e encaminhada depois que ela é
  resolvida; nunca encaminhada se a pergunta nunca resolve dentro da sessão.
```

**ADR-013-AC-26** (correção de bug + eficiência) — `backend/plugins/claude_code_runner.py::_build_interactive_mcp_config`, `test_claude_code_runner_plugin.py::"rejects non-object..."` / `"rejects malformed json..."`; e `backend/src/workflow_engine/adapters/http_api.py::get_run_detail`, `test_http_api_streaming.py::"loads chain yaml only once..."`
```
Bug encontrado (mcp config): um `mcp_config_path` estático existente mas com JSON
  inválido, ou JSON válido que não é um objeto (ex.: uma lista), causava
  `json.JSONDecodeError`/`AttributeError` não tratado três frames dentro do
  plugin, em vez de um erro claro.
Correção: valida explicitamente (JSON parseável + é um objeto) e levanta
  `ValueError` com mensagem clara nos dois casos.

Nit de eficiência (get_run_detail): a rota recarregava a YAML da chain duas vezes
  por requisição contra uma execução `running` (uma vez para `plugin` por etapa,
  outra dentro de `_is_awaiting_input`/`_resolve_active_claude_step`), mais uma
  consulta redundante a `workflow_runs`/`step_executions` que a própria função já
  tinha acabado de fazer.
Correção: `_claude_step_workspace_path` extraído como função pura, reaproveitada
  por `_resolve_active_claude_step` (inalterado externamente) e por
  `get_run_detail` (que agora carrega a YAML e resolve a etapa `running` uma
  única vez, sem round-trip adicional).
Verificado: teste que conta chamadas reais a `YamlJsonChainLoader.load` durante
  `GET /runs/{chain_name}` contra uma execução `running` — exatamente 1.
```

## Tabela de rastreabilidade — correções

| Achado (revisão) | AC | Componente | Status |
|---|---|---|---|
| Status compartilhado entre modos (InstructionBox) | AC-24 | InstructionBox | Corrigido |
| Instrução encaminhada durante pergunta pendente | AC-25 | Claude Code Runner | Mitigado |
| mcp_config_path malformado quebra sem mensagem clara | AC-26 | Claude Code Runner | Corrigido |
| YAML recarregada duas vezes em get_run_detail | AC-26 | API HTTP | Corrigido |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em
> andamento / Concluído / Bloqueado).
