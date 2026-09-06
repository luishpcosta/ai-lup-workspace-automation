# Plan: Templates de Workflow e Execução Ad-hoc (Repo Local + Modo Investigar)

**Feature ID:** 006-workflow-templates-execucao-adhoc
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-06

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Um **template de workflow** é um arquivo de chain config (`.yaml`) que também declara
sua própria metadata (`id`/`label`/`description`/`params_schema`) — um único arquivo,
carregável sem modificação pelo `YamlJsonChainLoader` existente (ele só lê as chaves que
conhece: `name`/`vars`/`steps`) e também pelo novo
`FileSystemWorkflowTemplateRegistry` (que lê as chaves de metadata e ignora o resto).

`POST /runs/from-template` valida os `params` recebidos contra o `params_schema`
declarado (`application/workflow_templates.py::validate_params`, função pura), depois
materializa um chain config novo (`materialize_chain_raw`, também pura: clona
`template.raw`, troca `name` por um `chain_name` único, faz merge de `params` em
`vars:`) e escreve esse resultado como um YAML real em
`<watch_dir>/_generated-configs/<chain_name>.yaml`. A partir daí, delega para
`ServerState.trigger(config_path)` — o mesmo método que `POST /runs` já usa. Nenhum
mecanismo existente (monitoria, SSE, instruções, cancelamento) precisa saber que a
execução veio de um template.

O modo `investigar` é uma adição ao `ClaudeCodeRunnerPlugin` existente (mesma classe,
mesmo arquivo) — `workspace_path` passa a também poder vir de `context.params`, além de
`context.input` (mantido para `coding`/`review`).

Decisão completa, diagrama e alternativas em
`adr/ADR-007-templates-workflow-execucao-adhoc.md`.

## Architecture & Components

**`domain/models.py`** (novo):
- `WorkflowTemplateParam(name, label, type, required=False, source=None)`.
- `WorkflowTemplateDefinition(id, label, description, params: tuple[...], raw: dict)`.

**`domain/ports.py`** (novo): `WorkflowTemplateRegistryPort` (`discover`/`get`/`list`),
espelhando `PluginRegistryPort`.

**`domain/exceptions.py`** (novo): `WorkflowTemplateNotFoundError`.

**`adapters/filesystem_workflow_template_registry.py`** (novo): varre `*.yaml`/`*.yml`
do diretório configurado, `yaml.safe_load` cada um, valida presença de
`id`/`label`/`description`/`params_schema`/`name`/`steps`; um arquivo malformado é
logado (`logger.warning`) e pulado, nunca derruba `discover()`.

**`application/workflow_templates.py`** (novo, só domínio):
- `validate_params(template, submitted) -> list[str]`.
- `materialize_chain_raw(template, submitted, chain_name) -> dict` — todo param
  declarado recebe default `""` antes do merge (para que um opcional não submetido
  ainda resolva no Chain Loader, que valida antes de qualquer execução).

**`adapters/yaml_json_chain_loader.py`** (fix pontual): `_resolve_vars` agora primeiro
testa se o valor inteiro do param (stripped) é uma referência `{{ vars.x }}` completa
(`_VARS_REF_WHOLE`); se for, devolve `raw_vars[x]` sem `str()`, preservando o tipo. Caso
contrário, mantém a substituição textual existente (`_VARS_REF.sub`).

**`adapters/http_api.py`** (extensão da ADR-004/005):
- `ServerState.__init__` ganha `templates_dir`/`local_repos_root`; monta
  `self.template_registry` (discover no boot) e `self.generated_configs_dir`
  (`<watch_dir>/_generated-configs`, criado no boot).
- `ServerState.trigger_from_template(template_id, submitted)`: busca template (404 se
  não achar), valida (400 se faltar obrigatório), gera `chain_name` único
  (`f"{template_id}--{uuid4().hex[:8]}"`), materializa e escreve o YAML, delega para
  `self.trigger(config_path)`.
- Rotas novas: `GET /workflows`, `GET /workspace/repos`, `POST /runs/from-template`
  (`FromTemplateRequest{template_id, params}`), mapeando erros para o contrato uniforme
  `{"error":{"code","message"}}` já usado (`template_not_found`, `invalid_params`,
  `already_running`).
- `build_app()`/`cmd_serve()` passam a receber/repassar `templates_dir`,
  `local_repos_root`.

**`adapters/cli.py`**: `serve_parser` ganha `--workflow-templates-dir` (default
`./config/workflow_templates`) e `--local-repos-root` (default `None`).

**`plugins/claude_code_runner.py`**: `run()` ganha o branch `modo == "investigar"` →
`_run_investigar`. `workdir = input_data.get("workspace_path") or params.get(
"workspace_path")` (nota: usa a chave `workspace_path` em `params`, diferente de
`coding`/`review`, que usam `workdir` — nome pedido explicitamente para este modo, ver
ADR-007). Prompt (`_investigar_prompt`) instrui explicitamente contra branch/commit/
push/PR e pede `relatorio`+`docs_consultados` estruturados
(`_INVESTIGAR_SCHEMA`, mesma mecânica de `--json-schema` já usada). Reusa
`_build_cmd`/`_run_streaming_session`/`_poll_instructions` sem alteração.

**Novos arquivos de config**: `config/mcp-docs-proxy.json` (MCP `docs-mcp-proxy`
apontando para `doc-repo-example`), `config/workflow_templates/investigar-impacto.yaml`,
`config/workflow_templates/implementar-historia-sdd.yaml` (mesmos `steps:` de
`examples/implementar-historia-sdd.yaml`, com `params_schema` correspondente).

## Data Model

Nenhuma mudança de schema SQLite. Um diretório novo,
`<watch_dir>/_generated-configs/`, guarda um YAML por disparo de template — mesma
convenção de arquivo que `<watch_dir>/<chain_name>.db`, sem tabela nova.

## Interfaces / Contracts

- **`GET /workflows`**: 200, `[{id, label, description, params_schema: [{name, label, type, required, source}]}]`.
- **`GET /workspace/repos`**: 200, `[{name, path}]` (vazio se `--local-repos-root` não configurado ou inexistente).
- **`POST /runs/from-template`**: corpo `{"template_id": str, "params": dict}`; 202 `{chain_name, status: "started"}` (mesma forma de `POST /runs`); 400 `invalid_params`; 404 `template_not_found`; 409 `already_running` (defensivo — praticamente inalcançável dado o `chain_name` gerado por UUID).
- **Modo `investigar` do Claude Code Runner**: `params = {modo: "investigar", prompt: str, docs_referenced?: list[str], workspace_path?: str, mcp_config_path: str}`; output `{status, relatorio, docs_consultados, session_log_path}`.

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01, AC-02, AC-07 | `filesystem_workflow_template_registry.py`, rota `GET /workflows` |
| FR-2 / AC-08, AC-09 | rota `GET /workspace/repos` |
| FR-3 / AC-10 | `ServerState.trigger_from_template` + rota `POST /runs/from-template` |
| FR-4 / AC-03, AC-04, AC-11, AC-12 | `application/workflow_templates.py::validate_params`, rota `POST /runs/from-template` |
| FR-5 / AC-13 | `ServerState.trigger_from_template` (`chain_name` único por UUID) |
| FR-6, FR-7 / AC-14, AC-15, AC-16 | `plugins/claude_code_runner.py::_run_investigar` |
| FR-8 / AC-17 | `config/workflow_templates/implementar-historia-sdd.yaml` |
| AC-05, AC-06 | `adapters/yaml_json_chain_loader.py::_resolve_vars` (fix) |
| NFR-1 | Reuso de `ServerState.trigger`/monitoria/SSE/instruções (ADR-004/005), sem mudança neles |
| NFR-2 (herdado) | `Plugin.run(context) -> output` inalterado |

## Constitution Compliance

- **Spec before code**: este plan só passa a ser implementado depois que `tasks.md`
  fechar o gate de cobertura.
- **Plugin contract is stable** (princípio 5): `Plugin.run(context) -> output` /
  `TransientError` não mudam — o modo `investigar` é só um novo valor de
  `params["modo"]`, mesmo contrato externo do Claude Code Runner (ADR-002/005).
- **Hexagonal boundary is one-way** (princípio 6): `WorkflowTemplateRegistryPort` fica
  em `domain/ports.py` (sem infra); `FileSystemWorkflowTemplateRegistry` (infra: `yaml`,
  filesystem) fica em `adapters/`; `application/workflow_templates.py` depende só de
  `domain/models.py`. `http_api.py` continua o único lugar (com `cli.py`) que monta o
  registro concreto.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Como materializar a chain de um template | Escreve YAML real em disco e reusa `ServerState.trigger()` | `ChainLoaderPort` aceita dict em memória | `_resolve_active_claude_step` (ADR-005) recarrega a chain do `.db`+YAML — um caminho em memória exigiria lógica especial só para runs de template |
| Formato do arquivo de template | Um único YAML, chain config + metadata juntos | Metadata em arquivo separado | Evita duplicar `name`/`steps` em dois arquivos sincronizados |
| Onde `workspace_path` vem no modo investigar | `context.params` (novo) OU `context.input` (compat) | Só `context.input`, exigindo um step `workspace_setup` antes sempre | O template `investigar-impacto` roda direto num repo local, sem etapa de preparação — `workspace_setup` seria clone desnecessário |
| Param opcional não submetido | Default `""` em `vars:` antes do merge | Deixar a chave ausente | Chain Loader valida `{{ vars.x }}` contra chaves existentes antes de qualquer execução — chave ausente quebraria a validação, não só o plugin |
| `chain_name` de um disparo de template | `f"{template_id}--{uuid4().hex[:8]}"` | Exigir que o usuário informe um nome | Elimina colisão entre disparos concorrentes sem exigir input extra do usuário |

## Risks

- `<watch_dir>/_generated-configs/` cresce indefinidamente nesta versão — sem limpeza
  automática, mesma postura já aceita para `--watch-dir` (ADR-004).
- Um plugin novo que declare um param opcional e trate `""` como um valor válido
  (diferente de "ausente") teria comportamento diferente do esperado — nenhum plugin
  existente faz isso (todos usam `if param:`/`.get(x) or default`), mas é uma convenção
  implícita a documentar para autores de plugin futuros.
