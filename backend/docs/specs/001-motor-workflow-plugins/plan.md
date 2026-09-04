# Plan: Motor de Workflow com Plugins Python

**Feature ID:** 001-motor-workflow-plugins
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-08-31

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Motor em Python com execução sequencial de uma cadeia de etapas declarada em um arquivo de config (YAML/JSON). Cada etapa referencia um plugin descoberto em um diretório local; o motor resolve o plugin, decide o input (parâmetro fixo ou output da etapa anterior), executa a chamada através de um wrapper de retry, e persiste o progresso em SQLite antes de seguir para a próxima etapa. Decisão completa e diagrama em `adr/ADR-001-motor-workflow-plugins.md`.

Implementação organizada em **arquitetura hexagonal (ports & adapters)**: o núcleo (domínio + orquestração) não importa nenhuma infraestrutura concreta (sqlite3, PyYAML, argparse, logging handlers); ele depende só de interfaces (`Ports`), e cada tecnologia concreta entra como um `Adapter` plugável. Isso é o que permite trocar SQLite por outro backend de persistência, ou YAML por outro formato de config, sem tocar no Workflow Engine.

## Architecture & Components

**`domain/`** (entidades, exceções, ports — sem imports de infraestrutura):
- `models.py` — `RetryPolicy`, `PluginContext`, `StepDefinition`, `ChainDefinition`, `WorkflowRun`, `StepExecution`.
- `exceptions.py` — `TransientError`, `RetryExhaustedError`, `PluginNotFoundError`, `ChainValidationError`, `WorkflowFailed`.
- `ports.py` — `Plugin` (contrato que todo plugin implementa), `PluginRegistryPort`, `StateStorePort`, `EventLoggerPort` (+ `NullEventLogger`, default sem I/O), `ChainLoaderPort`.

**`application/`** (orquestração; depende só de `domain`, nunca de `adapters`):
- `retry_handler.py` — `RetryHandler`, aplica a política de retry configurável reagindo a `TransientError`.
- `workflow_engine.py` — `WorkflowEngine`, orquestra a execução sequencial via `PluginRegistryPort`/`StateStorePort`/`EventLoggerPort`, decide o input de cada etapa.

**`adapters/`** (implementações concretas dos ports; só aqui entra infraestrutura):
- `filesystem_plugin_registry.py` — `FileSystemPluginRegistry` (implementa `PluginRegistryPort`): varre o diretório de plugins, importa os módulos e valida conformidade com `Plugin`.
- `sqlite_state_store.py` — `SqliteStateStore` (implementa `StateStorePort`): persiste `workflow_runs`/`step_executions`.
- `yaml_json_chain_loader.py` — `YamlJsonChainLoader` (implementa `ChainLoaderPort`): parseia e valida o YAML/JSON da cadeia.
- `json_event_logger.py` — `JsonEventLogger` (implementa `EventLoggerPort`): logging estruturado em JSON.
- `cli.py` — comando `workflow run <config>`; é a **composition root**: único módulo que importa adapters concretos e os injeta no `WorkflowEngine`; decide iniciar do zero ou retomar uma execução incompleta.

**`plugin_sdk.py`** — fachada pública para autores de plugin (`from workflow_engine.plugin_sdk import Plugin, PluginContext, TransientError`), para não expor o layout interno de `domain/`.

## Data Model

- `workflow_runs`: `run_id` (PK), `workflow_name`, `config_path`, `status` (`running`|`completed`|`failed`), `created_at`, `updated_at`.
- `step_executions`: `run_id` (FK), `step_name`, `status` (`pending`|`running`|`completed`|`failed`), `attempt_count`, `input` (JSON), `output` (JSON), `error_message`, `started_at`, `finished_at`.

## Interfaces / Contracts

- **Plugin**: `run(context) -> output`, onde `context` contém `input` (output da etapa anterior, ou `None`), `params` (dict da config), `run_id`, `step_name`. `output` é qualquer valor serializável em JSON.
- **Sinalização de erro**: plugin levanta `TransientError` para falha retriable; qualquer outra exceção é tratada como falha permanente.
- **Config da cadeia** (YAML/JSON): lista ordenada de etapas, cada uma com `plugin` (nome), `params` (dict), `usa_output_anterior` (bool, opcional, default `false`) e política de retry opcional (nº de tentativas + backoff).

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-03, AC-04 | `adapters/yaml_json_chain_loader.py` (`ChainLoaderPort`) |
| FR-2 / AC-05 | `domain/ports.py` (`Plugin`) |
| FR-3 / AC-06, AC-07 | `adapters/filesystem_plugin_registry.py` (`PluginRegistryPort`) |
| FR-4 / AC-01, AC-02, AC-10, AC-11, AC-14 | `application/workflow_engine.py` + `adapters/sqlite_state_store.py` (`StateStorePort`) |
| FR-5 / AC-05, AC-12, AC-13 | `application/retry_handler.py` |
| FR-6 / AC-15 | `adapters/json_event_logger.py` (`EventLoggerPort`) |
| FR-7 / AC-08, AC-09 | `application/workflow_engine.py` |

## Constitution Compliance

- **Spec before code**: este plan só passa a ser implementado depois que `tasks.md` fechar o gate de cobertura (ver Coverage Check em `tasks.md`).
- **Toda decisão é rastreável**: cada AC listada acima referencia um componente e, em `tasks.md`, uma tarefa.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Execução entre etapas | Sequencial/síncrona | Paralelo/assíncrono entre etapas | Fora de escopo nesta versão; simplifica o modelo de estado |
| Definição da cadeia | Config declarativa referenciando plugins Python | Composição só em código (estilo LCEL) | Evita exigir escrever Python só para montar a sequência |
| Persistência | SQLite | Arquivo JSON simples | Facilita consulta de execuções passadas e concorrência mínima de leitura/escrita |
| Sinalização de erro retriable | Exceção tipada `TransientError` | Retorno com flag explícita de sucesso/falha | Mais idiomático em Python; evita checar um campo de flag em todo call site |
| Assinatura do plugin | `run(context) -> output` | `run(input, params) -> output` | Um único parâmetro agrega metadados (`run_id`, `step_name`) sem crescer a assinatura no futuro |
| Distribuição | Clone do repositório (`pip install -e .`) | Publicação em PyPI/índice privado | Uso interno por enquanto (fora de escopo) |
| Organização interna do código | Arquitetura hexagonal (`domain`/`application`/`adapters`) | Módulos flat (um arquivo por responsabilidade, sem camadas) | Isola o núcleo de infraestrutura concreta (SQLite, PyYAML, argparse), tornando trivial trocar de adapter (ex.: outro backend de persistência) sem tocar a orquestração; motivado pelo próprio RF-3 (plugins como adapters de terceiros) |

## Risks

- A convenção de plugin (`run(context)->output`, `TransientError`) precisa ser adotada consistentemente por todo plugin futuro — qualquer desvio quebra retry e persistência.
- Volume/escala real não foi validado com dados; se o uso crescer além do individual, a decisão de execução sequencial (RNF-01 do ADR-001) precisa ser revisitada.
- SQLite introduz uma dependência de schema — mudanças em `step_executions` exigem estratégia de migração.
- A separação em camadas (`domain`/`application`/`adapters`) só tem valor se for mantida: um import de `adapters` dentro de `domain`/`application` quebra o isolamento silenciosamente (nada barra isso automaticamente hoje — é checado manualmente, ver `constitution.md`).
