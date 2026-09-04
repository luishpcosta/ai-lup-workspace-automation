# Tasks: Execuções Paralelas Independentes (run-many)

**Feature ID:** 003-execucoes-paralelas-independentes
**Phase:** Tasks
**Plan:** ./plan.md
**Last updated:** 2026-09-04

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades `ADR-003-AT-0N` em `adr/ADR-003-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | Adicionar subparser `run-many` em `build_parser()` (`configs` nargs+, `--plugins-dir`, `--db-dir`, `--max-parallel`, `--correlation-keys`) (ADR-003-AT-01) | AC-01 | done | `src/workflow_engine/adapters/cli.py::build_parser` |
| T-2 | Implementar validação do lote em `cmd_run_many`: carregar/validar todos os configs antes de disparar qualquer execução; rejeitar `chain.name` duplicado no lote; config inválido isolado não bloqueia os demais (ADR-003-AT-01) (depende de T-1) | AC-01, AC-02, AC-03 | done | `tests/test_cli_run_many.py::test_duplicate_chain_name_blocks_whole_batch_before_running_ac02`, `::test_invalid_config_does_not_block_valid_ones_ac03` |
| T-3 | Implementar disparo concorrente via `ThreadPoolExecutor(max_workers=--max-parallel)`, um `WorkflowEngine` novo por thread com `SqliteStateStore(db_dir/chain.name.db)` isolado (ADR-003-AT-02, AT-03) (depende de T-2) | AC-04, AC-05, AC-06, AC-07 | done | `tests/test_cli_run_many.py::test_respects_max_parallel_cap_ac04_ac05` (concorrência real, `time.sleep`, teto medido via `peak_seen`), `::test_isolated_state_store_survives_and_resumes_per_chain_ac06_ac07` |
| T-4 | Implementar coleta de resultados (`as_completed`), resumo final por execução e exit code (0 se todas completaram, 1 se alguma falhou); falha de uma execução não cancela as demais (ADR-003-AT-04) (depende de T-3) | AC-08, AC-09, AC-10 | done | `tests/test_cli_run_many.py::test_runs_independent_chains_and_reports_summary_ac01_ac08`, `::test_one_failure_does_not_cancel_others_ac09_ac10` |

Status values: `todo` → `doing` → `done`.

Full suite: `python -m pytest -q` → **65 passed** (2026-09-04). `python -m compileall .` → exit 0. `ruff check .` → All checks passed. `ruff format --check .` → 79 files already formatted.

## Coverage Check

Confirm manually before implementing:

- Every AC referenced by at least one task? yes (AC-01 a AC-10 cobertas por T-1 a T-4)
- Every task linked to an AC? yes
