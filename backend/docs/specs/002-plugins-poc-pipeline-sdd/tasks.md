# Tasks: Plugins de Prova de Conceito — Pipeline SDD Ponta a Ponta

**Feature ID:** 002-plugins-poc-pipeline-sdd
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-03

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades `ADR-002-AT-0N` em `adr/ADR-002-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | Estender `YamlJsonChainLoader` para resolver bloco `vars:` opcional e interpolar `{{ vars.<chave> }}` nos `params` de qualquer etapa, com validação de chave ausente (ADR-002-AT-07) | AC-18, AC-19, AC-20 | done | `src/workflow_engine/adapters/yaml_json_chain_loader.py` (`_resolve_vars`, regex `_VARS_REF` só casa `vars.*`, deixando `{{ summary }}`/`{{ docs_referenced }}` intactos); `tests/test_yaml_json_chain_loader.py::test_vars_resolved_in_step_params_ac18`, `::test_config_without_vars_block_behaves_like_before_ac19`, `::test_unknown_vars_key_fails_validation_ac20` — `python -m pytest tests/test_yaml_json_chain_loader.py -q` → 10 passed |
| T-2 | Implementar `plugins/workspace_setup.py`: clone/checkout de branch, install opcional, infraestrutura Docker opcional, `workspace_path`/`base_commit_sha` determinísticos (ADR-002-AT-01) | AC-01, AC-02, AC-03 | done | `plugins/workspace_setup.py`; `tests/test_workspace_setup_plugin.py` — `python -m pytest tests/test_workspace_setup_plugin.py -q` → 4 passed. Simplificação registrada: só a falha do docker compose é `TransientError` (único caso coberto por AC formal); falhas de git/install propagam como falha permanente — ver `progress.md` |
| T-3 | Implementar `plugins/claude_code_runner.py`, modo `coding`: invocação verificada da CLI (`-p`, `--mcp-config --strict-mcp-config`, `--json-schema`), `session_log_path` determinístico, `docs_referenced` estruturado (ADR-002-AT-02) (depende de T-2) | AC-04, AC-05 | done | `plugins/claude_code_runner.py` (`_run_coding`); `tests/test_claude_code_runner_plugin.py::test_coding_mode_invokes_cli_and_returns_structured_result_ac04_ac05` → 4 passed. **Verificado com chamada real** 2026-09-04 (`claude -p` de verdade contra `samples/docs-site`, ver `progress.md`): `--permission-mode acceptEdits --permission-prompts none` **negava** chamadas MCP; corrigido para `bypassPermissions`. Envelope JSON de `--json-schema` confirmado (`result` = string JSON escapada). Prompt agora instrui commit+push explicitamente (sem isso, `abrir_pr` falharia por a branch não existir no remoto) |
| T-4 | Implementar `plugins/git_pr.py`: criação/atualização de PR via `gh` CLI, validação obrigatória de rastreabilidade (`historia_id` + `docs_referenced`) antes de criar, carry-forward de `context.input` no output (ADR-002-AT-05) (depende de T-3) | AC-12, AC-13, AC-14, AC-15 | done | `plugins/git_pr.py` — flags reais verificadas (`gh 2.97.0`): `create` usa `--label`, `edit` usa `--add-label` (não intercambiáveis); `tests/test_git_pr_plugin.py` → 6 passed. **2 bugs reais achados numa PR real** (`github.com/luishpcosta/ai-lup-poc-target-cli`): (1) label do `params.labels` precisa já existir no repo, `gh pr create --label` falha se não existir — não é bug do plugin, é pré-requisito do repo-alvo, documentado; (2) título de PR > 256 chars (`summary` gerado pelo agente tinha 1007 chars) → `gh` rejeita (`GraphQL: Title is too long`) — corrigido com `_truncate_title` (256 chars, defensivo, não depende do autor do template acertar o tamanho), `test_title_over_256_chars_is_truncated` |
| T-5 | Implementar `plugins/shell_script_runner.py`: execução de script com timeout, `context.input` exposto como env vars `WORKFLOW_INPUT_*`, carry-forward no output (ADR-002-AT-04) (depende de T-4) | AC-09, AC-10, AC-11 | done | `plugins/shell_script_runner.py`; `tests/test_shell_script_runner_plugin.py` → 5 passed. Corrigido 2026-09-04 ao montar teste real: faltava `cwd=workspace_path` (script relativo resolveria a partir do processo da automação, não do repo clonado) — `test_runs_inside_workspace_path_from_input` |
| T-6 | Estender `plugins/claude_code_runner.py` com modo `review`: sessão nova (sem `-r`/`-c`/`--fork-session`), `session_log_path` determinístico (ADR-002-AT-03) (depende de T-5, mesmo arquivo de T-3) | AC-06, AC-07, AC-08 | done | Implementado junto com T-3 (mesmo arquivo/mesma plumbing de `_invoke_cli`/`_write_log`, T-6 não dependeu de fato de T-5 na prática); `tests/test_claude_code_runner_plugin.py::test_review_mode_starts_fresh_session_ac06_ac07`, `::test_failure_still_leaves_transcript_on_disk_ac08` — mesmo run acima, 4 passed |
| T-7 | Estender `JsonEventLogger` para incluir campo `correlacao` (história/branch/PR) quando presente nos dados da etapa, sem exigi-los (ADR-002-AT-06) (depende de T-2 a T-6, para conhecer os campos reais) | AC-16, AC-17 | done | Implementação real ficou em `application/workflow_engine.py` (`_log`/`_correlation`) + `adapters/cli.py` (`--correlation-keys`), não em `JsonEventLogger` — ver nota de arquitetura em `progress.md` (o Logger já repassava `**extra`; faltava decidir quais campos extrair, o que pertence à Engine pra não acoplar o motor genérico a nomes de campo específicos de plugin). `tests/test_workflow_engine.py::test_correlation_fields_from_params_surface_on_log_events_ac16`, `::test_no_correlacao_key_when_no_matching_field_present_ac17`, `::test_correlation_disabled_by_default_ac19_style_backcompat` — `python -m pytest tests/test_workflow_engine.py -q` → 8 passed |

Status values: `todo` → `doing` → `done`.

Full suite: `python -m pytest -q` → **57 passed** (2026-09-03). `python -m compileall .` → exit 0. `ruff check .` → All checks passed. `ruff format --check .` → 61 files already formatted.

## Coverage Check

Confirm manually before implementing:

- Every AC referenced by at least one task? yes (AC-01 a AC-20 cobertas por T-1 a T-7)
- Every task linked to an AC? yes

**Smoke-test manual (2026-09-03)**: `examples/implementar-historia-sdd.yaml` carregado
via `FileSystemPluginRegistry('./plugins').discover()` + `YamlJsonChainLoader().load(...)`
reais (não mocks) — os 4 plugins são descobertos (`claude_code_runner`, `git_pr`,
`shell_script_runner`, `workspace_setup`), `vars.historia_id`/`vars.branch_name` são
resolvidos corretamente em todas as etapas, e `{{ summary }}`/`{{ docs_referenced }}`
ficam intactos para o `git_pr` resolver em runtime. Não foram invocados `claude`/`gh`/
`git`/`docker` de verdade nesta sessão (exigiria repositório/PR reais) — cobertura de
unidade (57 testes, subprocess sempre injetado/fake) é a evidência de comportamento;
uma execução real ponta a ponta fica para quando houver um repositório-alvo e servidor
MCP configurados.
