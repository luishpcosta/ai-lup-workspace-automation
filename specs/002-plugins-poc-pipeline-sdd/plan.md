# Plan: Plugins de Prova de Conceito — Pipeline SDD Ponta a Ponta

**Feature ID:** 002-plugins-poc-pipeline-sdd
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-03

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Quatro plugins novos, descobertos pelo `FileSystemPluginRegistry` já existente no diretório externo `./plugins/` (convenção `PLUGIN`/`PLUGIN_NAME` por arquivo, herdada da feature `001` — nenhuma mudança nessa convenção). Cada plugin implementa só `workflow_engine.plugin_sdk.Plugin` (`run(context) -> output`) — nenhum importa `domain`/`application`/`adapters` diretamente, preservando a fronteira hexagonal (`constitution.md`, princípio 6).

A única mudança dentro de `src/workflow_engine/` é uma extensão aditiva e retrocompatível do `YamlJsonChainLoader` (`adapters/yaml_json_chain_loader.py`) para resolver um bloco `vars:` opcional na config. O contrato `Plugin.run(context) -> output` **não muda** (constitution, princípio 5) — a resolução de `vars` acontece inteiramente dentro do Chain Loader, antes de os `params` chegarem a qualquer plugin.

Decisão completa, diagrama da cadeia, contratos de payload por plugin e invocação verificada da CLI do Claude Code em `adr/ADR-002-plugins-poc-pipeline-sdd.md`.

## Architecture & Components

**`plugins/`** (externo ao pacote `workflow_engine`, descoberto via `FileSystemPluginRegistry`):
- `workspace_setup.py` — `PLUGIN = WorkspaceSetupPlugin`. Clona/atualiza repo, cria branch, instala dependências, sobe infraestrutura Docker opcional. `workspace_path` segue convenção determinística: `<workspaces_root>/<repo_slug>__<historia_id>` (`workspaces_root` é config de ambiente do plugin, não `param` de etapa).
- `claude_code_runner.py` — `PLUGIN = ClaudeCodeRunnerPlugin`. Invoca `claude -p ...` via `subprocess`, parametrizado por `params.modo` (`coding`|`review`). `session_log_path` segue convenção determinística: `<workspace_path>/.workflow-logs/<run_id>/<step_name>.log`, escrito incrementalmente (sobrevive a falha/timeout).
- `shell_script_runner.py` — `PLUGIN = ShellScriptRunnerPlugin`. Executa `.sh`/`.bat` via `subprocess`, expõe `context.input` como env vars `WORKFLOW_INPUT_<CHAVE>`, repassa `context.input` no próprio `output` (carry-forward).
- `git_pr.py` — `PLUGIN = GitPrPlugin`. Cria/atualiza PR via `gh` CLI (corpo por `--body-file`, nunca `--body` inline). Valida rastreabilidade (`historia_id` + `docs_referenced`) antes de qualquer chamada ao `gh`. Repassa `context.input` no próprio `output` (carry-forward).

**`src/workflow_engine/adapters/yaml_json_chain_loader.py`** (extensão do adapter existente, RF-5):
- `load()` passa a ler `raw.get("vars")` (dict `str -> str`) opcionalmente, no nível raiz.
- Novo helper privado que resolve `{{ vars.<chave> }}` em qualquer valor string de `params`, para cada `StepDefinition`, antes de retornar o `ChainDefinition`.
- Chave ausente em `vars` → `ChainValidationError` (mesma exceção já usada para plugin inexistente), levantada durante o parsing — antes de qualquer etapa rodar.

**`src/workflow_engine/adapters/json_event_logger.py`** (extensão do adapter existente, NFR-1):
- `log_event()` passa a incluir um campo `correlacao` no registro quando `run_id`/`step_name`/`event`/`extra` contiverem algum de `historia_id`, `branch`, `pr_number`, `pr_url` — sem exigir que a etapa os declare.

## Data Model

Nenhuma tabela nova. Reusa `workflow_runs`/`step_executions` (`001`) sem alteração de schema — a correlação (NFR-1) é resolvida via Logger, não via State Store (ver `adr/ADR-002-plugins-poc-pipeline-sdd.md`, Alternativas consideradas, sobre por que não se estendeu o schema).

## Interfaces / Contracts

Contratos de payload completos (params obrigatórios/opcionais, output, mapeamento de erro para `TransientError` vs. falha permanente) por plugin estão em `adr/ADR-002-acs.md`. Resumo:

- **Convenção de carry-forward**: todo plugin que recebe `context.input` inclui esses campos no próprio `output` (chaves novas do plugin têm precedência em colisão) — necessário porque `PluginContext` só carrega o `output` da etapa imediatamente anterior (contrato herdado de `001`, não alterado aqui).
- **`{{ vars.<chave> }}`**: resolvido pelo Chain Loader, nos `params`, antes da etapa rodar — sintaxe e timing diferentes de `{{ summary }}`/`{{ docs_referenced }}` dentro de `title_template`/`body_template`, que são resolvidos pelo próprio plugin `git_pr` em runtime a partir de `context.input`.
- **Invocação verificada da CLI do Claude Code** (`claude` 2.1.260): `-p/--print`, `--mcp-config <path> --strict-mcp-config` (nunca depende de `.mcp.json` de projeto auto-descoberto), `--output-format json --json-schema <schema>` (extração estruturada de `summary`/`docs_referenced`), `--permission-mode acceptEdits --permission-prompts none`; modo `review` **sem** `-r/--resume`/`-c/--continue`/`--fork-session` (garante sessão nova).

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01, AC-02, AC-03 | `plugins/workspace_setup.py` |
| FR-2 / AC-04, AC-05, AC-06, AC-07 | `plugins/claude_code_runner.py` |
| FR-3 / AC-09, AC-10, AC-11 | `plugins/shell_script_runner.py` |
| FR-4 / AC-12, AC-13, AC-14, AC-15 | `plugins/git_pr.py` |
| FR-5 / AC-18, AC-19, AC-20 | `src/workflow_engine/adapters/yaml_json_chain_loader.py` (extensão) |
| NFR-1 / AC-16, AC-17 | `src/workflow_engine/adapters/json_event_logger.py` (extensão) |
| NFR-2 / AC-05, AC-07, AC-08 | `plugins/claude_code_runner.py` |
| NFR-3 / AC-02 | `plugins/workspace_setup.py` |
| NFR-4 / AC-14 | `plugins/git_pr.py` |
| NFR-5 (herdado) | `001` — sem mudança |

## Constitution Compliance

- **Spec before code**: este plan só passa a ser implementado depois que `tasks.md` fechar o gate de cobertura.
- **Plugin contract is stable** (princípio 5): `Plugin.run(context) -> output` e `TransientError` não mudam; a única extensão de contrato (`vars:` na config) está registrada em `adr/ADR-002-plugins-poc-pipeline-sdd.md`, conforme exigido.
- **Hexagonal boundary is one-way** (princípio 6): os 4 plugins novos ficam em `./plugins/` (fora de `src/workflow_engine/`) e só importam `workflow_engine.plugin_sdk`; a extensão do Chain Loader e do Logger fica dentro de `adapters/`, sem introduzir import de `adapters` em `domain`/`application`.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Contexto MCP para o Claude Code | Configuração nativa da CLI (`--mcp-config`), sem plugin dedicado | Plugin "MCP Context" que busca a doc antes do coding | Claude Code já suporta MCP nativamente; um plugin extra só duplicaria a responsabilidade |
| Infraestrutura Docker | Capacidade opcional do `workspace_setup` (`docker_compose_path`) | Plugin dedicado de infraestrutura | Faz parte de "preparar o ambiente"; não justifica um plugin/etapa a mais no POC |
| Encadeamento multi-hop (dado de uma etapa 2+ posições atrás) | Convenção de carry-forward (plugin repassa `input` no próprio `output`) + reordenar a cadeia (PR logo após coding) | Estender `PluginContext`/`StateStorePort` com lookup de qualquer etapa anterior | Resolve sem tocar o contrato de Plugin estável (`001`); mudança de contrato central fica registrada como alternativa a reconsiderar se mais plugins precisarem de lookup não-adjacente |
| Rastreabilidade da PR (`historia_id`, docs consultados) | Validação obrigatória no `git_pr` antes de criar a PR, falha permanente se ausente | Deixar como recomendação não-obrigatória | Usuário levantou auditabilidade como requisito explícito — recomendação não garante rastro |
| Transcript do Claude Code | Caminho determinístico (`<workspace_path>/.workflow-logs/<run_id>/<step_name>.log`), não retornado só via `output` | Só retornar `session_log_path` no `output` de sucesso | Contrato de `001` trata falha como exceção sem `output` estruturado — caminho determinístico funciona mesmo quando a etapa falha |
| Duplicação de `historia_id`/`branch_name` entre etapas | Estender Chain Loader com `vars:` (retrocompatível) | Manter duplicação literal (decisão inicial do POC) | Risco de inconsistência entre etapas considerado alto o suficiente para justificar a extensão, mesmo sendo pequena |
| Extração de `docs_referenced` | `--json-schema` da CLI do Claude Code (saída estruturada garantida) | Parsing de texto livre da resposta | Elimina ambiguidade de parsing; a CLI garante o campo/tipo |

## Risks

- `gh` CLI e Docker precisam estar instalados e autenticados no ambiente local — fora do controle do motor.
- Falha de rede/MCP durante a etapa de coding não aparece no State Store (só vê o resultado final da etapa) — só no transcript em `session_log_path`; quem audita precisa consultar os dois lugares.
- Flags da CLI do Claude Code (`--mcp-config`, `--json-schema`, `--permission-prompts`) podem mudar entre versões — a invocação foi verificada contra `claude 2.1.260`; checar `claude --help` ao atualizar a CLI no ambiente de execução.
- Duas sintaxes de interpolação `{{ }}` coexistindo (vars do Chain Loader vs. `context.input` resolvido pelo `git_pr`) exige atenção de quem escrever configs.
- Volume/escala real não validado (herdado de `001`).
