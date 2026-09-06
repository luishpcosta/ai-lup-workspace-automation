# Atividades e Acceptance Criteria — ADR-007

> Referência: `ADR-007-templates-workflow-execucao-adhoc.md`. Componentes: Registro de
> Templates (novo), Aplicação de Templates (novo), Chain Loader (fix pontual), API HTTP
> (extensão), Claude Code Runner (modo novo).

## Componente: Registro de Templates (`FileSystemWorkflowTemplateRegistry`, novo)

### Atividade ADR-007-AT-01: Descoberta de templates por diretório

- **Descrição**: Cada `*.yaml`/`*.yml` em um diretório configurado é um candidato a
  template — precisa declarar `id`/`label`/`description`/`params_schema` além de ser
  um chain config válido (`name`/`steps`). Um arquivo malformado é logado e pulado, sem
  derrubar os demais (mesma filosofia de `FileSystemPluginRegistry`, ADR-001-AT-06/07).
- **Depende de**: Chain Loader existente (ADR-001-AT-03/04)

**AC ADR-007-AC-01**
```
Dado um diretório com um arquivo de template válido
Quando o registro faz discover()
Então o template fica disponível por get(id) e list(), com params (name/label/type/required/source) e raw (name/steps/vars completos) corretamente extraídos
```

**AC ADR-007-AC-02**
```
Dado um diretório com um template malformado (sem id, sem steps, ou YAML inválido) misturado com um válido
Quando o registro faz discover()
Então o template malformado é ignorado (logado, não levanta exceção) e o válido continua disponível
```

---

## Componente: Aplicação de Templates (`application/workflow_templates.py`, novo)

### Atividade ADR-007-AT-02: Validação e materialização de um disparo por template

- **Descrição**: `validate_params` verifica campos `required` ausentes; `materialize_
  chain_raw` renderiza um chain config novo (nome único, `vars:` = defaults vazios +
  vars do próprio template + params submetidos) a partir do template + o que foi
  submetido.
- **Depende de**: AT-01

**AC ADR-007-AC-03**
```
Dado um template com um param required não submetido
Quando validate_params roda
Então retorna pelo menos um erro nomeando esse param, e nenhuma execução é disparada
```

**AC ADR-007-AC-04**
```
Dado um template com todos os params required submetidos
Quando materialize_chain_raw roda
Então o chain resultante tem o chain_name fornecido, e vars: contém cada param declarado no params_schema (default "" se não submetido, ou o valor submetido, preservando o tipo original — lista/bool/etc.)
```

---

## Componente: Chain Loader (fix pontual, `yaml_json_chain_loader.py`)

### Atividade ADR-007-AT-03: Preservar tipo em referência `{{ vars.x }}` de valor inteiro

- **Descrição**: Quando o valor de um param é *exatamente* uma referência `{{ vars.x }}`
  (após strip, nada mais no valor), o resultado é o valor original de `vars.x` — não
  `str(vars.x)`. Uma referência parcial/embutida continua sendo stringificada como
  antes (comportamento pré-existente da ADR-002, inalterado).
- **Depende de**: Chain Loader `vars:` (ADR-002-AT-01)

**AC ADR-007-AC-05**
```
Dado um param cujo valor é exatamente "{{ vars.docs_referenced }}" e vars.docs_referenced é uma lista
Quando o Chain Loader resolve esse param
Então o param resultante é a lista original, não uma string
```

**AC ADR-007-AC-06** (regressão)
```
Dado um param cujo valor é "Docs: {{ vars.docs_referenced }} (fim)" (referência parcial/embutida)
Quando o Chain Loader resolve esse param
Então o resultado é a string com str(vars.docs_referenced) substituído no lugar — comportamento idêntico ao existente antes desta ADR
```

---

## Componente: API HTTP (extensão da ADR-004/005)

### Atividade ADR-007-AT-04: Listagem de templates e de repositórios locais

- **Descrição**: `GET /workflows` expõe os templates descobertos; `GET /workspace/repos`
  expõe as subpastas imediatas de `--local-repos-root` (novo flag de `serve`), vazio se
  não configurado.
- **Depende de**: AT-01

**AC ADR-007-AC-07**
```
Dado templates descobertos no boot do serve
Quando GET /workflows é chamado
Então retorna uma lista com id/label/description/params_schema de cada template
```

**AC ADR-007-AC-08**
```
Dado --local-repos-root apontando para um diretório com subpastas
Quando GET /workspace/repos é chamado
Então retorna {name, path} de cada subpasta imediata (arquivos soltos não contam)
```

**AC ADR-007-AC-09**
```
Dado --local-repos-root não configurado (ou apontando para um caminho inexistente)
Quando GET /workspace/repos é chamado
Então retorna uma lista vazia, nunca um erro
```

### Atividade ADR-007-AT-05: Disparo por template (`POST /runs/from-template`)

- **Descrição**: Valida params, materializa um YAML real em `<watch_dir>/_generated-
  configs/`, e delega para o mesmo `ServerState.trigger()` que `POST /runs` já usa —
  reuso total do caminho de disparo/monitoria/stream/instruções.
- **Depende de**: AT-02, AT-04

**AC ADR-007-AC-10**
```
Dado um template_id válido e params que satisfazem o params_schema
Quando POST /runs/from-template é chamado
Então dispara uma execução real (visível em GET /runs, completável, monitorável) e responde 202 com {chain_name, status: started} — mesmo formato de POST /runs
```

**AC ADR-007-AC-11**
```
Dado params faltando um campo required
Quando POST /runs/from-template é chamado
Então responde 400 {"error": {"code": "invalid_params", ...}}, sem disparar nada
```

**AC ADR-007-AC-12**
```
Dado um template_id desconhecido
Quando POST /runs/from-template é chamado
Então responde 404 {"error": {"code": "template_not_found", ...}}
```

**AC ADR-007-AC-13**
```
Dado duas chamadas a POST /runs/from-template para o mesmo template_id, com params diferentes
Quando ambas são disparadas
Então recebem chain_names distintos — nenhuma colisão, ambas executam de forma independente
```

---

## Componente: Claude Code Runner (modo novo, `plugins/claude_code_runner.py`)

### Atividade ADR-007-AT-06: Modo `investigar`

- **Descrição**: Aceita `prompt` + `docs_referenced` (opcional) + `workspace_path` de
  `context.params` (ou `context.input`, se presente — compat com `coding`/`review`).
  Não cria branch, não commita, não abre PR. Reusa `_build_cmd`/`_run_streaming_
  session`/`_poll_instructions` sem alteração — stream SSE e instruções ao vivo (ADR-005)
  funcionam automaticamente para este modo.
- **Depende de**: Claude Code Runner existente (ADR-002-AT-02/03, ADR-005-AT-01..03)

**AC ADR-007-AC-14**
```
Dado workspace_path presente em context.params (sem step workspace_setup anterior)
Quando o plugin roda em modo investigar
Então invoca a CLI com cwd = esse workspace_path, e o output final tem 'relatorio' e 'docs_consultados'
```

**AC ADR-007-AC-15**
```
Dado workspace_path ausente tanto em context.input quanto em context.params
Quando o plugin roda em modo investigar
Então levanta ValueError antes de qualquer invocação da CLI (nenhum processo é iniciado)
```

**AC ADR-007-AC-16**
```
Dado o modo investigar
Quando o prompt é montado
Então instrui explicitamente para não criar branch, não commitar/dar push, não abrir PR — diferente dos modos coding/review
```

---

## Tabela de rastreabilidade

| Requisito | ADR | Atividade | AC | Componente | Status |
|---|---|---|---|---|---|
| RF-01 | ADR-007 | AT-04 | AC-07 | API HTTP | Concluído |
| RF-02 | ADR-007 | AT-04 | AC-08, AC-09 | API HTTP | Concluído |
| RF-03 | ADR-007 | AT-05 | AC-10, AC-11, AC-12, AC-13 | API HTTP | Concluído |
| RF-04 | ADR-007 | AT-01 | AC-01, AC-02 | Registro de Templates | Concluído |
| RF-05 | ADR-007 | AT-06 | AC-14, AC-15, AC-16 | Claude Code Runner | Concluído |
| RF-06 | ADR-007 | AT-06 | AC-14 | Claude Code Runner | Concluído |
| RF-07 | ADR-007 | AT-01, AT-02 | AC-01, AC-04 | Registro de Templates, Aplicação de Templates | Concluído |
| RNF-01 | ADR-007 | AT-05 | AC-10 | API HTTP | Concluído |
| RNF-02 (herdado) | ADR-001 | — | — | (ver ADR-001) | N/A |
| (fix) | ADR-007 | AT-03 | AC-05, AC-06 | Chain Loader | Concluído |
| (aplicação) | ADR-007 | AT-02 | AC-03, AC-04 | Aplicação de Templates | Concluído |

> Atualize a coluna "Status" conforme as atividades avançam (Pendente / Em andamento /
> Concluído / Bloqueado).
