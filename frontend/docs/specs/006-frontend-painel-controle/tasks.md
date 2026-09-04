# Tasks: Painel de Controle Frontend v1 (REST/SSE)

**Feature ID:** 006-frontend-painel-controle
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-04

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades `ADR-006-AT-0N` em `../../adr/ADR-006-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | Scaffold Vite+React (JS) em `frontend/`; configurar Vitest + Testing Library (jsdom); substituir o placeholder de `init.sh` por comandos reais (ADR-006-AT-01) | AC-01 | done | `frontend/package.json`, `vite.config.js`, `init.sh` (`npm install && npm test && npm run build && npm run lint`). Downgrade real de Vite 8→5 e oxlint→ESLint 9 por incompatibilidade de engine com Node 20.17 nesta máquina (`rolldown`/`oxlint` sem binário nativo) — documentado, não escondido. |
| T-2 | `lib/config.js` (get/set `localStorage`) + `lib/apiClient.js` base (`getRuns`, `getRunDetail`, `createRun`, `postInstruction`, `cancelRun`, erro tipado conexão/HTTP) (ADR-006-AT-01) (depende de T-1) | AC-01, AC-03 | done | `src/lib/config.test.js` (4 testes), `src/lib/apiClient.test.js` (11 testes) — 15/15 passed |
| T-3 | `SettingsScreen.jsx` + wiring em `App.jsx` (forçada quando config vazia) (ADR-006-AT-01) (depende de T-2) | AC-01, AC-02 | done | `src/components/SettingsScreen.test.jsx` (2 testes), `src/App.test.jsx::forces the settings screen...` — 3/3 passed |
| T-4 | `RunsList.jsx`: `GET /runs`, destaque visual passivo quando status indica falha (ADR-006-AT-02) (depende de T-2) | AC-04, AC-12 | done | `src/components/RunsList.test.jsx` (4 testes, incluindo destaque visual e erro de conexão) — 4/4 passed |
| T-5 | `RunDetail.jsx`: `GET /runs/{chain_name}`, tabela por etapa, erro claro se 404 (ADR-006-AT-02) (depende de T-4) | AC-05 | done | `src/components/RunDetail.test.jsx` (5 testes) — 5/5 passed |
| T-6 | `lib/resolveConfigPath.js` (função pura, testada isoladamente) (ADR-006-AT-03) (depende de T-2) | AC-06 | done | `src/lib/resolveConfigPath.test.js` (3 testes) — 3/3 passed |
| T-7 | `TriggerForm.jsx`: um ou mais IDs, resolve e dispara por item, erro de um item não cancela os demais (ADR-006-AT-03) (depende de T-6) | AC-06, AC-13 | done | `src/components/TriggerForm.test.jsx` (3 testes, incluindo lote com 1 item inválido) — 3/3 passed |
| T-8 | `apiClient.js::openStream` (fetch + ReadableStream, distingue 200/409/erro de conexão) + `StreamPanel.jsx` (ADR-006-AT-04) (depende de T-5) | AC-07, AC-08 | done | `src/lib/apiClient.test.js` (2 testes de `openStream`), `src/components/StreamPanel.test.jsx` (3 testes) |
| T-9 | `InstructionBox.jsx` + `apiClient.js::postInstruction` wiring, erro 409 inline (ADR-006-AT-04) (depende de T-8) | AC-09 | done | `src/components/InstructionBox.test.jsx` (2 testes) — 2/2 passed |
| T-10 | Botão de cancelar em `RunDetail.jsx` + `apiClient.js::cancelRun`, refletindo os 3 estados documentados (ADR-006-AT-05) (depende de T-5) | AC-10 | done | `src/components/RunDetail.test.jsx::RunDetail — cancel` (3 casos parametrizados: cancelled/already_running/not_cancellable) |
| T-11 | `CORSMiddleware` em `backend/src/workflow_engine/adapters/http_api.py::build_app`; teste de regressão em `backend/tests/test_http_api.py` (ADR-006-AT-06) | AC-11 | done | `backend/tests/test_http_api.py::test_cors_allows_cross_origin_requests_from_the_frontend_ac11`, `::test_cors_preflight_allows_post_with_content_type_ac11` — 2/2 passed; suíte completa do backend 87/87 |
| T-12 | Verificação real ponta a ponta: `npm test`/`npm run build` no frontend, `python -m pytest` no backend, `workflow serve` real + `vite` dev server real confirmando CORS cross-origin de verdade (não só suposição) | AC-01 a AC-13 (regressão) | done | Frontend: 40/40 testes, `npm run lint` limpo, `npm run build` ok. Backend: 87/87 testes, `ruff check`/`format` limpos. **Real, não só mock**: `workflow serve` real na porta 8010 + `vite` dev server real na porta 5183, ambos processos simultâneos; `curl -i -H "Origin: http://localhost:5173" http://localhost:8010/runs` → `access-control-allow-origin: *`; preflight `OPTIONS` real → `access-control-allow-methods: GET, POST`. Processos encerrados após a verificação. |

Status values: `todo` → `doing` → `done`.

## Coverage Check

- Every AC referenced by at least one task? yes (AC-01 a AC-13 — ver tabela acima)
- Every task linked to an AC? yes
- Full suite: frontend `npm test` → **40 passed** (2026-09-04); backend `python -m pytest` → **87 passed** (2026-09-04, inclui as 2 novas AC-11)
