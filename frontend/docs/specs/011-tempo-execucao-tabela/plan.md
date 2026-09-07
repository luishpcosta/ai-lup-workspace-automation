# Plan: Tempo de execução na tabela de execuções

**Feature ID:** 011-tempo-execucao-tabela
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-07

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Decisão completa, alternativas e riscos em
`adr/ADR-012-tempo-execucao-tabela.md`. Contrato do lado `motor-workflow` é pequeno o
bastante para não abrir spec própria nesse contexto (mesmo padrão já usado por
ADR-010/ADR-011) — documentado aqui.

**Backend**: `duration_seconds` (inteiro, segundos, ou `null`) calculado inline em
`http_api.py`, reaproveitando `created_at`/`updated_at`/`status` já lidos do `.db`
por `list_runs`/`get_run_detail` — sem query adicional, sem novo modelo Pydantic
(ambos os endpoints já retornam dicts simples). Para status terminal, é
`updated_at - created_at` (fixo). Para `running`/`pending`, é `now() - created_at`
(recalculado a cada request, já que `updated_at` fica parado no último step
concluído enquanto a execução está ativa). Timestamp ausente/não-parseável produz
`null` em vez de erro — mesma postura defensiva de `_step_plugins_by_name`
(ADR-010).

**Frontend**: nova coluna "Duração" em `RunsList.jsx`, entre "Status" e
"Atualizado", lendo `run.duration_seconds` via um novo `formatDuration(seconds)` em
`lib/format.js`. Nenhum polling novo: a coluna só se beneficia do `setTimeout`
recursivo que `RunsList` já roda enquanto há execução `running`/`pending`
(ADR-011-AT-04) — cada nova resposta desse polling já traz um `duration_seconds`
recalculado para execuções ativas.

## Architecture & Components

- `backend/src/workflow_engine/adapters/http_api.py`:
  - `_duration_seconds(status, created_at, updated_at) -> int | None` (novo,
    privado, perto de `_step_plugins_by_name`) — FR-1, FR-2, FR-3, NFR-1.
  - `list_runs(...)` — adiciona `"duration_seconds": _duration_seconds(...)` ao dict
    de cada item, usando os valores já desempacotados da row — AC-01.
  - `get_run_detail(...)` — mesma adição ao dict de retorno, usando os valores já
    desempacotados de `run_row` — AC-02.
- `backend/tests/test_http_api.py`:
  - Atualizar as duas asserções de conjunto fechado existentes
    (`test_get_run_detail_includes_plugin_per_step_adr010_ac08`,
    `test_get_run_detail_includes_archived_field_adr011_ac07`) para incluir
    `"duration_seconds"` no `set(detail) == {...}` esperado.
  - Testes novos para AC-01 a AC-05 (ver Tasks).
- `frontend/src/lib/format.js`:
  - `formatDuration(seconds)` (novo, exportado) — formato compacto pt-BR
    (`"45s"` / `"2min 14s"` / `"1h 03min"`), retorna `'—'` para `null`/`undefined`/
    `NaN` — AC-06.
- `frontend/src/components/RunsList.jsx`:
  - Import de `formatDuration`.
  - Novo `<th className="col-duration">Duração</th>` entre os `<th>` de "Status" e
    "Atualizado".
  - Novo `<td className="col-duration">{formatDuration(run.duration_seconds)}</td>`
    entre os `<td>` correspondentes — AC-06, AC-07 (o valor muda sozinho porque a
    linha inteira já é re-renderizada a cada resposta do polling existente).
- `frontend/src/index.css`:
  - `.col-duration` — mesma declaração de `.col-time`, mais `tabular-nums` (dado
    numérico) — sem mudança de comportamento, só estilo.
- `frontend/src/components/RunsList.test.jsx`:
  - Testes novos para AC-06 (renderização formatada) — ver Tasks.

## Data Model

Nenhum campo novo de armazenamento — `duration_seconds` é **derivado em tempo de
leitura** a partir de `workflow_runs.created_at`/`updated_at`, já existentes no
schema do `SqliteStateStore` desde a ADR-002/ADR-003. Nada muda em
`sqlite_state_store.py`.

## Interfaces / Contracts

Contratos alterados, ambos aditivos — publicados em `adr/ADR-012-acs.md` (AC-01,
AC-02):

- `GET /runs` → cada item do array ganha `duration_seconds: number | null`. Todo
  campo existente (`chain_name`, `run_id`, `workflow_name`, `status`, `created_at`,
  `updated_at`, `source_db`, `archived`) mantém nome/tipo.
- `GET /runs/{chain_name}` → corpo ganha `duration_seconds: number | null` no nível
  do run (não por step). Todo campo existente mantém nome/tipo (mesma garantia dada
  pela ADR-010-AC-09/ADR-011-AC-07).

Nenhum outro contrato muda: `POST /runs`, `POST /runs/from-template`,
`GET /workflows`, `GET /workspace/repos`, `GET /runs/{chain_name}/stream`, instrução,
`POST /runs/{chain_name}/cancelar` e as rotas de arquivar/desarquivar (ADR-011)
continuam exatamente como estão.

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-01, AC-02, AC-06 | `http_api.py` (`_duration_seconds`, `list_runs`, `get_run_detail`), `RunsList.jsx` (coluna) |
| FR-2 / AC-04, AC-07 | `http_api.py` (ramo `running`/`pending` usa `now()`), `RunsList.jsx` (reaproveita polling da ADR-011) |
| FR-3 / AC-03 | `http_api.py` (ramo terminal usa `updated_at` fixo) |
| NFR-1 | Nenhuma coluna/tabela nova — só leitura derivada de `created_at`/`updated_at` existentes |
| NFR-2 | `duration_seconds` é aditivo nos dois endpoints — testes de conjunto fechado atualizados, não quebrados |
| NFR-3 | Nenhum polling novo — `RunsList.jsx` não ganha nenhum `useEffect`/timer adicional |

## Constitution Compliance

- **Spec before code** (princípio 1): este plan e a ADR-012 são escritos antes da
  implementação — Tasks gate abaixo precisa passar antes do primeiro commit de
  código desta feature.
- **Contrato REST é do backend** (princípio 5): o campo novo está decidido e
  publicado em `adr/ADR-012-tempo-execucao-tabela.md`, revisitando
  `afeta: [motor-workflow]` — este plan só consome a decisão.
- **Configuração em runtime** (princípio 6): nenhuma mudança nesta feature toca
  configuração de boot.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Onde calcular a duração | Inline em `http_api.py`, na mesma camada que já lê os timestamps do `.db` | Calcular no frontend a partir de `created_at`/`updated_at` já expostos | Evita duplicar a regra condicional (terminal vs. `now()`) em dois lugares; backend já é a fonte única de verdade para campos derivados similares (`archived`, `plugin`) |
| Duração de execução ativa | Recalculada a cada request com `now() - created_at`, sem novo polling | Um mecanismo de push dedicado para duração "ao vivo" | O polling que `RunsList` já faz (ADR-011) é suficiente — cada resposta nova já carrega um valor recalculado |
| Duração por step em `RunDetail` | Fora de escopo nesta feature | Adicionar junto, já que o dado (`started_at`/`finished_at`) está disponível | Usuário pediu especificamente "a tabela"; `RunDetail` exigiria desenho de coluna próprio numa tela separada — fica pronto para uma extensão futura sem mudança de contrato adicional |

## Risks

Nenhum risco novo identificado além dos já cobertos pelas ADRs anteriores — é leitura
pura sobre dado já persistido, sem nova escrita/rota/coluna.
