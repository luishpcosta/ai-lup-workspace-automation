# Atividades e Acceptance Criteria — ADR-003

> Referência: `ADR-003-execucoes-paralelas-independentes.md`. Único componente
> afetado: CLI (`adapters/cli.py`) — nenhuma mudança em `domain/`/`application/`/
> plugins.

## Componente: CLI (`run-many`)

### Atividade ADR-003-AT-01: Validação do lote antes de disparar qualquer execução

- **Descrição**: Carregar e validar todos os configs do lote (mesmo
  `YamlJsonChainLoader`/`ChainValidationError` da ADR-001), e rejeitar o lote se dois
  configs resolverem para o mesmo `chain.name` — tudo antes de qualquer thread
  começar a rodar.
- **Depende de**: Chain Loader (ADR-001-AT-02)

**AC ADR-003-AC-01**
```
Dado N configs de cadeia válidos, cada um com chain.name distinto
Quando `workflow run-many` é invocado com esses N configs
Então todos são carregados e validados antes de qualquer execução começar
```

**AC ADR-003-AC-02**
```
Dado dois ou mais configs do lote cujo chain.name é igual
Quando `workflow run-many` valida o lote
Então a validação falha antes de disparar qualquer execução, indicando quais configs colidem no nome
```

**AC ADR-003-AC-03**
```
Dado um config inválido (ex. referenciando plugin inexistente) misturado com configs válidos no mesmo lote
Quando `workflow run-many` valida o lote
Então os configs válidos disparam normalmente, e o config inválido aparece no resumo final como falha imediata, sem consumir uma vaga do pool de execuções
```

---

### Atividade ADR-003-AT-02: Execução concorrente com teto configurável

- **Descrição**: Disparar uma execução (`WorkflowEngine.run`) por config válido,
  usando `ThreadPoolExecutor(max_workers=--max-parallel)`, compartilhando uma única
  instância de `FileSystemPluginRegistry` entre as threads (plugins não têm estado
  mutável entre chamadas).
- **Depende de**: Workflow Engine (ADR-001-AT-08), Plugin Registry (ADR-001-AT-04)

**AC ADR-003-AC-04**
```
Dado `--max-parallel N` e mais de N configs válidos no lote
Quando `run-many` executa
Então no máximo N execuções rodam simultaneamente em qualquer instante; as demais aguardam uma vaga liberar
```

**AC ADR-003-AC-05**
```
Dado dois ou mais configs de histórias verdadeiramente independentes (repo_url/historia_id diferentes) rodando em paralelo
Quando as execuções chamam o mesmo plugin (mesma instância compartilhada via registry único)
Então cada chamada usa o context (input/params/run_id/step_name) da sua própria execução, sem nenhum estado cruzado entre elas
```

---

### Atividade ADR-003-AT-03: Isolamento de State Store por execução

- **Descrição**: Cada execução do lote usa seu próprio arquivo SQLite
  (`<db-dir>/<chain.name>.db`), não um `workflow_state.db` compartilhado —
  elimina contenção de escrita entre execuções concorrentes.
- **Depende de**: State Store (ADR-001-AT-08)

**AC ADR-003-AC-06**
```
Dado uma execução do lote para uma cadeia chamada "hist-X"
Quando ela roda dentro de `run-many`
Então seu progresso (workflow_runs/step_executions) é persistido em <db-dir>/hist-X.db, isolado dos arquivos .db das demais execuções do lote
```

**AC ADR-003-AC-07**
```
Dado que uma execução do lote já tinha uma execução incompleta anterior registrada no seu próprio .db (de uma rodada anterior de `run-many` que falhou nela)
Quando o lote roda de novo com o mesmo config
Então essa execução retoma a partir da etapa que falhou, sem repetir as etapas já concluídas (mesma semântica de retomada da ADR-001, AC-02)
```

---

### Atividade ADR-003-AT-04: Resumo final e código de saída

- **Descrição**: Bloquear até todas as execuções do lote terminarem (sucesso ou
  falha), reportar um resumo por história, e retornar exit code 1 se alguma falhou
  (0 se todas completaram). Uma execução falhando não cancela nem afeta as demais.
- **Depende de**: Workflow Engine (ADR-001-AT-08)

**AC ADR-003-AC-08**
```
Dado que todas as execuções do lote terminam (qualquer combinação de sucesso/falha)
Quando `run-many` finaliza
Então imprime um resumo listando, por execução: nome da cadeia, run_id, status (completou/falhou) e o motivo quando falhou
```

**AC ADR-003-AC-09**
```
Dado que pelo menos uma execução do lote terminou com falha
Quando `run-many` termina
Então o exit code do processo é 1
Dado que todas as execuções completaram com sucesso, então o exit code é 0
```

**AC ADR-003-AC-10**
```
Dado que uma execução do lote falha enquanto outras ainda estão em andamento
Quando a falha ocorre
Então as demais execuções continuam rodando normalmente até seu próprio fim — não são canceladas nem interrompidas pela falha de outra
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-003 | AT-01, AT-02 | AC-01 a AC-05 | CLI | Pendente |
| RF-02 | ADR-003 | AT-03 | AC-06, AC-07 | CLI | Pendente |
| RF-03 | ADR-003 | AT-04 | AC-10 | CLI | Pendente |
| RF-04 | ADR-003 | AT-04 | AC-08, AC-09 | CLI | Pendente |
| RNF-01 | ADR-003 | — | — | (decisão de escopo, sem AC técnica — ver Alternativas consideradas) | N/A |
| RNF-02 | ADR-003 | AT-02 | AC-04 | CLI | Pendente |
| RNF-03 (herdado) | ADR-001 | — | — | (ver ADR-001) | N/A |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em andamento /
> Concluído / Bloqueado).
