# Atividades e Acceptance Criteria — ADR-012

> Referência: `ADR-012-tempo-execucao-tabela.md`. Cada atividade pertence a um
> componente e tem 1+ AC vinculada. As ACs de contrato REST (AC-01, AC-02) descrevem
> o contrato explicitamente — campos, tipos e regras.

## Componente: motor-workflow (backend)

### Atividade ADR-012-AT-01: `GET /runs` ganha `duration_seconds` por item

- **Descrição**: `list_runs` calcula `duration_seconds` (inteiro, segundos, ou `null`)
  a partir de `created_at`/`updated_at`/`status` já lidos do `.db`, sem query
  adicional. Aditivo — nenhum campo existente muda.
- **Depende de**: nada.

**AC ADR-012-AC-01** (contrato REST)
```
Dado que o frontend chama GET /runs
A resposta de sucesso é: 200 com uma lista de objetos — mesmos campos de hoje
  (chain_name, run_id, workflow_name, status, created_at, updated_at, source_db,
  archived) mais duration_seconds (number | null)
Para status terminal (diferente de running/pending): duration_seconds é fixo,
  igual a round(updated_at - created_at) em segundos
Para status running/pending: duration_seconds é igual a round(now() - created_at)
  em segundos, recalculado a cada chamada (não fixo)
```

### Atividade ADR-012-AT-02: `GET /runs/{chain_name}` ganha `duration_seconds`

- **Descrição**: `get_run_detail` inclui `duration_seconds` no corpo, mesma regra de
  cálculo da AT-01, calculado a partir do `run_row` já lido. Aditivo.
- **Depende de**: nada.

**AC ADR-012-AC-02** (contrato REST)
```
Dado que o frontend chama GET /runs/{chain_name}
A resposta de sucesso é: 200 com os mesmos campos de hoje (chain_name, run_id,
  status, created_at, updated_at, steps, archived) mais duration_seconds
  (number | null) — aditivo, resto do formato inalterado (mesma garantia de
  retrocompatibilidade já dada pela ADR-010-AC-09/ADR-011-AC-07)
```

### Atividade ADR-012-AT-03: Cálculo correto para execução terminada vs. em andamento

- **Descrição**: mesma função de cálculo usada pela AT-01 e AT-02 — valor fixo para
  status terminal, valor crescente (baseado em `now()`) para `running`/`pending`.
- **Depende de**: AT-01, AT-02.

**AC ADR-012-AC-03**
```
Dado um run com status terminal (ex.: completed), created_at e updated_at
  conhecidos e fixos
Quando GET /runs ou GET /runs/{chain_name} é chamado duas vezes, em momentos
  diferentes
Então duration_seconds é o mesmo valor exato nas duas chamadas, igual a
  round(updated_at - created_at)
```

**AC ADR-012-AC-04**
```
Dado um run com status running (ou pending), created_at conhecido
Quando GET /runs ou GET /runs/{chain_name} é chamado duas vezes, com um intervalo
  de tempo real entre as chamadas
Então duration_seconds não decresce entre as duas chamadas (aumenta ou permanece
  igual, nunca menor)
```

### Atividade ADR-012-AT-04: Timestamp ausente/corrompido não quebra a resposta

- **Descrição**: se `created_at` (ou `updated_at`, quando necessário para o cálculo)
  não existir ou não for parseável como ISO-8601, `duration_seconds` é `null` — a
  resposta continua 200, sem erro 500.
- **Depende de**: AT-01, AT-02.

**AC ADR-012-AC-05**
```
Dado um run cujo created_at está ausente ou corrompido (não parseável)
Quando GET /runs ou GET /runs/{chain_name} é chamado
Então a resposta é 200 normalmente, com duration_seconds: null para essa execução
  (nenhum erro 500)
```

---

## Componente: Frontend App

### Atividade ADR-012-AT-05: Coluna "Duração" em `RunsList`

- **Descrição**: nova coluna entre "Status" e "Atualizado", lendo
  `run.duration_seconds` e formatando com um novo `formatDuration(seconds)` em
  `lib/format.js` (formato compacto pt-BR: segundos, minutos+segundos, ou
  horas+minutos).
- **Depende de**: ADR-012-AT-01.

**AC ADR-012-AC-06**
```
Dado uma execução com duration_seconds numérico presente na resposta de GET /runs
Quando a tabela de execuções renderiza
Então uma coluna "Duração", posicionada entre "Status" e "Atualizado", mostra o
  valor formatado de forma compacta (ex.: "45s", "2min 14s", "1h 03min")
```

### Atividade ADR-012-AT-06: Duração de execução ativa atualiza sozinha

- **Descrição**: nenhum polling novo — a coluna só precisa reagir ao polling que
  `RunsList` já faz enquanto há execução `running`/`pending` (ADR-011-AT-04). Como o
  backend recalcula `duration_seconds` a cada request para esse status, o valor
  exibido aumenta a cada nova resposta de polling.
- **Depende de**: ADR-012-AT-01, ADR-012-AT-03, ADR-011-AT-04 (polling já existente).

**AC ADR-012-AC-07**
```
Dado o painel de execuções aberto com uma execução em status running, coluna
  "Duração" visível
Quando o polling automático já existente (ADR-011) traz uma nova resposta de
  GET /runs, sem qualquer ação do usuário na tela
Então o valor exibido na coluna "Duração" para essa execução aumenta (nunca
  diminui), sem exigir clique em "Atualizar"
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-012 | AT-01, AT-02, AT-05 | AC-01, AC-02, AC-06 | motor-workflow + Frontend App | Concluído |
| RF-02 | ADR-012 | AT-03, AT-06 | AC-04, AC-07 | motor-workflow + Frontend App | Concluído |
| RF-03 | ADR-012 | AT-03 | AC-03 | motor-workflow | Concluído |
| RNF-01 | ADR-012 | AT-01, AT-02 | AC-01, AC-02 | motor-workflow | Concluído |
| RNF-02 | ADR-012 | AT-01, AT-02, AT-04 | AC-01, AC-02, AC-05 | motor-workflow | Concluído |
| RNF-03 | ADR-012 | AT-06 | AC-07 | Frontend App | Concluído |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em
> andamento / Concluído / Bloqueado).
