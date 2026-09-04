# Atividades e Acceptance Criteria — ADR-001

> Referência: `ADR-001-motor-workflow-plugins.md`. Cada atividade pertence a um
> componente e tem 1+ AC vinculada. A AC de contrato do Plugin Interface descreve o
> contrato explicitamente (campos, tipos e regras elicitadas na Fase 3.5), não apenas
> "deve funcionar".

## Componente: CLI

### Atividade ADR-001-AT-01: Comando de execução/retomada de workflow

- **Descrição**: Implementar comando `workflow run <config>` que inicia uma nova
  execução se não houver `run_id` incompleto para aquele workflow, ou retoma a
  execução incompleta mais recente encontrada no State Store.
- **Depende de**: Chain Loader (AT-02), Workflow Engine (AT-05)

**AC ADR-001-AC-01**
```
Dado um arquivo de config válido e nenhuma execução incompleta anterior
Quando o usuário roda `workflow run <config>`
Então uma nova execução é criada no State Store com status "running" e a cadeia de etapas é executada do início
```

**AC ADR-001-AC-02**
```
Dado um arquivo de config e uma execução anterior com status "failed" para o mesmo workflow
Quando o usuário roda `workflow run <config>`
Então a execução retoma a partir da primeira etapa com status diferente de "completed", sem re-executar as etapas já concluídas
```

---

## Componente: Chain Loader

### Atividade ADR-001-AT-02: Parser e validador da cadeia declarativa

- **Descrição**: Implementar leitura e validação de um arquivo YAML/JSON que declara a
  cadeia ordenada de etapas, cada uma com nome do plugin, `params` e a flag opcional
  `usa_output_anterior`.
- **Depende de**: —

**AC ADR-001-AC-03**
```
Dado um arquivo de config com uma lista de etapas, cada uma referenciando um plugin existente
Quando o Chain Loader processa o arquivo
Então retorna uma estrutura ordenada de etapas com nome do plugin, params e a flag usa_output_anterior (default: false quando omitida)
```

**AC ADR-001-AC-04**
```
Dado um arquivo de config referenciando um plugin que não existe no diretório de plugins
Quando o Chain Loader processa o arquivo
Então a validação falha antes de qualquer etapa ser executada, com mensagem indicando qual plugin não foi encontrado
```

---

## Componente: Plugin Interface

### Atividade ADR-001-AT-03: Contrato base de plugin

- **Descrição**: Definir a interface/classe base que todo plugin deve implementar,
  incluindo a exceção `TransientError` usada para sinalizar falhas retriable.
- **Depende de**: —

**AC ADR-001-AC-05** (contrato in-process)
```
Dado que o Workflow Engine chama um plugin para executar uma etapa
O plugin expõe o método run(context) -> output
O context contém os campos: input (output da etapa anterior ou None), params (dict), run_id (string), step_name (string)
O output retornado é um valor serializável em JSON
Falhas retriable são sinalizadas pelo plugin levantando TransientError; qualquer outra exceção é tratada como falha permanente
```

---

## Componente: Plugin Registry

### Atividade ADR-001-AT-04: Descoberta e validação de plugins

- **Descrição**: Varrer o diretório de plugins configurado, importar os módulos
  encontrados e validar que cada um implementa a Plugin Interface (AT-03) antes de
  disponibilizá-lo ao Engine.
- **Depende de**: Plugin Interface (AT-03)

**AC ADR-001-AC-06**
```
Dado um diretório de plugins contendo um módulo que implementa run(context) -> output corretamente
Quando o Plugin Registry é inicializado
Então o plugin fica disponível para resolução pelo nome declarado na config da cadeia
```

**AC ADR-001-AC-07**
```
Dado um módulo no diretório de plugins que não implementa o método run(context) esperado
Quando o Plugin Registry é inicializado
Então o módulo é rejeitado com um erro claro indicando incompatibilidade com a Plugin Interface, sem interromper o carregamento dos demais plugins válidos
```

---

## Componente: Workflow Engine

### Atividade ADR-001-AT-05: Orquestração sequencial da cadeia

- **Descrição**: Executar as etapas da cadeia em ordem, resolvendo o plugin de cada
  uma via Plugin Registry e decidindo o input (valor fixo dos `params` ou output da
  etapa anterior, conforme `usa_output_anterior`).
- **Depende de**: Chain Loader (AT-02), Plugin Registry (AT-04)

**AC ADR-001-AC-08**
```
Dado uma cadeia de 3 etapas onde a etapa 2 declara usa_output_anterior: true
Quando o Engine executa a cadeia
Então o context.input recebido pelo plugin da etapa 2 é igual ao output retornado pela etapa 1
```

**AC ADR-001-AC-09**
```
Dado uma etapa que não declara usa_output_anterior (ou declara false)
Quando o Engine executa essa etapa
Então o context.input recebido pelo plugin é None, independentemente do output da etapa anterior
```

### Atividade ADR-001-AT-06: Persistência de progresso e retomada

- **Descrição**: Integrar o Engine ao State Store para gravar status/output de cada
  etapa e permitir retomar uma execução incompleta.
- **Depende de**: State Store (AT-08)

**AC ADR-001-AC-10**
```
Dado que uma etapa termina com sucesso
Quando o Engine segue para a próxima etapa
Então o State Store já registra essa etapa como "completed" com seu output, antes de a próxima etapa começar
```

**AC ADR-001-AC-11**
```
Dado que uma etapa falha de forma permanente (exceção que não é TransientError)
Quando o Engine trata essa falha
Então a etapa é marcada como "failed" no State Store, a execução do workflow é interrompida, e nenhuma etapa seguinte é executada
```

---

## Componente: Retry Handler

### Atividade ADR-001-AT-07: Retry configurável por etapa/plugin

- **Descrição**: Envolver a chamada ao plugin de cada etapa, aplicando a política de
  retry (nº de tentativas + backoff) configurada para aquela etapa quando o plugin
  levantar `TransientError`.
- **Depende de**: Plugin Interface (AT-03)

**AC ADR-001-AC-12**
```
Dado uma etapa configurada com política de retry de 3 tentativas
Quando o plugin levanta TransientError nas duas primeiras chamadas e retorna com sucesso na terceira
Então o Retry Handler retorna o output da terceira tentativa como resultado da etapa, sem propagar as falhas anteriores como erro final
```

**AC ADR-001-AC-13**
```
Dado uma etapa configurada com política de retry de 2 tentativas
Quando o plugin levanta TransientError em todas as tentativas
Então o Retry Handler propaga a falha ao Engine como falha permanente após esgotar as tentativas configuradas
```

---

## Componente: State Store (SQLite)

### Atividade ADR-001-AT-08: Schema e camada de acesso

- **Descrição**: Implementar as tabelas `workflow_runs` e `step_executions` e as
  operações de leitura/escrita usadas pelo Engine (criar execução, atualizar status de
  etapa, consultar execução incompleta mais recente).
- **Depende de**: —

**AC ADR-001-AC-14** (contrato de schema)
```
Dado o schema do State Store
A tabela workflow_runs tem os campos: run_id (PK), workflow_name, config_path, status (running|completed|failed), created_at, updated_at
A tabela step_executions tem os campos: run_id (FK), step_name, status (pending|running|completed|failed), attempt_count, input (JSON), output (JSON), error_message, started_at, finished_at
```

---

## Componente: Logger

### Atividade ADR-001-AT-09: Logging estruturado em JSON

- **Descrição**: Emitir logs estruturados em JSON para início/fim de etapa, tentativas
  de retry e erros, integrados ao Engine e ao Retry Handler.
- **Depende de**: —

**AC ADR-001-AC-15**
```
Dado que uma etapa inicia, é reprocessada por retry, ou termina (sucesso ou falha)
Quando o evento ocorre
Então um registro de log em formato JSON é emitido contendo, no mínimo: run_id, step_name, evento, timestamp
```

---

## Tabela de rastreabilidade

| Requisito (PRD) | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-001 | AT-02 | AC-03, AC-04 | Chain Loader | Pendente |
| RF-02 | ADR-001 | AT-03, AT-04 | AC-05, AC-06, AC-07 | Plugin Interface / Plugin Registry | Pendente |
| RF-03 | ADR-001 | AT-04 | AC-06, AC-07 | Plugin Registry | Pendente |
| RF-04 | ADR-001 | AT-06 | AC-10, AC-11 | Workflow Engine | Pendente |
| RF-05 | ADR-001 | AT-07 | AC-12, AC-13 | Retry Handler | Pendente |
| RF-06 | ADR-001 | AT-09 | AC-15 | Logger | Pendente |
| RF-07 | ADR-001 | AT-05 | AC-08, AC-09 | Workflow Engine | Pendente |
| RNF-01 | ADR-001 | AT-05, AT-06 | AC-08 a AC-11 | Workflow Engine | Pendente |
| RNF-02 | ADR-001 | — | — | (distribuição — sem AC técnica dedicada) | N/A |
| RNF-03 | ADR-001 | AT-06 | AC-10, AC-11 | Workflow Engine | Pendente |
| RNF-04 | ADR-001 | AT-08 | AC-14 | State Store (SQLite) | Pendente |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em andamento /
> Concluído / Bloqueado). Isso é o que permite a uma IA (ou a outro humano) auditar
> depois se a demanda foi de fato atendida ponta a ponta.
