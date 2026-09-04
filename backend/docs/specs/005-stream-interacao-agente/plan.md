# Plan: Streaming ao Vivo e Interação com o Agente (Claude Code Runner)

**Feature ID:** 005-stream-interacao-agente
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-04

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Reescrita interna de `plugins/claude_code_runner.py` (ADR-002): `subprocess.run`
bloqueante vira `Popen` de longa duração, usando `--input-format stream-json
--output-format stream-json --verbose` (verificado ao vivo contra `claude 2.1.260`,
incluindo a composição com `--json-schema`). O contrato externo do plugin
(`params`/`output`, `TransientError`) não muda — só a implementação de invocação.

Dois arquivos novos por etapa do Claude Code Runner, ambos em caminho determinístico
(mesma convenção de `session_log_path`, ADR-002): o log em si (agora escrito
incrementalmente) e um arquivo de instruções que uma thread do plugin faz polling
enquanto a sessão está ativa. `adapters/http_api.py` (feature `004`) ganha dois
endpoints que tailam/apendam esses mesmos arquivos — mecanismo por arquivo, não por
estado em memória, é o que garante NFR-1 (funciona igual pra execuções do terminal).

Decisão completa, diagrama e verificação ao vivo em
`adr/ADR-005-stream-interacao-agente.md`.

## Architecture & Components

**`plugins/claude_code_runner.py`** (reescrito internamente):
- `__init__` troca `run_command` (injeção de `subprocess.run`) por `popen_factory`
  (injeção de `subprocess.Popen`) — mudança de assinatura registrada, não escondida.
- `_run_streaming_session`: abre o processo com stdin/stdout conectados, manda a
  primeira mensagem (prompt) via stdin (não mais como argumento posicional — o modo
  `--input-format stream-json` lê a conversa inteira do stdin), lê linha a linha
  escrevendo cada uma em `session_log_path` incrementalmente, fecha o stdin assim que
  vê o evento `type:"result"` da rodada atual (uma sessão stream-json não se encerra
  sozinha depois de um turno — verificado ao vivo).
- `_poll_instructions` (thread separada, daemon): observa
  `<step_name>.instrucoes.jsonl` por conteúdo novo (delta desde a última leitura, não
  só a última linha — evita perder duas instruções que cheguem entre dois ciclos de
  poll) e repassa cada linha nova como mensagem de usuário pro stdin do processo vivo.
- `_extract_structured`: prefere o campo `structured_output` (já um dict, achado ao
  verificar `--json-schema` + `stream-json` ao vivo) sobre `result` (string JSON,
  fallback).
- `_raise_if_failed`: `returncode != 0` com padrão conhecido no texto agregado vira
  `TransientError` (mesma heurística da ADR-002); `returncode == 0` mas o evento
  `result` tem `is_error: true` também vira falha permanente (achado novo — a ADR-002
  não tinha essa distinção porque `--output-format json` não expunha isso da mesma
  forma).

**`src/workflow_engine/adapters/http_api.py`** (extensão da feature `004`):
- `_resolve_active_claude_step(watch_dir, chain_name)`: lê `workflow_runs.config_path`
  do `.db`, recarrega a cadeia (`YamlJsonChainLoader`, sem `known_plugins` — só precisa
  do mapeamento etapa→plugin), acha a etapa com `status="running"` cujo `plugin` é
  `claude_code_runner`, extrai `workspace_path` do `input` dessa etapa (carry-forward,
  ADR-002). Retorna `None` uniformemente para "chain desconhecida", "sem etapa rodando"
  ou "etapa rodando não é Claude Code Runner" — todos os casos viram a mesma resposta
  409 nas duas rotas novas.
- `GET /runs/{chain_name}/stream`: resolve o caminho do log, retransmite via
  `StreamingResponse` (SSE) — gerador lê linha a linha, e quando não há linha nova
  consulta `step_executions.status`; para de tailar quando o status deixa de ser
  "running" (drena o que sobrou antes de encerrar).
- `POST /runs/{chain_name}/instrucoes`: resolve o caminho de instruções, acrescenta a
  mensagem recebida.
- Nenhuma mudança em `ServerState`/`trigger`/`cancel` (feature `004` intocada).

## Data Model

Nenhuma mudança de schema. Dois arquivos novos por etapa (log + instruções), não
tabelas — `step_executions.status="running"` (já existente) é o que os endpoints usam
pra saber se ainda vale a pena tailar/aceitar instrução.

## Interfaces / Contracts

- **Popen/stdin**: `{"type": "user", "message": {"role": "user", "content": "<texto>"}}`
  por linha — formato verificado ao vivo, tanto pro prompt inicial quanto pras
  instruções de steering.
- **`GET /runs/{chain_name}/stream`**: SSE (`data: <linha>\n\n`), 200 quando há etapa
  ativa; 409 `not_streamable` caso contrário.
- **`POST /runs/{chain_name}/instrucoes`**: corpo `{"mensagem": "<texto>"}`, 202 quando
  há etapa ativa; 409 `not_interactable` caso contrário.

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01 | `plugins/claude_code_runner.py::_run_streaming_session` |
| FR-2 / AC-02, AC-03 | `plugins/claude_code_runner.py::_run_streaming_session` (escrita incremental) |
| FR-3 / AC-04, AC-05 | `plugins/claude_code_runner.py::_poll_instructions` |
| FR-4 / AC-06, AC-07 | `adapters/http_api.py::_tail_session_log` + rota `GET /runs/{chain_name}/stream` |
| FR-5 / AC-08, AC-09 | `adapters/http_api.py` rota `POST /runs/{chain_name}/instrucoes` |
| NFR-1 / AC-10 | `adapters/http_api.py::_resolve_active_claude_step` (lê só do `.db`+YAML, sem depender de `ServerState.active`) |

## Constitution Compliance

- **Spec before code**: este plan só passa a ser implementado depois que `tasks.md`
  fechar o gate de cobertura.
- **Plugin contract is stable** (princípio 5): `params`/`output`/`TransientError` do
  Claude Code Runner não mudam — só a implementação interna de invocação. Mudança
  registrada nesta ADR (005), conforme o princípio exige.
- **Hexagonal boundary is one-way** (princípio 6): `http_api.py` continua um adapter;
  `_resolve_active_claude_step` só lê arquivos `.db`/YAML já existentes, sem importar
  nada de `plugins/` (a convenção de caminho é duplicada, não importada — plugins
  nunca são uma dependência do core).

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Mecanismo de invocação | `Popen` de longa duração, stream-json nos dois sentidos | Manter `subprocess.run` e só reler o log ao final | Não permite interação em tempo real nem stream de verdade — só um replay depois de pronto |
| Entrega de instrução | Polling de arquivo (delta desde a última leitura) | Named pipe/socket por sessão | Portável (Windows não tem named pipes POSIX); latência de polling aceitável para uso local/individual |
| Extração do resultado | Prefere `structured_output` (achado ao vivo) sobre `result`-como-string | Só usar `result` (como a ADR-002 original) | `structured_output` já vem parseado — evita um parse duplo desnecessário quando disponível |
| Como `serve` acha o Claude Code Runner ativo | Recarrega a config YAML da cadeia a cada chamada | Guardar o mapeamento etapa→plugin em algum lugar persistente | Config YAML já é a fonte de verdade (ADR-001); recarregar é barato e evita duplicar essa informação em outro lugar |

## Risks

- Polling de arquivo pode ter latência perceptível (não é um sistema de baixa
  latência) — aceitável para uso local/individual, mas real.
- `structured_output` não é uma flag documentada publicamente até onde verificado
  nesta sessão — pode mudar de nome/formato em versões futuras da CLI sem aviso
  formal (ver ADR-005, Riscos).
- `serve` recarrega a definição da cadeia a cada chamada de `/stream`/`/instrucoes` —
  custo pequeno, mas é I/O extra por requisição.
