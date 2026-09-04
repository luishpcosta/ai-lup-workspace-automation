# Tasks: API HTTP e Monitoria de Workflows (workflow serve)

**Feature ID:** 004-api-http-monitoria
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-04

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades `ADR-004-AT-0N` em `adr/ADR-004-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | Adicionar subparser `serve` em `cli.py::build_parser()` (`--port`, `--plugins-dir`, `--watch-dir`, `--max-parallel`, `--correlation-keys`) e dispatch em `main()`, sem alterar `cmd_run`/`cmd_run_many` (ADR-004-AT-01) | AC-01 | done | `src/workflow_engine/adapters/cli.py` (subparser `serve`, dispatch em `main()`); `tests/test_http_api.py::test_serve_subcommand_does_not_disturb_run_or_run_many_ac01` |
| T-2 | Implementar `ServerState.trigger()` em `http_api.py`: valida config, rejeita disparo duplicado concorrente do mesmo `chain_name`, submete ao `ThreadPoolExecutor`; rota `POST /runs` (ADR-004-AT-02) (depende de T-1) | AC-02, AC-03, AC-04 | done | `tests/test_http_api.py::test_post_runs_is_async_and_completes_in_background_ac02`, `::test_post_runs_rejects_invalid_config_ac03`, `::test_post_runs_rejects_duplicate_concurrent_trigger_ac04`. **Bug real achado e corrigido**: `YamlJsonChainLoader` não checava existência do arquivo — `workflow run <inexistente>` quebrava com `FileNotFoundError` cru em vez de erro limpo; corrigido na fonte (beneficia `run`/`run-many`/`serve`), teste de regressão em `test_yaml_json_chain_loader.py`. Também corrigido: FastAPI aninha `HTTPException.detail` sob `"detail"` por padrão — exception handler customizado devolve `{"error": {...}}` plano, batendo com o contrato documentado |
| T-3 | Implementar `list_runs()`/`get_run_detail()` (leitura direta via `sqlite3` em `--watch-dir`) e rotas `GET /runs`, `GET /runs/{chain_name}` (com `?include=io`) (ADR-004-AT-03) (depende de T-2) | AC-05, AC-06, AC-07 | done | `tests/test_http_api.py::test_get_runs_sees_executions_from_any_source_ac05` (prova real: um run criado direto via Engine, simulando `workflow run` no terminal, aparece ao lado de um disparado pela API), `::test_get_run_detail_hides_io_by_default_ac06`, `::test_get_run_detail_unknown_chain_ac07` |
| T-4 | Implementar `ServerState.cancel()` (cancela via `Future.cancel()` se ainda não iniciou; distingue já-em-execução / de-outro-processo / desconhecido) e rota `POST /runs/{chain_name}/cancelar` (ADR-004-AT-04) (depende de T-2) | AC-08, AC-09, AC-09b, AC-10 | done | `tests/test_http_api.py::test_cancel_queued_run_succeeds_ac08` (concorrência real via arquivos-marcador, mesma técnica de `test_cli_run_many.py`), `::test_cancel_running_run_is_refused_honestly_ac09`, `::test_cancel_run_from_another_process_is_refused_ac09b`, `::test_cancel_unknown_chain_ac10` |

Status values: `todo` → `doing` → `done`.

Full suite: `python -m pytest -q` → **77 passed** (2026-09-04). `ruff check .` → All checks passed. `ruff format --check .` → 92 files already formatted.

## Coverage Check

Confirm manually before implementing:

- Every AC referenced by at least one task? yes (AC-01 a AC-10/AC-09b cobertas por T-1 a T-4)
- Every task linked to an AC? yes
