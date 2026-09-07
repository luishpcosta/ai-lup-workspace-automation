# Plan: Atualização automática do painel/detalhe + arquivamento de execuções

**Feature ID:** 010-atualizacao-arquivamento-execucoes
**Phase:** Verify
**Spec:** ./spec.md
**Last updated:** 2026-09-07

> HOW the spec will be implemented. Every functional requirement in `spec.md` must be addressed here. Cite `constitution.md` for any constraint you rely on.

## Technical Approach

Duas frentes independentes, implementadas juntas por terem sido pedidas na mesma
demanda — decisão completa, alternativas e riscos em
`adr/ADR-011-atualizacao-automatica-arquivamento-execucoes.md`.

**FR-3/FR-4 (arquivamento, motor-workflow + frontend)**: `archived_at` (nullable)
persiste no próprio arquivo SQLite por chain (`<chain_name>.db`), lido/escrito
direto via `sqlite3` em `http_api.py` — mesmo padrão de desacoplamento já usado por
`list_runs`/`get_run_detail` (ADR-004), fora do `StateStorePort`. Uma migração
aditiva (`ALTER TABLE ... ADD COLUMN`, idempotente) roda sob demanda antes de
qualquer leitura/escrita de arquivamento, cobrindo `.db` antigos e novos. Duas rotas
novas (`POST /runs/{chain_name}/arquivar` e `.../desarquivar`), mesmo contrato de
erro 404 de `cancelar`. `GET /runs` ganha `?archived=true` opcional (default:
exclui arquivadas, comportamento de hoje). `GET /runs/{chain_name}` ganha `archived`
(bool), sempre presente.

No frontend, `RunsList` ganha um botão "Arquivar" por linha e um card/filtro
"Arquivadas" na `summary-strip` (mesmo padrão dos cards de status — ADR-006-AC-04);
selecionar o filtro troca a consulta para `GET /runs?archived=true` e troca o botão
por linha para "Desarquivar". `RunDetail` ganha uma ação "Arquivar"/"Desarquivar" no
cabeçalho, ao lado do status geral.

**FR-1/FR-2 (atualização automática, frontend puro)**: `RunsList` e `RunDetail`
passam a reconsultar seus endpoints já existentes (`GET /runs`, `GET
/runs/{chain_name}`) via `setTimeout` recursivo (cada rodada só agenda a próxima a
partir do dado que acabou de chegar — um `setInterval` fixo decidiria com o estado
de uma rodada atrás, ainda não atualizado no instante em que o efeito roda), sem
endpoint novo. `RunsList` só reagenda enquanto a resposta mais recente tiver alguma
execução `running`/`pending`; `RunDetail` só enquanto `detail.status` for
`running`/`pending`. Ambos cancelam o `setTimeout` pendente no cleanup do efeito
(desmontagem ou troca de `chainName`/filtro) — mesmo cuidado já usado no
`AbortController` de
`StreamPanel`/`openStream` (ADR-006). O `refreshToken`/botão manual "Atualizar"
(ADR-006) e o `onDispatched` do `TriggerForm` (ADR-007) continuam existindo
exatamente como hoje — o polling é um gatilho adicional, não uma substituição.

## Architecture & Components

- `backend/src/workflow_engine/adapters/http_api.py`:
  - `_ensure_archived_column(db_file)` (novo, privado) — `ALTER TABLE workflow_runs
    ADD COLUMN archived_at TEXT`, silenciando `sqlite3.OperationalError` de coluna
    já existente — FR-3, FR-4, NFR-4.
  - `list_runs(watch_dir, archived=False)` — filtra por `archived_at IS NULL`
    (default) ou `IS NOT NULL` (`archived=True`); item ganha `archived: bool` — FR-4.
  - `get_run_detail(...)` — inclui `archived: bool` no corpo — FR-3, FR-4.
  - `set_run_archived(watch_dir, chain_name, archived: bool) -> bool` (novo) —
    `UPDATE ... SET archived_at = ?`; retorna `False` se o `.db` não existe — FR-3,
    FR-4.
  - Rotas novas: `POST /runs/{chain_name}/arquivar`, `POST
    /runs/{chain_name}/desarquivar` — FR-3, FR-4.
  - Rota existente `GET /runs` ganha query param `archived: str | None` — FR-4.
- `backend/tests/test_http_api.py` — testes novos para AC-01 a AC-07.
- `frontend/src/lib/apiClient.js`:
  - `getRuns({ archived } = {})` (assinatura estendida, retrocompatível — chamada
    sem args continua igual) — FR-4.
  - `archiveRun(chainName)` / `unarchiveRun(chainName)` (novos) — FR-3, FR-4.
- `frontend/src/components/RunsList.jsx`:
  - Novo estado `showArchived`; card "Arquivadas" na `summary-strip`; botão
    "Arquivar"/"Desarquivar" por linha conforme `showArchived` — FR-3, FR-4.
  - `useEffect` de polling: `setTimeout` recursivo que rechama a mesma busca a
    partir do dado recém-recebido, enquanto houver `running`/`pending` nele;
    cancelado no cleanup — FR-1, NFR-3.
- `frontend/src/components/RunDetail.jsx`:
  - Ação "Arquivar"/"Desarquivar" no cabeçalho, ao lado do badge de status — FR-3,
    FR-4.
  - `useEffect` de polling: `setTimeout` recursivo que rechama `getRunDetail`
    enquanto o `status` recém-recebido for `running`/`pending`; cancelado no
    cleanup/troca de `chainName` — FR-2, NFR-3.

## Data Model

Coluna nova em `workflow_runs` (por arquivo `.db`, um por chain — não é uma tabela
compartilhada):

```
archived_at TEXT NULL   -- ISO-8601 UTC quando arquivada; NULL quando não arquivada
```

Migração: aditiva, aplicada sob demanda (`ALTER TABLE ... ADD COLUMN`, idempotente)
— sem script de migração separado, sem downtime, sem tocar `_SCHEMA` do
`SqliteStateStore` (a tabela continua sendo criada por ele para `.db` novos; a
coluna é adicionada por `http_api.py` no primeiro acesso a qualquer `.db`,
novo ou antigo).

## Interfaces / Contracts

Contratos novos/alterados, todos aditivos — publicados em `adr/ADR-011-acs.md`
(AC-05, AC-06, AC-07):

- `POST /runs/{chain_name}/arquivar` → 200 `{"chain_name": string, "archived":
  true}`; 404 `{"error": {"code": "not_found", "message": string}}`. Idempotente.
- `POST /runs/{chain_name}/desarquivar` → 200 `{"chain_name": string, "archived":
  false}`; 404 igual acima. Idempotente.
- `GET /runs?archived=true` → mesmo formato de item de hoje + `archived: boolean`;
  sem o parâmetro, só itens `archived: false` (comportamento de hoje preservado).
- `GET /runs/{chain_name}` → ganha `archived: boolean` no corpo; todo campo
  existente mantém nome/tipo (mesma garantia dada pela ADR-010-AC-09 ao campo
  `plugin`).

Nenhum outro contrato muda: `POST /runs`, `POST /runs/from-template`, `GET
/workflows`, `GET /workspace/repos`, `GET /runs/{chain_name}/stream`, instrução e
`POST /runs/{chain_name}/cancelar` continuam exatamente como em `009`/ADR-010.

## Requirement Coverage

| Requirement | Addressed by |
|---|---|
| FR-1 / AC-08, AC-09 | `RunsList.jsx` (polling condicional a execução ativa) |
| FR-2 / AC-10, AC-11, AC-12 | `RunDetail.jsx` (polling condicional a status não-terminal, cleanup no unmount/troca) |
| FR-3 / AC-02, AC-04, AC-05, AC-13 | `http_api.py` (rota arquivar), `RunsList.jsx`/`RunDetail.jsx` (ação arquivar) |
| FR-4 / AC-03, AC-04, AC-05, AC-06, AC-14, AC-15 | `http_api.py` (rota desarquivar, `?archived=`), `RunsList.jsx` (filtro "Arquivadas") |
| NFR-1 (herdado) | Nenhuma mudança — sem autenticação |
| NFR-2 | Arquivar nunca apaga `.db`/histórico — só `archived_at`; detalhe continua acessível arquivado (AC-15) |
| NFR-3 | Polling condicional (para quando não há nada ativo/terminal) — AC-09, AC-11 |
| NFR-4 | Campos/rotas novos são aditivos — `archived`/rotas novas não removem nem renomeiam nada existente (AC-01, AC-07) |

## Constitution Compliance

- **Spec before code** (princípio 1): este plan e a ADR-011 são escritos antes da
  implementação — Tasks gate abaixo precisa passar antes do primeiro commit de
  código desta feature.
- **Contrato REST é do backend** (princípio 5): as rotas novas e o campo `archived`
  estão decididos e publicados em
  `adr/ADR-011-atualizacao-automatica-arquivamento-execucoes.md`, revisitando
  `afeta: [motor-workflow]` — este plan só consome a decisão.
- **Configuração em runtime** (princípio 6): nenhuma mudança nesta feature toca
  configuração de boot.

## Key Decisions

| Decision | Choice | Alternatives considered | Rationale |
|---|---|---|---|
| Onde persiste "arquivada" | Coluna `archived_at` no `.db` por chain, lida/escrita direto via `sqlite3` fora do `StateStorePort` | `localStorage` no frontend; índice/arquivo separado (`_archived.json`) | Decisão explícita do usuário (precisa sobreviver a troca de navegador) + mesmo padrão de desacoplamento de leitura já usado por `list_runs`/`get_run_detail` (ADR-004) — sem novo formato de arquivo para manter sincronizado |
| Como a lista/detalhe atualizam sozinhos | Polling (`setTimeout` recursivo, decide com o dado fresco de cada resposta) sobre os endpoints REST já existentes | SSE/WebSocket dedicado para lista e/ou detalhe; `setInterval` fixo | Ganho de um canal push não se justifica para um app local de uso individual (RNF-3); polling de poucos segundos resolve com muito menos superfície nova. `setInterval` fixo decidiria se reagenda com o estado de uma rodada atrás (ainda não atualizado no instante em que o efeito roda) — `setTimeout` recursivo evita essa condição de corrida |
| Quando parar de arquivar (reversibilidade) | Reversível — filtro "Arquivadas" + ação de desarquivar | Arquivar definitivo (sem tela de gerenciamento) | Decisão explícita do usuário — evita perda acidental de contexto de uma execução |
| Quando o polling para | `RunsList`: sem execução `running`/`pending` na última resposta. `RunDetail`: `detail.status` terminal | Polling incondicional (sempre ativo) | Evita requisições periódicas sem propósito quando não há nada para observar (NFR-3) |

## Risks

- Polling em `RunDetail` e `RunsList` simultâneos (ex.: usuário com duas abas)
  multiplica requisições — aceitável no volume baixo já assumido (uso local
  individual); se isso mudar no futuro, um SSE dedicado passa a se justificar (ver
  Alternativas na ADR-011).
- `ALTER TABLE` num `.db` corrompido ou de formato inesperado poderia lançar um erro
  diferente de "coluna já existe" — mitigado tratando `sqlite3.OperationalError`
  como não-fatal na migração (mesma postura de degradação graciosa de
  `_step_plugins_by_name`, ADR-010).
