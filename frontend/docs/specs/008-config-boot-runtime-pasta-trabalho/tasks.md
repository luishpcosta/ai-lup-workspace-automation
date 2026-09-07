# Tasks: Configuração de Boot em Runtime e Pasta de Trabalho

**Feature ID:** 008-config-boot-runtime-pasta-trabalho
**Phase:** Verify
**Plan:** ./plan.md
**Last updated:** 2026-09-06

> Small, ordered, independently verifiable tasks derived from `plan.md`.
> **Gate:** every acceptance criterion has ≥1 task, and every task references an AC.
> IDs correspondem às atividades de `adr/ADR-009-acs.md`.

## Tasks

| ID | Task | Satisfies | Status | Evidence |
|---|---|---|---|---|
| T-1 | `public/painel-config.json` (novo); `lib/config.js`: `loadDefaults()`, `getEffectiveConfig()`, `getFieldSources()`, `clearConfig()`, precedência `localStorage` > arquivo > vazio por campo | AC-01, AC-02, AC-03 | done | `src/lib/config.test.js` (12 testes, incluindo arquivo ausente/JSON inválido e precedência campo a campo) |
| T-2 | `main.jsx`: chama `loadDefaults()` antes do primeiro `render` (depende de T-1) | AC-01 | done | `src/lib/config.test.js`; verificado manualmente no navegador (localStorage vazio → painel abre direto, sem tela de configuração) |
| T-3 | `components/SettingsScreen.jsx` redesenhado: campo `reposRoot`, selo "default do arquivo" por campo, remoção de todo `placeholder`, botão "Restaurar defaults do arquivo" (depende de T-1) | AC-04, AC-05 | done | `src/components/SettingsScreen.test.jsx` (7 testes, incluindo verificação explícita de ausência de `placeholder` em todos os campos) |
| T-4 | `lib/apiClient.js::getLocalRepos()`: acrescenta `?root=` quando `reposRoot` está configurado (depende de T-1) | AC-05, AC-06, AC-07 | done | `src/lib/apiClient.test.js` (16 testes, incluindo `?root=` enviado e omitido) |
| T-5 | `backend/adapters/http_api.py::get_local_repos`: parâmetro de consulta opcional `root`, precedência sobre a raiz do processo (depende de nada) | AC-06, AC-07 | done | `backend/tests/test_http_api_templates.py` (4 testes novos: `root` sobrepõe raiz configurada, `root` sem raiz configurada, raiz inexistente → lista vazia, sem `root` → comportamento inalterado) |
| T-6 | `backend/adapters/cli.py`: default de `--local-repos-root` via `LOCAL_REPOS_ROOT`, flag explícita vence a variável (depende de nada) | AC-08 | done | `backend/tests/test_http_api.py::test_serve_local_repos_root_falls_back_to_env_and_flag_wins_adr009_ac08` |
| T-7 | `start-local.sh`: deriva `LOCAL_REPOS_ROOT` do diretório-pai do repo quando não informado; ecoa a raiz em uso (depende de T-6) | AC-08 | done | Revisão manual do script; comportamento equivalente confirmado via `curl http://localhost:8000/workspace/repos` com o backend subido com `LOCAL_REPOS_ROOT` explícito |
| T-8 | Verificação ponta a ponta no navegador: boot sem configuração salva, troca de pasta de trabalho refletindo no seletor sem reiniciar o backend, persistência após reload, tela de configuração sem placeholders | AC-01, AC-04, AC-05 | done | Sessão de verificação manual via automação de navegador (2026-09-06): `localStorage` vazio → painel direto; `?root=` trocado pela tela → seletor lista a árvore nova; reload → raiz preservada |
| T-9 | Verificação de regressão: suíte completa do frontend e do backend | AC-01 a AC-08 | done | Frontend: `npm test` → **75 passed** (14 arquivos); `npm run lint` → limpo. Backend: `python -m pytest` → **125 passed** |

Status values: `todo` → `doing` → `done`.

## Coverage Check

- Every AC referenced by at least one task? yes (AC-01 a AC-08 — ver tabela acima)
- Every task linked to an AC? yes
- Full suite: frontend `npm test` → **75 passed**, `npm run lint` → limpo; backend
  `python -m pytest` → **125 passed** (2026-09-06)
