# Tasks: Implementar em Repositório Local, PR via CI do Repositório-Alvo

**Feature ID:** 007-implementar-local-pr-via-ci
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-06

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades `ADR-008-AT-0N` em `adr/ADR-008-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | `plugins/claude_code_runner.py`: modo `coding_local` (`_CODING_LOCAL_SCHEMA`, `run()` dispatch, `_run_coding_local`, `_coding_local_prompt`) (ADR-008-AT-01) | AC-01, AC-02, AC-03 | done | `tests/test_claude_code_runner_plugin.py::test_coding_local_mode_reads_workspace_path_from_params_and_returns_branch_ac01_ac03`, `::test_coding_local_mode_prefers_workspace_path_from_input_when_present`, `::test_coding_local_mode_without_workspace_path_raises_ac02` |
| T-2 | `plugins/claude_code_runner.py`: regressão — testes existentes de `coding`/`review`/`investigar` continuam passando sem alteração (ADR-008-AT-01) (depende de T-1) | AC-04 | done | Suíte completa **120 passed** (era 113 antes desta feature) — nenhum teste existente de `coding`/`review`/`investigar` alterado |
| T-3 | `plugins/git_pr.py`: ação `confirm_pr` (`import json`, `run()` retorna cedo antes de exigir `title_template`/`body_template`, `_confirm_pr`) (ADR-008-AT-02) | AC-05, AC-06, AC-07, AC-08 | done | `tests/test_git_pr_plugin.py::test_confirm_pr_returns_confirmed_when_pr_exists_ac05`, `::test_confirm_pr_raises_transient_when_no_pr_found_yet_ac06`, `::test_confirm_pr_without_branch_raises_permanently_ac07`, `::test_confirm_pr_transient_gh_failure_is_retriable` |
| T-4 | `plugins/git_pr.py`: regressão — testes existentes de `create_pr`/`update_pr` continuam passando sem alteração (ADR-008-AT-02) (depende de T-3) | AC-09 | done | Mesma suíte completa **120 passed** — nenhum teste existente de `create_pr`/`update_pr` alterado |
| T-5 | `config/workflow_templates/implementar-local.yaml` (novo, `params_schema` + dois `steps:`) (ADR-008-AT-03) (depende de T-1, T-3) | AC-10, AC-12 | done | Arquivo criado; descoberto automaticamente pelo `FileSystemWorkflowTemplateRegistry` já existente (feature `006`) — sem mudança de código para aparecer em `GET /workflows` |
| T-6 | Verificação ponta a ponta (manual, contra `ai-lup-poc-target-cli` real): dispara `implementar-local` via `POST /runs/from-template`, confirma branch criada + push + PR aberta pela CI do repo-alvo + step `confirmar_pr` retornando `confirmed` (depende de T-5) | AC-11 | done | **Verificado de ponta a ponta contra o repositório real**, com confirmação explícita do usuário antes de rodar: `workflow serve --local-repos-root <pai>` real (porta 8010) + `POST /runs/from-template` real (`chain_name: implementar-local--d4384c0a`) contra `ai-lup-poc-target-cli`. Etapa `implementar` completou em ~2m37s (sem clone — usou o checkout local diretamente), reportou `branch: feature/001-example-hello`. Etapa `confirmar_pr` completou na 1ª tentativa, `pr_number: 8`. **Confirmado de forma independente** (não só confiando no plugin): `git branch -a`/`git log origin/feature/001-example-hello` mostram o commit real (`7e4eada`) na branch nova; `gh pr view 8` mostra `state: OPEN`, `body` = literalmente o template da CI do repo-alvo ("PR aberto automaticamente pela CI após `init.sh` passar..."), confirmando que o `git_pr` do motor nunca chamou `create_pr`; `gh pr checks 8` mostra os 2 jobs da CI do repo-alvo (`Valida harness SDD`, `Abre PR automaticamente`) `pass`. PR real: https://github.com/luishpcosta/ai-lup-poc-target-cli/pull/8 |

Status values: `todo` → `doing` → `done`.

Suíte completa: `python -m pytest -q` → **120 passed** (2026-09-06, era 113 antes desta
feature). `python -m compileall .` → exit 0. `ruff check .` → All checks passed.
`ruff format --check .` → 95 files already formatted.

## Coverage Check

- Every AC referenced by at least one task? yes (AC-01 a AC-12 cobertas por T-1 a T-6)
- Every task linked to an AC? yes
