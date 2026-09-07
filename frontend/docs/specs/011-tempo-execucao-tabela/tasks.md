# Tasks: Tempo de execução na tabela de execuções

**Feature ID:** 011-tempo-execucao-tabela
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-07

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades de `adr/ADR-012-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | `http_api.py`: helper `_duration_seconds(status, created_at, updated_at)` (depende de nada) | AC-03, AC-04, AC-05 | done | `_duration_seconds` em `http_api.py`, perto de `_step_plugins_by_name` |
| T-2 | `http_api.py`: `list_runs` inclui `duration_seconds` por item (depende de T-1) | AC-01 | done | `test_duration_seconds_is_fixed_for_completed_run_adr012_ac01_ac02_ac03` |
| T-3 | `http_api.py`: `get_run_detail` inclui `duration_seconds` no corpo (depende de T-1) | AC-02 | done | mesmo teste acima (verifica os dois endpoints) |
| T-4 | `backend/tests/test_http_api.py`: atualizar as duas asserções de conjunto fechado existentes + testes novos para AC-01 a AC-05 | AC-01 a AC-05 | done | `test_duration_seconds_is_fixed_for_completed_run_adr012_ac01_ac02_ac03`, `test_duration_seconds_for_running_run_never_decreases_adr012_ac04`, `test_duration_seconds_is_null_when_created_at_corrupted_adr012_ac05`; `python -m pytest` → 135/135 passed (3 novos); `ruff check`/`format` limpos |
| T-5 | `frontend/src/lib/format.js`: `formatDuration(seconds)` (depende de nada) | AC-06 | done | `src/components/RunsList.test.jsx`, describe `RunsList — tempo de execução (ADR-012-AC-06)` |
| T-6 | `frontend/src/components/RunsList.jsx`: coluna "Duração" entre "Status" e "Atualizado" (depende de T-5, T-2) | AC-06, AC-07 | done | mesmo describe acima; verificado num navegador real (ver T-9) |
| T-7 | `frontend/src/index.css`: `.col-duration` (depende de T-6) | AC-06 | done | verificado visualmente num navegador real (ver T-9) |
| T-8 | `frontend/src/components/RunsList.test.jsx`: testes novos para AC-06 | AC-06 | done | 2 testes novos: renderiza `"2min 14s"` para `duration_seconds: 134`; renderiza `"—"` quando o campo está ausente |
| T-9 | Verificação de regressão: suíte completa do frontend e do backend + verificação real (backend + vite reais, execução observada com a coluna "Duração" incrementando sozinha via o polling já existente) | AC-01 a AC-07 | done | Frontend: `npm test` → **103 passed** (15 arquivos); `npm run lint` → limpo; `npm run build` → ok. Backend: `python -m pytest` → **135 passed**; `ruff check`/`format` → limpos. **Verificado num navegador real** (backend real porta 8000 + vite dev server real porta 5173): 4 execuções reais já existentes no `.db` mostraram a coluna "Duração" com valores batendo exatamente com `updated_at - created_at` (ex.: 415s → "6min 55s", 277s → "4min 37s"); uma execução real nova (`shell_script_runner` com `sleep 20`, sem mock) disparada diretamente no mesmo `watch_dir` do backend em execução apareceu como "Em execução" com "13s" logo após o disparo, e — sem nenhum clique em "Atualizar" — avançou sozinha para "Concluído" com "20s" fixo (valor exato do `sleep`), confirmando tanto o cálculo `now() - created_at` durante a execução quanto o valor fixo ao terminar, e que a coluna se beneficia do polling já existente da ADR-011 sem nenhum mecanismo novo |

Status values: `todo` → `doing` → `done`.

## Coverage Check

- Every AC referenced by at least one task? yes (AC-01 a AC-07 — ver tabela acima)
- Every task linked to an AC? yes
- Full suite: frontend `npm test` → **103 passed** (15 arquivos), `npm run lint` → limpo,
  `npm run build` → ok; backend `python -m pytest` → **135 passed**, `ruff check`/`format` →
  limpos (2026-09-07). Verificação real ponta a ponta em navegador real (ver T-9).
