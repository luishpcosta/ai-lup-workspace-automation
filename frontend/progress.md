# Session Progress Log

## Current State

**Last Updated:** 2026-09-04
**Active Feature:** 006-frontend-painel-controle — Painel de Controle Frontend v1 (REST/SSE) — Verify, `done`
**Active SDD Phase:** Verify
**Pending Gate:** Nenhum. Todas as 13 ACs (AC-01 a AC-13) implementadas e verificadas — ver `docs/specs/006-frontend-painel-controle/tasks.md`.

## Status

### What's Done

- [x] Harness SDD criado (`AGENTS.md`, `constitution.md`, `init.sh`, este `progress.md`)
- [x] ADR-006 (com achados de entrevista de UX) movida para `adr/`
- [x] `docs/specs/006-frontend-painel-controle/{spec,plan,tasks}.md` escritas a partir da ADR-006, gate de cobertura fechado (13 ACs, 12 tasks)
- [x] Scaffold real: React 19 + Vite 5 (JS), Vitest + Testing Library, ESLint 9
  (trocado de oxlint/Vite 8 padrão do `create-vite` — binários nativos
  `rolldown`/`oxlint` não carregam no Node 20.17 desta máquina; downgrade
  documentado, não escondido — ver Decisions Made)
- [x] `lib/config.js`, `lib/resolveConfigPath.js`, `lib/apiClient.js` (erro tipado
  conexão/HTTP; `openStream` via `fetch`+`ReadableStream`, não `EventSource`, para
  distinguir 409 de 200)
- [x] `SettingsScreen`, `RunsList` (destaque visual de falha), `RunDetail`
  (tabela por etapa + cancelar), `TriggerForm` (disparo em lote por ID de
  documento de referência), `StreamPanel`, `InstructionBox`
- [x] `CORSMiddleware` em `backend/.../http_api.py::build_app` (única mudança de
  backend; 2 testes de regressão novos, `backend/tests/test_http_api.py`)
- [x] 40/40 testes do frontend passando, `npm run lint`/`npm run build` limpos
- [x] 87/87 testes do backend passando (inclui as 2 novas AC-11), `ruff` limpo
- [x] **Verificação real** (não só mocks): `workflow serve` real (porta 8010) +
  `vite` dev server real (porta 5183) rodando simultaneamente; `curl` com header
  `Origin` real confirmou `access-control-allow-origin: *` e preflight `OPTIONS`
  real confirmou `access-control-allow-methods: GET, POST` — CORS funciona de
  ponta a ponta, não é só suposição de que o middleware está certo

### What's In Progress

- [ ] Nenhuma — feature completa

### What's Next

Nenhuma feature nova especificada ainda. Possível próximo passo (não pedido
ainda): executar o rename pendente de `historia_id` (registrado como decisão
pendente na ADR-006, atravessa vocabulário de ADR-001/002 no backend).

## Open Clarifications

Nenhuma pendente e bloqueante.

## Blockers / Risks

- [ ] Testes desta feature não cobrem um navegador real (sem Playwright neste
  ambiente) — só unidade/integração com `fetch`/stream mockados. A parte que
  não podia ser mockada com confiança (CORS real) foi verificada com processos
  reais (ver acima); o que fica sem cobertura automática é só a interação
  visual (layout, destaque CSS).
- [ ] `npm audit` reporta 5 vulnerabilidades (3 moderate, 1 high, 1 critical) —
  todas do mesmo problema conhecido do `esbuild` do Vite 5 (dev server aceita
  requisição de qualquer site enquanto roda localmente, GHSA-67mh-4wv8-2f99).
  Afeta só o dev server local, não o build de produção. Aceito nesta versão
  (mesma postura de "uso local/individual, sem auth" já decidida na ADR-006);
  revisitar ao considerar Vite 6+ quando o Node desta máquina for atualizado.

## Decisions Made

- **Vite 8 (`rolldown`) e `oxlint` trocados por Vite 5 e ESLint 9**: description
  — o `create-vite` padrão instalou Vite 8 + `oxlint`, ambos com binário nativo
  que não carrega no Node 20.17.0 desta máquina (`EBADENGINE`, requer
  `^20.19.0 || >=22.12.0`). Vite 5 + ESLint 9 (`^18.18.0 || ^20.9.0`) funcionam
  de verdade nesta máquina — testado (`npm run build`/`npm run lint` reais).
  - Context: descoberto ao rodar `npm run build` pela primeira vez (erro real
    de módulo nativo ausente, não suposição).
  - Constitution impact: `constitution.md` já reflete React 19 + Vite 5 +
    Vitest + ESLint como stack real (não mais "a definir").
- **Disparo em lote atualiza a listagem, não navega automaticamente para
  detalhe**: com vários IDs disparados de uma vez, não há "o" item para
  navegar — `TriggerForm` chama `onDispatched()` ao final do lote, que só
  força um refresh de `RunsList`. Corrigido também o texto de `spec.md`
  AC-06, que ainda dizia "leva ao detalhe" (divergência da própria ADR-006-acs.md).

## Evidence of Completion

- [x] AC-01 a AC-13 verificadas: `docs/specs/006-frontend-painel-controle/tasks.md`
  (T-1 a T-12, todas `done`, evidência por tarefa)
- [x] Coverage check limpo: toda AC tem ≥1 task e toda task referencia uma AC
- [x] `npm test` → 40 passed; `npm run build` → ok; `npm run lint` → limpo
- [x] `python -m pytest` (backend) → 87 passed; `ruff check`/`format` → limpos
- [x] Verificação real ponta a ponta (processos reais, não `TestClient`/mock) —
  ver "What's Done" acima

## Notes for Next Session

Feature 006 está completa e verificada. Se uma nova demanda de frontend
aparecer, a próxima ADR (em qualquer contexto) é `ADR-007` (numeração global,
ver `../CONTEXT-MAP.md`). O rename pendente de `historia_id` (ADR-006,
Consequências) segue em aberto, sem prazo definido.
