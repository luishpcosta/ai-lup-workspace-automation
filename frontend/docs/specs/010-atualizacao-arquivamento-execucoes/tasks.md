# Tasks: Atualização automática do painel/detalhe + arquivamento de execuções

**Feature ID:** 010-atualizacao-arquivamento-execucoes
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-07

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades de `adr/ADR-011-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | `http_api.py`: `_ensure_archived_column` (migração aditiva idempotente) + `set_run_archived(watch_dir, chain_name, archived)` (depende de nada) | AC-01, AC-04 | done | `test_archive_run_on_preexisting_db_without_archived_column_adr011_ac01` |
| T-2 | `http_api.py`: rotas `POST /runs/{chain_name}/arquivar` e `.../desarquivar` (depende de T-1) | AC-02, AC-03, AC-04, AC-05 | done | `test_archive_and_unarchive_run_are_idempotent_adr011_ac02_ac03`, `test_archive_and_unarchive_unknown_chain_ac04` |
| T-3 | `http_api.py`: `list_runs` ganha `archived` (filtro + campo no item); rota `GET /runs` ganha query param `archived` (depende de T-1) | AC-06 | done | `test_get_runs_default_excludes_archived_adr011_ac06` |
| T-4 | `http_api.py`: `get_run_detail` inclui `archived` no corpo (depende de T-1) | AC-07 | done | `test_get_run_detail_includes_archived_field_adr011_ac07` |
| T-5 | `backend/tests/test_http_api.py`: testes para T-1 a T-4 (migração em `.db` pré-existente, arquivar/desarquivar idempotentes, 404, filtro em `GET /runs`, `archived` em `GET /runs/{chain_name}`) | AC-01 a AC-07 | done | `python -m pytest` → 132/132 passed (5 novos); `ruff check`/`format` limpos |
| T-6 | `apiClient.js`: `getRuns({ archived } = {})` (retrocompatível), `archiveRun(chainName)`, `unarchiveRun(chainName)` (depende de T-2, T-3) | AC-02, AC-03, AC-06 | done | `src/lib/apiClient.test.js`, describe `apiClient — arquivamento (ADR-011)` (4 testes novos) |
| T-7 | `RunsList.jsx`: card/filtro "Arquivadas" na `summary-strip`, botão "Arquivar"/"Desarquivar" por linha conforme o filtro ativo (depende de T-6) | AC-13, AC-14 | done | `src/components/RunsList.test.jsx`, describe `RunsList — arquivamento (ADR-011-AC-13/AC-14)`; verificado num navegador real (ver T-12) |
| T-8 | `RunsList.jsx`: polling (`setTimeout` recursivo) enquanto houver `running`/`pending` na última resposta; cancelado no cleanup (depende de nada, independente de T-7) | AC-08, AC-09 | done | `src/components/RunsList.test.jsx`, describe `RunsList — atualização automática (ADR-011-AC-08/AC-09)` (fake timers) |
| T-9 | `RunDetail.jsx`: ação "Arquivar"/"Desarquivar" no cabeçalho, ao lado do status geral (depende de T-6) | AC-15 | done | `src/components/RunDetail.test.jsx`, describe `RunDetail — arquivamento (ADR-011-AC-15)`; verificado num navegador real (ver T-12) |
| T-10 | `RunDetail.jsx`: polling (`setTimeout` recursivo) enquanto `detail.status` for `running`/`pending`; cancelado no cleanup/troca de `chainName` (depende de nada, independente de T-9) | AC-10, AC-11, AC-12 | done | `src/components/RunDetail.test.jsx`, describe `RunDetail — atualização automática (ADR-011-AC-10/AC-11)` (fake timers) |
| T-11 | Testes novos/atualizados do frontend (`RunsList.test.jsx`, `RunDetail.test.jsx`, `apiClient.test.js`) para T-6 a T-10 | AC-08 a AC-15 | done | Ver evidências por task acima |
| T-12 | Verificação de regressão: suíte completa do frontend e do backend + verificação real (backend + vite reais, uma execução observada avançando sem clique manual) | AC-01 a AC-15 | done | Frontend: `npm test` → **101 passed** (15 arquivos); `npm run lint` → limpo; `npm run build` → ok. Backend: `python -m pytest` → **132 passed**; `ruff check`/`format` → limpos. **Verificado num navegador real** (backend real porta 8123 + vite dev server real porta 5183, chain de 2 etapas com `sleep` real): painel avançou de "Em execução" para "Concluído" sozinho, sem clique em "Atualizar" (AC-08); tela de detalhe avançou "passo-2 Em execução" → ambas etapas "Concluído" sozinha (AC-10/AC-11); arquivar no detalhe e na listagem, aba "Arquivadas", e desarquivar, todos confirmados visualmente de ponta a ponta (AC-13/AC-14/AC-15) |

Status values: `todo` → `doing` → `done`.

## Coverage Check

- Every AC referenced by at least one task? yes (AC-01 a AC-15 — ver tabela acima)
- Every task linked to an AC? yes
- Full suite: frontend `npm test` → **101 passed** (15 arquivos), `npm run lint` → limpo,
  `npm run build` → ok; backend `python -m pytest` → **132 passed**, `ruff check`/`format` →
  limpos (2026-09-07). Verificação real ponta a ponta em navegador real (ver T-12).
