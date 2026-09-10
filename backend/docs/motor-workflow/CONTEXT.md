---
contexto: motor-workflow
depende_de: []
---

# Contexto: motor-workflow

Motor de workflow local (Python) que orquestra uma cadeia configurável de etapas via
plugins, mais os pontos de entrada e observabilidade construídos em torno dele
(CLI, execuções paralelas, API HTTP, streaming). Ver `adr/` para o histórico de
decisões deste contexto (ADR-001 a ADR-005) — a partir da ADR-006 (decidida no
diretório do contexto [frontend](../../../frontend/docs/CONTEXT.md), que a mantém
em `frontend/adr/`) este contexto passa a ser consumido por ele via REST/SSE.

## Linguagem

**Plugin**:
Unidade de extensão do motor — implementa `run(context) -> output`; é o único ponto
onde o motor invoca uma ferramenta externa (git, `claude`, `gh`, um script).
_Evitar_: step handler, task, adapter (adapter é termo da arquitetura hexagonal interna, não do plugin).

**TransientError**:
Exceção que um plugin levanta para sinalizar uma falha retriable. Qualquer outra
exceção é tratada como falha permanente pelo motor.
_Evitar_: retryable error, soft failure.

**Carry-forward**:
Convenção pela qual um plugin inclui todos os campos de `context.input` no próprio
`output`, para que dados de uma etapa alcancem etapas mais de um passo à frente na
cadeia (o motor só entrega a uma etapa o `output` da etapa imediatamente anterior).
_Evitar_: propagation, pass-through (usar sempre "carry-forward").

**chain_name**:
Nome declarado no campo `name` da config de uma cadeia; identifica de forma única uma
execução em um lote (`run-many`) ou num diretório observado (`serve`) — é o nome do
arquivo State Store (`<chain_name>.db`).
_Evitar_: workflow_name (usado apenas dentro do schema legado de `workflow_run`/`001`, não como termo corrente).

**workspace_path**:
Diretório determinístico (`<workspaces_root>/<repo_slug>__<historia_id>`) onde o
Workspace Setup clona/prepara o repositório-alvo de uma história. Chega às etapas
seguintes por carry-forward.
_Evitar_: working directory, checkout path.

**session_log_path**:
Caminho determinístico (`<workspace_path>/.workflow-logs/<run_id>/<step_name>.log`)
do transcript de uma sessão do Claude Code Runner — existe mesmo quando a etapa falha,
e (a partir da ADR-005) é escrito incrementalmente, tornando-se "tailable" em tempo real.
_Evitar_: session transcript, output file.

**pergunta pendente** (`ask_user`, ADR-013):
Tool MCP dedicada (`mcp_servers/ask_user_server.py`) que o modo
`coding_local_interativo` do Claude Code Runner disponibiliza ao agente — chamá-la
bloqueia de verdade o agente (protocolo de tool-use, não convenção de prompt) até
uma resposta chegar por `POST /runs/{chain_name}/resposta` ou o timeout estourar.
Sinalizada pela existência de `<step_name>.pergunta.json` (par de
`<step_name>.resposta.json`), mesma convenção determinística de `session_log_path`/
`instructions_path`. _Evitar_: confirmação (termo já usado por `confirm_pr`,
ADR-008, que é polling/retry, não pausa real).

**awaiting_input** (ADR-013):
Campo aditivo de `GET /runs`/`GET /runs/{chain_name}` — `true` só quando a run está
`running` **e** existe uma pergunta pendente (`ask_user`) para a etapa ativa; derivado
em tempo de leitura, sem coluna nova no State Store, mesma filosofia de `plugin`
(ADR-010)/`archived`/`duration_seconds` (ADR-011/012).
