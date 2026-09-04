# Tasks: Streaming ao Vivo e Interação com o Agente (Claude Code Runner)

**Feature ID:** 005-stream-interacao-agente
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-04

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades `ADR-005-AT-0N` em `adr/ADR-005-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | Reescrever `plugins/claude_code_runner.py`: `Popen` de longa duração via `--input-format/--output-format stream-json --verbose`, contrato externo (`params`/`output`) inalterado (ADR-005-AT-01) | AC-01 | done | `plugins/claude_code_runner.py` (`_run_streaming_session`, `_build_cmd`); `tests/test_claude_code_runner_plugin.py::test_coding_mode_invokes_cli_and_returns_structured_result_ac04_ac05`, `::test_review_mode_starts_fresh_session_ac06_ac07` — 8/8 passed |
| T-2 | Escrita incremental de `session_log_path`, uma linha por evento recebido (ADR-005-AT-02) (depende de T-1) | AC-02, AC-03 | done | `tests/test_claude_code_runner_plugin.py::test_session_log_written_incrementally_ac02`, `::test_failure_still_leaves_transcript_on_disk_ac08` |
| T-3 | Thread de polling do arquivo de instruções, repassando linhas novas pro stdin do processo vivo; para de observar quando a sessão termina (ADR-005-AT-03) (depende de T-1) | AC-04, AC-05 | done | `tests/test_claude_code_runner_plugin.py::test_forwards_pending_instruction_to_stdin_ac04`, `::test_stdin_closed_after_result_event`. **Verificado ao vivo duas vezes**: direto na CLI, e através do plugin reescrito de verdade (script real, instrução "pare e responda X" mudou o `summary` final para "X" — ver `progress.md`) |
| T-4 | `GET /runs/{chain_name}/stream` (SSE) em `http_api.py`: resolve etapa ativa do Claude Code Runner via `.db`+YAML, tail do log até a etapa deixar de estar "running" (ADR-005-AT-04) (depende de T-2) | AC-06, AC-07 | done | `tests/test_http_api_streaming.py::test_stream_tails_active_claude_step_live_and_stops_on_completion_ac06`, `::test_stream_refuses_when_no_active_claude_step_ac07` |
| T-5 | `POST /runs/{chain_name}/instrucoes` em `http_api.py`: mesma resolução de etapa ativa, acrescenta ao arquivo de instruções (ADR-005-AT-05) (depende de T-3) | AC-08, AC-09, AC-10 | done | `tests/test_http_api_streaming.py::test_post_instruction_appends_to_deterministic_file_ac08`, `::test_post_instruction_refuses_when_no_active_claude_step_ac09`. AC-10 coberto implicitamente por todos os testes acima (runs semeados via `SqliteStateStore` direto, nunca via `ServerState.trigger` — ver nota no arquivo de teste) |

Status values: `todo` → `doing` → `done`.

Full suite: `python -m pytest -q` → **85 passed** (2026-09-04). `ruff check .` → All checks passed.

## Coverage Check

Confirm manually before implementing:

- Every AC referenced by at least one task? yes (AC-01 a AC-10 cobertas por T-1 a T-5)
- Every task linked to an AC? yes
