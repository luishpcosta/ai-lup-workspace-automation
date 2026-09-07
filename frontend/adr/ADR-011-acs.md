# Atividades e Acceptance Criteria — ADR-011

> Referência: `ADR-011-atualizacao-automatica-arquivamento-execucoes.md`. Cada
> atividade pertence a um componente e tem 1+ AC vinculada. As ACs de contrato REST
> (ADR-011-AC-05, AC-06, AC-07) descrevem o contrato explicitamente — campos, tipos e
> regras.

## Componente: motor-workflow (backend)

### Atividade ADR-011-AT-01: Persistir `archived_at` por execução

- **Descrição**: migração aditiva/idempotente (`ALTER TABLE workflow_runs ADD COLUMN
  archived_at TEXT`, erro de coluna já existente silenciado) aplicada sob demanda
  antes de qualquer leitura/escrita de arquivamento — cobre `.db` criados antes e
  depois desta feature. Sem mudança no `StateStorePort`/`SqliteStateStore` (campo é
  lido/escrito direto via `sqlite3` em `http_api.py`, mesmo padrão de `list_runs`).
- **Depende de**: nada.

**AC ADR-011-AC-01**
```
Dado um arquivo `.db` de execução criado antes desta feature (sem a coluna
  `archived_at`)
Quando qualquer rota de arquivamento/listagem é chamada para essa execução
Então a migração aditiva roda sem erro e a operação completa normalmente
```

### Atividade ADR-011-AT-02: Rotas `arquivar`/`desarquivar`

- **Descrição**: `POST /runs/{chain_name}/arquivar` e
  `POST /runs/{chain_name}/desarquivar`, idempotentes, mesmo contrato de erro 404 já
  usado por `POST /runs/{chain_name}/cancelar`.
- **Depende de**: ADR-011-AT-01.

**AC ADR-011-AC-02**
```
Dado um chain_name existente, não arquivado
Quando POST /runs/{chain_name}/arquivar é chamado
Então a resposta é 200 com {"chain_name": <nome>, "archived": true}
E chamadas repetidas ao mesmo endpoint continuam retornando 200 com "archived": true
  (idempotente)
```

**AC ADR-011-AC-03**
```
Dado um chain_name existente, arquivado
Quando POST /runs/{chain_name}/desarquivar é chamado
Então a resposta é 200 com {"chain_name": <nome>, "archived": false}
E chamadas repetidas continuam retornando 200 com "archived": false (idempotente)
```

**AC ADR-011-AC-04**
```
Dado um chain_name que não existe (sem .db correspondente)
Quando POST /runs/{chain_name}/arquivar OU /desarquivar é chamado
Então a resposta é 404 com {"error": {"code": "not_found", "message": <str>}}
```

**AC ADR-011-AC-05** (contrato REST)
```
Dado que o frontend chama POST /runs/{chain_name}/arquivar ou /desarquivar
O payload de request: nenhum corpo (ação identificada pela rota + chain_name na URL)
A resposta de sucesso é: 200 com os campos: chain_name (string), archived (boolean)
Os erros são: 404 -> {"error": {"code": "not_found", "message": string}} quando
  chain_name não existe
A escrita é idempotente via: a própria semântica da ação (setar archived_at para um
  valor fixo — now() ou NULL — não incrementar/acumular nada)
```

### Atividade ADR-011-AT-03: `GET /runs` filtra por arquivamento; `GET /runs/{chain_name}` expõe `archived`

- **Descrição**: `GET /runs` ganha query param opcional `archived` (`"true"` |
  ausente). Sem o parâmetro, exclui execuções com `archived_at` preenchido
  (comportamento de hoje, preservado). Com `archived=true`, retorna só as que têm
  `archived_at` preenchido. `GET /runs/{chain_name}` (detalhe) sempre inclui o campo
  `archived` (bool), independente de estar ou não arquivada — o detalhe continua
  acessível por link direto mesmo fora da listagem padrão.
- **Depende de**: ADR-011-AT-01.

**AC ADR-011-AC-06** (contrato REST)
```
Dado que o frontend chama GET /runs ou GET /runs?archived=true
O payload de request: query param opcional archived (string "true"; qualquer outro
  valor ou ausência é tratado como "false")
A resposta de sucesso é: 200 com uma lista de objetos — mesmos campos de hoje
  (chain_name, run_id, workflow_name, status, created_at, updated_at, source_db)
  mais archived (boolean)
Sem archived=true: só objetos com archived=false
Com archived=true: só objetos com archived=true
```

**AC ADR-011-AC-07** (contrato REST)
```
Dado que o frontend chama GET /runs/{chain_name}
A resposta de sucesso é: 200 com os mesmos campos de hoje (chain_name, run_id,
  status, created_at, updated_at, steps) mais archived (boolean) — aditivo, resto do
  formato inalterado (mesma garantia de retrocompatibilidade já dada pela
  ADR-010-AC-09 para o campo plugin)
```

---

## Componente: Frontend App

### Atividade ADR-011-AT-04: `RunsList` atualiza sozinha enquanto há execução ativa

- **Descrição**: `RunsList` passa a reconsultar `GET /runs` em intervalo curto
  (poucos segundos) sempre que a resposta mais recente tiver ao menos uma execução
  `running`/`pending`; para de consultar quando não há mais nada ativo. O
  `refreshToken` (disparo/botão manual, ADR-006) continua funcionando exatamente
  como hoje — é um gatilho adicional, não uma substituição.
- **Depende de**: nada (usa `GET /runs` já existente).

**AC ADR-011-AC-08**
```
Dado o painel de execuções aberto, com uma execução em status "running"
Quando o status dessa execução muda no backend (ex.: para "completed") sem qualquer
  ação do usuário na tela
Então o painel reflete o novo status em até um intervalo curto de polling, sem
  exigir clique em "Atualizar"
```

**AC ADR-011-AC-09**
```
Dado o painel de execuções aberto, sem nenhuma execução running/pending
Quando o tempo passa
Então nenhuma nova requisição de polling é disparada (só volta a consultar
  automaticamente após um novo disparo ou clique manual em "Atualizar")
```

### Atividade ADR-011-AT-05: `RunDetail` atualiza sozinho enquanto a execução avança

- **Descrição**: `RunDetail` passa a reconsultar `GET /runs/{chain_name}` em
  intervalo curto enquanto `detail.status` for `running`/`pending`; para quando o
  status vira terminal (`completed`/`failed`). Atualiza a tabela de etapas e o
  status geral exibido. `StreamPanel` não muda — continua com seu próprio SSE
  independente deste polling (ADR-005/ADR-010).
- **Depende de**: nada (usa `GET /runs/{chain_name}` já existente).

**AC ADR-011-AC-10**
```
Dado a tela de detalhe aberta para uma execução "running", com a etapa 1 "running"
Quando a etapa 1 termina e a etapa 2 começa no backend, sem qualquer ação do usuário
  na tela
Então a tabela de etapas reflete os novos status (etapa 1 "completed", etapa 2
  "running") em até um intervalo curto de polling, sem exigir clique em "Atualizar"
```

**AC ADR-011-AC-11**
```
Dado a tela de detalhe aberta para uma execução já "completed" ou "failed"
Quando o tempo passa
Então nenhuma nova requisição de polling é disparada para o detalhe
```

**AC ADR-011-AC-12**
```
Dado o usuário navega para outra execução (ou volta para a listagem) enquanto o
  polling do detalhe anterior estava ativo
Quando a troca de tela acontece
Então o polling da execução anterior é cancelado (nenhuma requisição órfã continua
  disparando para um chainName que não está mais em tela)
```

### Atividade ADR-011-AT-06: UI de arquivar/desarquivar

- **Descrição**: botão "Arquivar" por linha em `RunsList` e no cabeçalho de
  `RunDetail`; novo card/filtro "Arquivadas" na `summary-strip` de `RunsList`
  (mesmo padrão dos cards de status existentes — ADR-006-AC-04), que troca a
  consulta para `GET /runs?archived=true` e mostra botão "Desarquivar" em vez de
  "Arquivar" por linha.
- **Depende de**: ADR-011-AT-02, ADR-011-AT-03.

**AC ADR-011-AC-13**
```
Dado uma execução visível na listagem padrão
Quando o usuário clica em "Arquivar" nessa linha
Então POST /runs/{chain_name}/arquivar é chamado e a execução some da listagem
  padrão (sem precisar de reload manual da página)
```

**AC ADR-011-AC-14**
```
Dado o filtro "Arquivadas" selecionado
Quando a tela renderiza
Então só execuções arquivadas aparecem, cada uma com um botão "Desarquivar"
E clicar em "Desarquivar" chama POST /runs/{chain_name}/desarquivar e remove a
  execução da lista de arquivadas
```

**AC ADR-011-AC-15**
```
Dado uma execução arquivada, acessada diretamente pelo detalhe (RunDetail)
Quando a tela de detalhe renderiza
Então ela mostra o conteúdo normalmente (arquivar nunca bloqueia o acesso ao
  detalhe) com uma ação "Desarquivar" disponível no cabeçalho
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-011 | AT-04 | AC-08, AC-09 | Frontend App | Concluído |
| RF-02 | ADR-011 | AT-05 | AC-10, AC-11, AC-12 | Frontend App | Concluído |
| RF-03 | ADR-011 | AT-02, AT-06 | AC-02, AC-04, AC-05, AC-13 | motor-workflow + Frontend App | Concluído |
| RF-04 | ADR-011 | AT-02, AT-03, AT-06 | AC-03, AC-04, AC-05, AC-06, AC-14, AC-15 | motor-workflow + Frontend App | Concluído |
| RNF-01 | ADR-011 | AT-02 | AC-02, AC-03 | motor-workflow | Concluído |
| RNF-02 | ADR-011 | AT-04, AT-05 | AC-08, AC-10 | Frontend App | Concluído |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em
> andamento / Concluído / Bloqueado).
