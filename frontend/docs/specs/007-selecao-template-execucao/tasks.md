# Tasks: Disparo por Template — Specs Remotas e Repositórios Locais

**Feature ID:** 007-selecao-template-execucao
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-06

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades relevantes de `../../../backend/adr/ADR-007-acs.md`
> (componente frontend desta feature).

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | `lib/config.js`: troca `configDir` por `specsBaseUrl`; `SettingsScreen.jsx`: campo `specsBaseUrl` no lugar de `configDir` | AC-01, AC-02 | done | `src/lib/config.test.js` (5 testes), `src/components/SettingsScreen.test.jsx` (2 testes) |
| T-2 | `lib/apiClient.js`: `getWorkflows()`, `getLocalRepos()`, `createRunFromTemplate(templateId, params)`; remove `createRun` (sem chamador) (depende de T-1) | AC-03, AC-05, AC-07, AC-08 | done | `src/lib/apiClient.test.js` (14 testes, incluindo `GET /workflows`, `GET /workspace/repos`, `POST /runs/from-template` 202/400/404) |
| T-3 | `lib/specsClient.js` (novo): `fetchSpecsIndex`/`fetchSpecContent`, fetch direto, `SpecsError` próprio (depende de T-1) | AC-06 | done | `src/lib/specsClient.test.js` (5 testes) |
| T-4 | `components/TemplateSelector.jsx` (novo): `GET /workflows`, seleção + descrição (depende de T-2) | AC-03 | done | `src/components/TemplateSelector.test.jsx` (3 testes) |
| T-5 | `components/RepoPicker.jsx` (novo): `GET /workspace/repos`, lista vazia explicada (depende de T-2) | AC-05 | done | `src/components/RepoPicker.test.jsx` (3 testes) |
| T-6 | `components/SpecPicker.jsx` (novo): fetch direto via `specsClient.js`, multi-seleção por checkbox (depende de T-3) | AC-06 | done | `src/components/SpecPicker.test.jsx` (3 testes) |
| T-7 | `components/DynamicParamsForm.jsx` (novo): um campo por `params_schema`, delega `source` para `RepoPicker`/`SpecPicker` (depende de T-5, T-6) | AC-04 | done | `src/components/DynamicParamsForm.test.jsx` (4 testes) |
| T-8 | `components/TriggerForm.jsx` reescrito: orquestra `TemplateSelector`+`DynamicParamsForm`, dispara via `createRunFromTemplate`, erro inline, `onDispatched` preservado (depende de T-4, T-7) | AC-07, AC-08, AC-09 | done | `src/components/TriggerForm.test.jsx` (5 testes, incluindo `implementar-historia-sdd` selecionável na mesma tela e erro `invalid_params` exibido inline) |
| T-9 | Remove `lib/resolveConfigPath.js` + teste (órfãos após T-8) (depende de T-8) | — (limpeza) | done | Arquivos removidos; suíte completa sem referências restantes (`npm run lint` limpo) |
| T-10 | Verificação de regressão: `RunsList`/`RunDetail`/`StreamPanel`/`InstructionBox`/`App.jsx` sem mudança de contrato; suíte completa + build + lint | AC-10 | done | `src/App.test.jsx` (3 testes), `src/components/{RunsList,RunDetail,StreamPanel,InstructionBox}.test.jsx` inalterados e passando — suíte completa **61 passed**; `npm run build` ok; `npm run lint` limpo |

Status values: `todo` → `doing` → `done`.

## Coverage Check

- Every AC referenced by at least one task? yes (AC-01 a AC-10 — ver tabela acima)
- Every task linked to an AC? yes (T-9 é limpeza pura, sem AC própria, mas depende de T-8 e é pré-requisito do estado final verificado em T-10)
- Full suite: `npm test` → **61 passed** (2026-09-06, era 40 antes desta feature); `npm run build` → ok; `npm run lint` → limpo
