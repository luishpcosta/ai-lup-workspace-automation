# Tasks: Motor de Workflow com Plugins Python

**Feature ID:** 001-motor-workflow-plugins
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-08-31

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades `ADR-001-AT-0N` em `adr/ADR-001-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | Definir a Plugin Interface base: contrato `run(context) -> output` e exceção `TransientError` | AC-05 | done | `src/workflow_engine/domain/ports.py` (`Plugin`), `domain/exceptions.py` (`TransientError`), `domain/models.py` (`PluginContext`); fachada pública em `plugin_sdk.py`; `tests/test_plugin_sdk.py` — `python -m pytest tests/test_plugin_sdk.py` (3 passed) |
| T-2 | Implementar schema e camada de acesso do State Store (SQLite): tabelas `workflow_runs` e `step_executions` | AC-14 | done | `src/workflow_engine/adapters/sqlite_state_store.py` (`SqliteStateStore`, implementa `domain/ports.py::StateStorePort`); `tests/test_sqlite_state_store.py` — `python -m pytest tests/test_sqlite_state_store.py` (7 passed) |
| T-3 | Implementar Plugin Registry: descoberta de plugins no diretório configurado e validação contra a Plugin Interface (depende de T-1) | AC-06, AC-07 | done | `src/workflow_engine/adapters/filesystem_plugin_registry.py` (`FileSystemPluginRegistry`, implementa `PluginRegistryPort`); `tests/test_filesystem_plugin_registry.py` — `python -m pytest tests/test_filesystem_plugin_registry.py` (5 passed) |
| T-4 | Implementar Chain Loader: parser/validador da cadeia declarativa (config YAML/JSON) | AC-03, AC-04 | done | `src/workflow_engine/adapters/yaml_json_chain_loader.py` (`YamlJsonChainLoader`, implementa `ChainLoaderPort`); `tests/test_yaml_json_chain_loader.py` — `python -m pytest tests/test_yaml_json_chain_loader.py` (7 passed) |
| T-5 | Implementar Retry Handler: wrapper de retry configurável por etapa/plugin reagindo a `TransientError` (depende de T-1) | AC-12, AC-13 | done | `src/workflow_engine/application/retry_handler.py`; `tests/test_retry_handler.py` — `python -m pytest tests/test_retry_handler.py` (4 passed) |
| T-6 | Implementar Logger: logging estruturado em JSON para eventos de início/retry/fim de etapa | AC-15 | done | `src/workflow_engine/adapters/json_event_logger.py` (`JsonEventLogger`, implementa `EventLoggerPort`); `tests/test_json_event_logger.py` — `python -m pytest tests/test_json_event_logger.py` (1 passed) |
| T-7 | Implementar Workflow Engine: orquestração sequencial da cadeia e decisão de input fixo vs. output da etapa anterior (depende de T-3, T-4) | AC-08, AC-09 | done | `src/workflow_engine/application/workflow_engine.py`; `tests/test_workflow_engine.py::test_output_chains_into_next_step_when_configured_ac08`, `::test_step_without_flag_does_not_receive_previous_output_ac09` |
| T-8 | Integrar Workflow Engine ao State Store: persistir progresso por etapa e permitir retomada de execução incompleta (depende de T-2, T-7) | AC-10, AC-11 | done | `tests/test_workflow_engine.py::test_new_run_executes_from_start_ac01`, `::test_permanent_failure_stops_execution_ac11`, `::test_resume_skips_completed_steps_and_retries_failed_one_ac02` |
| T-9 | Implementar CLI: comando `workflow run <config>` que inicia nova execução ou retoma a incompleta mais recente (depende de T-4, T-8) | AC-01, AC-02 | done | `src/workflow_engine/adapters/cli.py` (composition root); `tests/test_cli.py` — `python -m pytest tests/test_cli.py` (2 passed); smoke-test manual via `python -m workflow_engine.adapters.cli run ...` confirmou encadeamento de output e logging JSON em execução real |

Status values: `todo` → `doing` → `done`.

Full suite: `python -m pytest -q` → `34 passed` (2026-08-31). `python -m compileall .` → exit 0.

**Refatoração hexagonal (2026-08-31)**: código reorganizado em `domain/` (entidades/exceções/ports), `application/` (`RetryHandler`, `WorkflowEngine`) e `adapters/` (implementações concretas + `cli.py` como composition root), sem mudança de comportamento — mesma suíte de 34 testes, apenas com imports/paths atualizados. Ver `plan.md` (seção Architecture & Components) e `constitution.md` (princípio 6) para a regra de fronteira.

## Coverage Check

Confirm manually before implementing:

- Every AC referenced by at least one task? yes (AC-01 a AC-15 cobertas por T-1 a T-9)
- Every task linked to an AC? yes
