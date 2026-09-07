# Tasks: Refinamentos de UX — Tema, Knowledge Bases e Stream Legível

**Feature ID:** 009-refinamentos-ux-stream-legivel
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-07

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades de `adr/ADR-010-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | `App.jsx`/`index.css`: reposicionar `ThemeToggle` como último item de `.topbar__actions`, com separação visual do grupo de botões (depende de nada) | AC-01 | done | Verificado visualmente no navegador (backend + vite reais, porta 8123/5183): alternador aparece à direita de "Atualizar"/"Configurações", separado por divisor |
| T-2 | `package.json`: adiciona dependência `react-select`; `SpecPicker.jsx` reescrito sobre `react-select` (`isMulti`), mesmo contrato de props (`id`/`value`/`onChange`), textos renomeados para "Knowledge Base(s)" (depende de nada) | AC-02, AC-03 | done | `src/components/SpecPicker.test.jsx` (5 testes); verificado visualmente (combobox em barra, busca, chips removíveis, claro e escuro) |
| T-3 | `index.css`: remove a regra de checkbox-list antiga, adiciona overrides `.select__*` (claro/escuro) para o tema do react-select (depende de T-2) | AC-02 | done | Verificação visual (claro e escuro) — ver T-2 |
| T-4 | `claude-implementar-local.yaml`: `docs_referenced.label` → "Knowledge Bases" (depende de nada) | AC-04 | done | `curl http://127.0.0.1:8123/workflows` real confirmou `"label":"Knowledge Bases"`; `DynamicParamsForm.test.jsx` |
| T-5 | `backend/adapters/http_api.py::get_run_detail`: acrescenta `plugin` por item de `steps[]`, resolvido do YAML via `config_path`; `null` se não recarregável (depende de nada) | AC-08, AC-09 | done | `backend/tests/test_http_api.py::test_get_run_detail_includes_plugin_per_step_adr010_ac08`, `::test_get_run_detail_plugin_is_null_when_config_missing_adr010_ac08` |
| T-6 | `lib/claudeStream.js` (novo): parser de linhas `stream-json` → turnos (texto/tool/summary); nunca lança para linha não reconhecida (depende de nada) | AC-05, AC-07 | done | `src/lib/claudeStream.test.js` (8 testes) |
| T-7 | `StreamPanel.jsx` redesenhado: recebe `plugin`; registro de formatadores; leitura formatada por padrão quando há formatador; alternador "Ver log bruto"/"Ver leitura formatada"; fallback para bruto sem formatador/linha inválida (depende de T-5, T-6) | AC-05, AC-06, AC-07 | done | `src/components/StreamPanel.test.jsx` (7 testes, incluindo os 4 novos de leitura formatada/toggle/fallback) |
| T-8 | `RunDetail.jsx`: acha o step `running` em `detail.steps` e repassa seu `plugin` para `StreamPanel` (depende de T-5) | AC-05 | done | `src/components/RunDetail.test.jsx` (5 testes, sem regressão); verificado visualmente num run concluído (sem step `running` → sem badge, comportamento anterior preservado) |
| T-9 | Atualiza testes existentes afetados (`SpecPicker.test.jsx`, `DynamicParamsForm.test.jsx`, `StreamPanel.test.jsx`, `App.test.jsx`) e testes novos (`claudeStream.test.js`, `test_http_api.py` para `plugin`) | AC-01 a AC-09 | done | Ver evidências por task acima |
| T-10 | Verificação de regressão: suíte completa do frontend e do backend | AC-01 a AC-09 | done | Frontend: `npm test` → **89 passed** (15 arquivos); `npm run lint` → limpo; `npm run build` → ok. Backend: `python -m pytest` → **127 passed**; `ruff check` → limpo. Verificação real no navegador com backend real subido (porta 8123) e vite dev server real (porta 5183) |

Status values: `todo` → `doing` → `done`.

## Coverage Check

- Every AC referenced by at least one task? yes (AC-01 a AC-09 — ver tabela acima)
- Every task linked to an AC? yes
- Full suite: frontend `npm test` → **89 passed** (15 arquivos), `npm run lint` → limpo,
  `npm run build` → ok; backend `python -m pytest` → **127 passed**, `ruff check` →
  limpo (2026-09-07).
