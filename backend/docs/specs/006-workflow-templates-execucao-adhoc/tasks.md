# Tasks: Templates de Workflow e Execução Ad-hoc (Repo Local + Modo Investigar)

**Feature ID:** 006-workflow-templates-execucao-adhoc
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-06

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades `ADR-007-AT-0N` em `adr/ADR-007-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | `domain/models.py` (`WorkflowTemplateParam`, `WorkflowTemplateDefinition`), `domain/ports.py` (`WorkflowTemplateRegistryPort`), `domain/exceptions.py` (`WorkflowTemplateNotFoundError`) (ADR-007-AT-01) | AC-01 | done | `src/workflow_engine/domain/{models,ports,exceptions}.py` |
| T-2 | `adapters/filesystem_workflow_template_registry.py`: descoberta por diretório, template malformado logado e pulado (ADR-007-AT-01) (depende de T-1) | AC-01, AC-02 | done | `tests/test_filesystem_workflow_template_registry.py` — 5/5 passed |
| T-3 | `application/workflow_templates.py`: `validate_params`, `materialize_chain_raw` (default `""` para param opcional não submetido) (ADR-007-AT-02) (depende de T-1) | AC-03, AC-04 | done | `tests/test_workflow_templates_application.py` — 5/5 passed |
| T-4 | `adapters/yaml_json_chain_loader.py::_resolve_vars`: preserva tipo quando o valor do param é uma referência `{{ vars.x }}` inteira (ADR-007-AT-03) | AC-05, AC-06 | done | `tests/test_yaml_json_chain_loader.py::test_whole_value_vars_ref_preserves_list_type_ac07`, `::test_partial_vars_ref_is_still_stringified_ac08` |
| T-5 | `GET /workflows`, `GET /workspace/repos` em `http_api.py`; `ServerState` ganha `template_registry`/`local_repos_root` (ADR-007-AT-04) (depende de T-2) | AC-07, AC-08, AC-09 | done | `tests/test_http_api_templates.py::test_get_workflows_lists_templates_with_schema_ac01`, `::test_get_local_repos_is_empty_when_not_configured_ac03`, `::test_get_local_repos_lists_subfolders_when_configured_ac02` |
| T-6 | `POST /runs/from-template` + `ServerState.trigger_from_template` (materializa YAML em `_generated-configs/`, delega para `trigger()` existente) (ADR-007-AT-05) (depende de T-3, T-5) | AC-10, AC-11, AC-12, AC-13 | done | `tests/test_http_api_templates.py::test_post_runs_from_template_dispatches_and_completes_ac04`, `::test_post_runs_from_template_rejects_missing_required_param_ac05`, `::test_post_runs_from_template_rejects_unknown_template_ac06`, `::test_two_dispatches_of_the_same_template_never_collide_in_chain_name_ac07` |
| T-7 | `adapters/cli.py`: flags `--workflow-templates-dir`/`--local-repos-root` em `serve` (habilita configuração de T-5/T-6) | AC-08, AC-09 | done | `src/workflow_engine/adapters/cli.py` (`serve_parser`); coberto indiretamente por T-5 (mesmo caminho de config repassado por `cmd_serve`) |
| T-8 | `plugins/claude_code_runner.py`: modo `investigar` (`workspace_path` de `params`/`input`, prompt anti-branch/commit/PR, schema `relatorio`/`docs_consultados`) (ADR-007-AT-06) | AC-14, AC-15, AC-16 | done | `tests/test_claude_code_runner_plugin.py::test_investigar_mode_reads_workspace_path_from_params_ac_investigar_01`, `::test_investigar_mode_prefers_workspace_path_from_input_when_present`, `::test_investigar_mode_without_workspace_path_raises` |
| T-9 | `config/mcp-docs-proxy.json`, `config/workflow_templates/investigar-impacto.yaml`, `config/workflow_templates/implementar-historia-sdd.yaml` (regressão: mesmos `steps:` de `examples/implementar-historia-sdd.yaml`) | AC-01, AC-17 | done | Arquivos criados; `implementar-historia-sdd.yaml` verificado carregável por `YamlJsonChainLoader` (mesma estrutura `steps:` do example já coberto por smoke-test da feature `002`) — ver `progress.md` para verificação manual ponta a ponta pendente |

Status values: `todo` → `doing` → `done`.

Full suite: `python -m pytest -q` → **109 passed** (2026-09-06, era 87 antes desta
feature). `python -m compileall .` → exit 0. `ruff check .` → All checks passed.
`ruff format --check .` → 85 files already formatted.

## Coverage Check

Confirm manually before implementing:

- Every AC referenced by at least one task? yes (AC-01 a AC-17 cobertas por T-1 a T-9)
- Every task linked to an AC? yes
