# Atividades e Acceptance Criteria — ADR-004

> Referência: `ADR-004-api-http-monitoria.md`. Único componente novo:
> `adapters/http_api.py` (`workflow serve`). Nenhum plugin, nenhuma etapa de
> `WorkflowEngine`/`application`/`domain` muda nesta ADR.

## Componente: API HTTP (`workflow serve`)

### Atividade ADR-004-AT-01: Composition root `workflow serve`

- **Descrição**: Novo subcomando `serve --port N --plugins-dir DIR --watch-dir DIR
  --max-parallel N`, análogo a `run`/`run-many` (ADR-001/ADR-003), sem alterá-los.
- **Depende de**: CLI existente (ADR-001-AT-01, ADR-003-AT-01)

**AC ADR-004-AC-01**
```
Dado `workflow serve --port N --watch-dir D` invocado
Quando o comando executa
Então um servidor HTTP sobe na porta N, e os comandos `run`/`run-many` continuam funcionando de forma totalmente independente (nenhum import/mudança neles)
```

---

### Atividade ADR-004-AT-02: Disparo assíncrono de execução (`POST /runs`)

- **Descrição**: Validar o config, disparar `WorkflowEngine.run()` numa thread do pool
  (mesma mecânica do `run-many`, ADR-003), responder imediatamente sem esperar a
  execução terminar, e proteger contra disparo duplicado concorrente do mesmo
  `chain_name`.
- **Depende de**: Workflow Engine (ADR-001-AT-08), disparo concorrente (ADR-003-AT-02)

**AC ADR-004-AC-02** (contrato de payload)
```
Dado POST /runs com corpo {"config_path": "<caminho válido>"}
Quando a requisição é processada
Então responde 202 com {"chain_name": <nome resolvido>, "status": "started"} antes de a execução terminar (a execução continua rodando em background)
```

**AC ADR-004-AC-03**
```
Dado POST /runs com config_path inexistente ou cadeia inválida (mesma validação da ADR-001/ADR-003)
Quando a requisição é processada
Então responde 400 com {"error": {"code": "invalid_config", "message": "..."}}, sem disparar nenhuma execução
```

**AC ADR-004-AC-04** (RNF-03 — proteção contra corrida)
```
Dado uma execução já em andamento (não terminada) para um chain_name X
Quando um segundo POST /runs resolvendo para o mesmo chain_name X chega antes da primeira terminar
Então responde 409 com {"error": {"code": "already_running", ...}}, sem chamar WorkflowEngine.run() uma segunda vez sobre o mesmo arquivo .db
```

---

### Atividade ADR-004-AT-03: Monitoria (`GET /runs`, `GET /runs/{chain_name}`)

- **Descrição**: Escanear todos os arquivos `.db` em `--watch-dir` (schema
  `workflow_runs`/`step_executions` da ADR-001) e expor uma visão agregada, **sem
  distinguir se a execução foi disparada por `serve`, `run-many` ou `run`** — a
  convenção de diretório é o único acoplamento (ver ADR-004, Decisão).
- **Depende de**: State Store (ADR-001-AT-08), isolamento por arquivo (ADR-003-AT-03)

**AC ADR-004-AC-05**
```
Dado arquivos .db em watch-dir criados por serve, por `run-many` e por um `workflow run --db <watch-dir>/<nome>.db` manual no terminal
Quando GET /runs é chamado
Então os três aparecem na lista, cada um com chain_name, run_id, status, created_at/updated_at e o nome do arquivo (source_db) — independente de quem os criou
```

**AC ADR-004-AC-06** (contrato de payload)
```
Dado um chain_name existente em watch-dir
Quando GET /runs/{chain_name} é chamado sem ?include=io
Então retorna status por etapa (step_name, status, attempt_count, started_at, finished_at, error_message) SEM os campos input/output
Quando chamado com ?include=io
Então a resposta inclui também input/output de cada etapa
```

**AC ADR-004-AC-07**
```
Dado um chain_name sem arquivo .db correspondente em watch-dir
Quando GET /runs/{chain_name} é chamado
Então responde 404 com {"error": {"code": "not_found", ...}}
```

---

### Atividade ADR-004-AT-04: Cancelamento (`POST /runs/{chain_name}/cancelar`)

- **Descrição**: Abortar uma execução em andamento — só garantido para execuções
  disparadas pelo próprio processo `serve` (handle em memória); para as demais,
  responde recusando de forma explícita, em vez de falhar silenciosamente.
- **Depende de**: Disparo assíncrono (AT-02)

**AC ADR-004-AC-08**
```
Dado uma execução disparada por este processo `serve`, ainda em andamento
Quando POST /runs/{chain_name}/cancelar é chamado
Então a execução é abortada, marcada "failed" no .db, e a resposta é 200 com {"chain_name", "status": "cancelling"}
```

**AC ADR-004-AC-09**
```
Dado uma execução em andamento que NÃO foi disparada por este processo `serve` (ex.: rodando via `workflow run` no terminal)
Quando POST /runs/{chain_name}/cancelar é chamado
Então responde 409 com {"error": {"code": "not_cancellable", "message": "..."}} explicando que essa execução precisa ser interrompida no processo que a disparou — nenhuma tentativa de matar processo é feita
```

**AC ADR-004-AC-10**
```
Dado um chain_name sem execução conhecida
Quando POST /runs/{chain_name}/cancelar é chamado
Então responde 404 com {"error": {"code": "not_found", ...}}
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-004 | AT-01 | AC-01 | API HTTP | Pendente |
| RF-02 | ADR-004 | AT-02 | AC-02, AC-03 | API HTTP | Pendente |
| RF-03 | ADR-004 | AT-03 | AC-05 | API HTTP | Pendente |
| RF-04 | ADR-004 | AT-03 | AC-06, AC-07 | API HTTP | Pendente |
| RF-05 | ADR-004 | AT-04 | AC-08, AC-09, AC-10 | API HTTP | Pendente |
| RNF-01 (herdado) | ADR-001 | — | — | (ver ADR-001) | N/A |
| RNF-02 | ADR-004 | AT-02, AT-03, AT-04 | AC-03, AC-04, AC-07, AC-09, AC-10 | API HTTP | Pendente |
| RNF-03 | ADR-004 | AT-02 | AC-04 | API HTTP | Pendente |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em andamento /
> Concluído / Bloqueado).
